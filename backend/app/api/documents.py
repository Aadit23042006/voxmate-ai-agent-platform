"""Advanced document workspace APIs; existing upload/RAG behavior remains unchanged."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Document, DocumentChunk, DocumentNote, DocumentRevision
from app.agents.llm_client import answer_from_context

router = APIRouter(prefix="/documents", tags=["documents"])

class NotePayload(BaseModel):
    content: str

class RenamePayload(BaseModel):
    filename: str

@router.get("")
def list_documents(db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    docs = db.query(Document).filter(Document.user_id==user.id).order_by(Document.created_at.desc()).all()
    return [{"id": d.id, "filename": d.filename, "mime_type": d.mime_type, "created_at": d.created_at,
             "chunk_count": len(d.chunks),
             "notes": [{"id": n.id, "content": n.content, "created_at": n.created_at}
                       for n in db.query(DocumentNote).filter(DocumentNote.document_id==d.id).order_by(DocumentNote.created_at).all()]}
           for d in docs]

@router.get("/{document_id}")
def get_document(document_id: str, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    d=db.query(Document).filter(Document.id==document_id, Document.user_id==user.id).first()
    if not d: raise HTTPException(404,"Document not found")
    chunks=db.query(DocumentChunk).filter(DocumentChunk.document_id==d.id).order_by(DocumentChunk.chunk_index).all()
    notes=db.query(DocumentNote).filter(DocumentNote.document_id==d.id).order_by(DocumentNote.created_at).all()
    return {"id":d.id,"filename":d.filename,"mime_type":d.mime_type,"created_at":d.created_at,
            "content":"\n\n".join(c.content for c in chunks),
            "chunks":[{"index":c.chunk_index,"content":c.content} for c in chunks],
            "notes":[{"id":n.id,"content":n.content,"created_at":n.created_at} for n in notes]}

@router.patch("/{document_id}")
def rename_document(document_id: str, payload: RenamePayload, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    d=db.query(Document).filter(Document.id==document_id, Document.user_id==user.id).first()
    if not d: raise HTTPException(404,"Document not found")
    if not payload.filename.strip(): raise HTTPException(400,"Filename is required")
    db.add(DocumentRevision(document_id=d.id,user_id=user.id,filename=d.filename))
    d.filename=payload.filename.strip(); db.commit()
    return {"id":d.id,"filename":d.filename}

@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    d=db.query(Document).filter(Document.id==document_id, Document.user_id==user.id).first()
    if not d: raise HTTPException(404,"Document not found")
    db.delete(d); db.commit(); return {"deleted":True}

@router.post("/{document_id}/notes")
def add_note(document_id: str, payload: NotePayload, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    d=db.query(Document).filter(Document.id==document_id, Document.user_id==user.id).first()
    if not d: raise HTTPException(404,"Document not found")
    n=DocumentNote(document_id=d.id,user_id=user.id,content=payload.content.strip())
    db.add(n); db.commit(); db.refresh(n)
    return {"id":n.id,"content":n.content}

@router.post("/{document_id}/summarize")
def summarize_document(document_id: str, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    d=db.query(Document).filter(Document.id==document_id, Document.user_id==user.id).first()
    if not d: raise HTTPException(404,"Document not found")
    chunks=db.query(DocumentChunk).filter(DocumentChunk.document_id==d.id).order_by(DocumentChunk.chunk_index).all()
    context="\n\n".join(c.content for c in chunks)
    if not context: return {"summary":"No extracted text is available."}
    return {"summary": answer_from_context(context, "Create a structured summary with key points, important facts, and action items.")}
