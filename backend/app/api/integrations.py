from app.utils.datetime import utcnow
"""Phase 2 integrations: Google OAuth, notifications, and workflows."""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, GoogleConnection, OAuthState, Notification, Workflow
from app.integrations.google import configured, authorization_url, exchange_code
from app.integrations.notifications import register_device
from app.integrations.workflows import run_workflow
from app.integrations.github import save_token, status as github_status, disconnect as github_disconnect, GitHubError

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/google/connect")
def google_connect(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not configured():
        raise HTTPException(503, "Google OAuth is not configured on this VoxMate backend.")
    state = secrets.token_urlsafe(32)
    db.add(OAuthState(id=state, user_id=user.id, provider="google"))
    db.commit()
    return {"authorization_url": authorization_url(state)}


@router.get("/google/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    row = db.query(OAuthState).filter(OAuthState.id == state, OAuthState.provider == "google").first()
    if not row or row.created_at < utcnow() - timedelta(minutes=10):
        raise HTTPException(400, "Invalid or expired OAuth state.")
    tokens = exchange_code(code)
    conn = db.query(GoogleConnection).filter(GoogleConnection.user_id == row.user_id).first()
    expires = utcnow() + timedelta(seconds=int(tokens.get("expires_in", 3600)))
    if conn:
        conn.access_token = tokens["access_token"]
        if tokens.get("refresh_token"): conn.refresh_token = tokens["refresh_token"]
        conn.expires_at = expires
        conn.scope = tokens.get("scope")
        conn.updated_at = utcnow()
    else:
        conn = GoogleConnection(user_id=row.user_id, access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"), expires_at=expires, scope=tokens.get("scope"))
        db.add(conn)
    db.delete(row); db.commit()
    return RedirectResponse(url="/docs")


@router.get("/google/status")
def google_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"connected": db.query(GoogleConnection).filter(GoogleConnection.user_id == user.id).first() is not None}



class GitHubTokenPayload(BaseModel):
    token: str = Field(min_length=20, description="GitHub fine-grained personal access token.")

@router.post("/github/connect")
def github_connect(payload: GitHubTokenPayload, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return save_token(db, user, payload.token.strip())
    except GitHubError as exc:
        raise HTTPException(400, str(exc))

@router.get("/github/status")
def github_connection_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return github_status(db, user)

@router.delete("/github/disconnect")
def github_connection_disconnect(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return github_disconnect(db, user)

class DevicePayload(BaseModel):
    expo_push_token: str
    platform: str | None = None

@router.post("/notifications/device")
def add_device(payload: DevicePayload, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = register_device(db, user, payload.expo_push_token, payload.platform)
    return {"id": row.id, "enabled": row.enabled}


class NotificationPayload(BaseModel):
    title: str
    body: str
    data: dict = Field(default_factory=dict)
    scheduled_for: datetime | None = None

@router.post("/notifications")
def create_notification(payload: NotificationPayload, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.integrations.notifications import queue_notification
    row = queue_notification(db, user, payload.title, payload.body, payload.data, payload.scheduled_for)
    return {"id": row.id, "status": row.status}


class WorkflowPayload(BaseModel):
    name: str
    trigger_type: str
    trigger_config: dict = Field(default_factory=dict)
    actions: list[dict] = Field(default_factory=list)
    enabled: bool = True

@router.post("/workflows")
def create_workflow(payload: WorkflowPayload, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.trigger_type not in {"schedule","task_due","webhook"}:
        raise HTTPException(400, "Unsupported workflow trigger.")
    wf=Workflow(user_id=user.id,name=payload.name,trigger_type=payload.trigger_type,
                trigger_config=payload.trigger_config,actions=payload.actions,enabled=payload.enabled)
    db.add(wf); db.commit(); db.refresh(wf)
    return wf

@router.get("/workflows")
def list_workflows(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Workflow).filter(Workflow.user_id == user.id).order_by(Workflow.created_at.desc()).all()

@router.post("/workflows/{workflow_id}/run")
def run_workflow_now(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    wf=db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if not wf: raise HTTPException(404, "Workflow not found")
    return {"results": run_workflow(db, user, wf, {"trigger":"manual"})}

