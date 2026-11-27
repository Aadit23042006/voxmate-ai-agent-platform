"""Phase 5 platform APIs: multi-agent delegation, agent personas, plugins and analytics."""
import time
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import (
    User, CustomAgent, MarketplacePlugin, PluginInstallation, AgentRun,
    VoiceSession, Message, ToolCall,
)
from app.schemas import CustomAgentCreate, CustomAgentOut, PluginOut, AnalyticsOut
from pydantic import BaseModel
from app.agents.llm_client import get_llm_client

router = APIRouter(prefix="/platform", tags=["platform"])

DEFAULT_PLUGINS = [
    dict(slug="research-suite", name="Research Suite", description="Deep research and web search tools.",
         version="1.0.0", author="VoxMate", icon="globe-outline", category="research",
         featured=True, tool_names=["search", "deep_research"]),
    dict(slug="developer-kit", name="Developer Kit", description="Coding Agent tools for GitHub repositories.",
         version="1.0.0", author="VoxMate", icon="code-slash-outline", category="developer",
         featured=True, tool_names=["github_list_repos", "github_get_file", "github_search_code",
                                    "github_create_branch", "github_write_file", "github_create_pr"]),
    dict(slug="productivity-pack", name="Productivity Pack", description="Tasks, reminders, calendar and Gmail.",
         version="1.0.0", author="VoxMate", icon="briefcase-outline", category="productivity",
         featured=False, tool_names=["create_reminder", "list_tasks", "calendar_list",
                                     "calendar_create_event", "gmail_search", "gmail_send"]),
    dict(slug="document-intelligence", name="Document Intelligence", description="Ask questions about uploaded files.",
         version="1.0.0", author="VoxMate", icon="document-text-outline", category="knowledge",
         featured=False, tool_names=["ask_document"]),
]

def _seed(db):
    for item in DEFAULT_PLUGINS:
        if not db.query(MarketplacePlugin).filter_by(slug=item["slug"]).first():
            db.add(MarketplacePlugin(**item))
    db.commit()

@router.get("/agents", response_model=list[CustomAgentOut])
def list_agents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(CustomAgent).filter_by(user_id=user.id).order_by(CustomAgent.created_at.desc()).all()

