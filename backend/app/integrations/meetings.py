from app.utils.datetime import utcnow
import json, re
from datetime import datetime
from app.models.models import Meeting, MeetingSegment
from app.agents.llm_client import get_llm_client

def start_meeting(db,user,title="Meeting"):
    m=Meeting(user_id=user.id,title=title,status="recording",transcript="",action_items=[],decisions=[])
    db.add(m); db.commit(); db.refresh(m); return m

def add_segment(db,user,meeting_id,text,speaker="You"):
    m=db.query(Meeting).filter(Meeting.id==meeting_id,Meeting.user_id==user.id,Meeting.status=="recording").first()
    if not m: raise ValueError("Meeting not found or already completed")
    db.add(MeetingSegment(meeting_id=m.id,user_id=user.id,speaker=speaker,text=text))
    m.transcript=(m.transcript+"\n"+f"{speaker}: {text}").strip()
    db.commit(); return m

def finish_meeting(db,user,meeting_id):
    m=db.query(Meeting).filter(Meeting.id==meeting_id,Meeting.user_id==user.id).first()
    if not m: raise ValueError("Meeting not found")
    if m.status=="completed": return m
    prompt=("Analyze this meeting transcript. Return valid JSON with keys summary (string), "
            "action_items (array of objects with task, owner, due_date), decisions (array of strings), "
            "open_questions (array of strings). Do not invent missing owners/dates.\n\n"+m.transcript)
    r=get_llm_client().generate_content(contents=prompt)
    raw=getattr(r,"text",str(r))
    try:
        clean=re.sub(r"^```json|```$","",raw.strip(),flags=re.I).strip()
        data=json.loads(clean)
    except Exception:
        data={"summary":raw,"action_items":[],"decisions":[],"open_questions":[]}
    m.summary=data.get("summary","")
    m.action_items=data.get("action_items",[])
    m.decisions=data.get("decisions",[])
    m.status="completed"; m.ended_at=utcnow()
    db.commit(); db.refresh(m); return m

