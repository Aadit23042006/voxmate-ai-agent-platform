from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Meeting
from app.integrations.meetings import start_meeting, add_segment, finish_meeting

router=APIRouter(prefix="/meetings",tags=["meetings"])
class StartPayload(BaseModel): title: str="Meeting"
class SegmentPayload(BaseModel): text: str; speaker: str="You"

@router.post("")
def create(payload:StartPayload,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    m=start_meeting(db,user,payload.title); return {"id":m.id,"title":m.title,"status":m.status}

@router.post("/{meeting_id}/segments")
def segment(meeting_id:str,payload:SegmentPayload,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    try: m=add_segment(db,user,meeting_id,payload.text,payload.speaker)
    except ValueError as e: raise HTTPException(404,str(e))
    return {"id":m.id,"transcript":m.transcript}

@router.post("/{meeting_id}/finish")
def finish(meeting_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    try: m=finish_meeting(db,user,meeting_id)
    except ValueError as e: raise HTTPException(404,str(e))
    return {"id":m.id,"title":m.title,"status":m.status,"transcript":m.transcript,
            "summary":m.summary,"action_items":m.action_items,"decisions":m.decisions,"ended_at":m.ended_at}

@router.get("")
def list_meetings(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    rows=db.query(Meeting).filter(Meeting.user_id==user.id).order_by(Meeting.created_at.desc()).all()
    return [{"id":m.id,"title":m.title,"status":m.status,"summary":m.summary,"action_items":m.action_items,"decisions":m.decisions,"created_at":m.created_at} for m in rows]

@router.get("/{meeting_id}")
def get_meeting(meeting_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    m=db.query(Meeting).filter(Meeting.id==meeting_id,Meeting.user_id==user.id).first()
    if not m: raise HTTPException(404,"Meeting not found")
    return {"id":m.id,"title":m.title,"status":m.status,"transcript":m.transcript,"summary":m.summary,"action_items":m.action_items,"decisions":m.decisions}
