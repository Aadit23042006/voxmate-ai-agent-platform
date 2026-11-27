from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, ResearchReport

router=APIRouter(prefix="/research",tags=["research"])

@router.get("")
def list_reports(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    rows=db.query(ResearchReport).filter(ResearchReport.user_id==user.id).order_by(ResearchReport.created_at.desc()).all()
    return [{"id":r.id,"query":r.query,"answer":r.answer,"sources":r.sources,"created_at":r.created_at} for r in rows]

@router.get("/{report_id}")
def get_report(report_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    r=db.query(ResearchReport).filter(ResearchReport.id==report_id,ResearchReport.user_id==user.id).first()
    if not r: raise HTTPException(404,"Research report not found")
    return {"id":r.id,"query":r.query,"answer":r.answer,"sources":r.sources,"created_at":r.created_at}