@router.post("/agents", response_model=CustomAgentOut)
def create_agent(payload: CustomAgentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = payload.name.strip()
    if not name or not payload.persona.strip():
        raise HTTPException(400, "Agent name and persona are required.")
    row = CustomAgent(user_id=user.id, name=name[:60], description=payload.description[:240],
                      persona=payload.persona[:5000], tool_names=payload.tool_names[:30],
                      enabled=payload.enabled)
    db.add(row); db.commit(); db.refresh(row)
    return row

@router.put("/agents/{agent_id}", response_model=CustomAgentOut)
def update_agent(agent_id: str, payload: CustomAgentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(CustomAgent).filter_by(id=agent_id, user_id=user.id).first()
    if not row: raise HTTPException(404, "Agent not found.")
    row.name=payload.name.strip()[:60]; row.description=payload.description[:240]
    row.persona=payload.persona[:5000]; row.tool_names=payload.tool_names[:30]; row.enabled=payload.enabled
    db.commit(); db.refresh(row); return row

@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(CustomAgent).filter_by(id=agent_id,user_id=user.id).first()
    if not row: raise HTTPException(404,"Agent not found.")
    db.delete(row); db.commit(); return {"deleted": True}

@router.get("/plugins", response_model=list[PluginOut])
def list_plugins(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _seed(db)
    installed={x.plugin_id for x in db.query(PluginInstallation).filter_by(user_id=user.id, enabled=True).all()}
    rows=db.query(MarketplacePlugin).filter_by(enabled=True).order_by(MarketplacePlugin.featured.desc(), MarketplacePlugin.name).all()
    return [PluginOut.model_validate(x, from_attributes=True).model_copy(update={"installed": str(x.id) in installed}) for x in rows]

@router.post("/plugins/{plugin_id}/install")
def install_plugin(plugin_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _seed(db); plugin=db.query(MarketplacePlugin).filter_by(id=plugin_id, enabled=True).first()
    if not plugin: raise HTTPException(404,"Plugin not found.")
    row=db.query(PluginInstallation).filter_by(user_id=user.id,plugin_id=plugin.id).first()
    if row: row.enabled=True
    else: db.add(PluginInstallation(user_id=user.id,plugin_id=plugin.id,enabled=True))
    db.commit(); return {"installed": True, "slug": plugin.slug}

@router.delete("/plugins/{plugin_id}/install")
def uninstall_plugin(plugin_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(PluginInstallation).filter_by(user_id=user.id,plugin_id=plugin_id).first()
    if row: db.delete(row); db.commit()
    return {"installed": False}

class MultiAgentRequest(BaseModel):
    task: str
    agent_keys: list[str] | None = None

@router.post("/multi-agent")
def multi_agent(payload: MultiAgentRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Run independent specialist perspectives then synthesize them with a lead agent."""
    task = payload.task
    agent_keys = payload.agent_keys
    if not task.strip(): raise HTTPException(400,"task is required")
    custom=db.query(CustomAgent).filter_by(user_id=user.id,enabled=True).all()
    available=[("general","General assistant","Provide a practical general solution.")]
    available += [(a.name,a.name,a.persona) for a in custom]
    if agent_keys:
        wanted=set(agent_keys)
        available=[a for a in available if a[0] in wanted]
    available=available[:5]
    client=get_llm_client(); results=[]
    for key,name,persona in available:
        started=time.perf_counter()
        try:
            prompt=f"""You are one specialist in a multi-agent team. {persona}
Task: {task}
Return concise findings, assumptions, risks, and a recommendation for the lead agent."""
            response=client.generate_content(prompt)
            text=getattr(response,"text",None) or "No result returned."
            status="success"
        except Exception as exc:
            text=f"Agent failed: {exc}"; status="error"
        latency=int((time.perf_counter()-started)*1000)
        db.add(AgentRun(user_id=user.id,agent_key=key,role="worker",status=status,latency_ms=latency))
        results.append({"agent":name,"status":status,"latency_ms":latency,"result":text})
    synthesis_prompt=f"""You are the lead agent. Synthesize these specialist findings into one useful answer.
Original task: {task}
Findings:
{results}
Resolve conflicts explicitly and give a concrete next step."""
    started=time.perf_counter()
    try:
        response=client.generate_content(synthesis_prompt)
        synthesis=getattr(response,"text",None) or "No synthesis returned."
        status="success"
    except Exception as exc:
        synthesis=f"Synthesis failed: {exc}"; status="error"
    db.add(AgentRun(user_id=user.id,agent_key="lead",role="lead",status=status,
                    latency_ms=int((time.perf_counter()-started)*1000)))
    db.commit()
    return {"task":task,"agents":[r["agent"] for r in results],"findings":results,"synthesis":synthesis}

@router.get("/analytics", response_model=AnalyticsOut)
def analytics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sessions=db.query(VoiceSession).filter_by(user_id=user.id).all()
    ids=[x.id for x in sessions]
    msgs=db.query(Message).filter(Message.session_id.in_(ids)).count() if ids else 0
    calls=db.query(ToolCall).filter(ToolCall.session_id.in_(ids)).all() if ids else []
    successful=sum(c.status=="success" for c in calls)
    lat=[c.latency_ms for c in calls if c.latency_ms is not None]
    counts=Counter(c.tool_name for c in calls)
    runs=db.query(AgentRun).filter_by(user_id=user.id).count()
    return AnalyticsOut(
        sessions=len(sessions),messages=msgs,tool_calls=len(calls),
        successful_tool_calls=successful,failed_tool_calls=len(calls)-successful,
        avg_tool_latency_ms=round(sum(lat)/len(lat),1) if lat else 0.0,
        active_custom_agents=db.query(CustomAgent).filter_by(user_id=user.id,enabled=True).count(),
        installed_plugins=db.query(PluginInstallation).filter_by(user_id=user.id,enabled=True).count(),
        agent_runs=runs,top_tools=[{"tool":k,"calls":v} for k,v in counts.most_common(8)]
    )
