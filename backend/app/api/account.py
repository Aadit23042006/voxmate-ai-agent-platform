from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import (
    User, VoiceSession, Message, ToolCall, Task, Document, DocumentChunk, Webhook,
)
from app.schemas import (
    PreferencesUpdate, PreferencesOut, UsageStatsOut, VALID_TTS_VOICES,
    WebhookCreate, WebhookOut,
)

router = APIRouter(prefix="/account", tags=["account"])


# ---------------------------------------------------------------- prefs ---

@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(get_current_user)):
    return PreferencesOut(tts_voice=user.tts_voice, assistant_name=user.assistant_name, tone=user.tone)


@router.put("/preferences", response_model=PreferencesOut)
def update_preferences(
    payload: PreferencesUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.tts_voice is not None:
        if payload.tts_voice not in VALID_TTS_VOICES:
            raise HTTPException(status_code=400, detail=f"tts_voice must be one of {VALID_TTS_VOICES}")
        user.tts_voice = payload.tts_voice
    if payload.assistant_name is not None:
        name = payload.assistant_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="assistant_name cannot be empty")
        user.assistant_name = name[:40]
    if payload.tone is not None:
        if payload.tone not in ("casual", "formal"):
            raise HTTPException(status_code=400, detail="tone must be 'casual' or 'formal'")
        user.tone = payload.tone

    db.commit()
    db.refresh(user)
    return PreferencesOut(tts_voice=user.tts_voice, assistant_name=user.assistant_name, tone=user.tone)


# ---------------------------------------------------------------- stats ---

@router.get("/stats", response_model=UsageStatsOut)
def get_usage_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session_ids = [s.id for s in db.query(VoiceSession.id).filter(VoiceSession.user_id == user.id).all()]

    total_messages = (
        db.query(Message).filter(Message.session_id.in_(session_ids)).count() if session_ids else 0
    )
    tool_calls = (
        db.query(ToolCall).filter(ToolCall.session_id.in_(session_ids)).all() if session_ids else []
    )

    def _count(name):
        return sum(1 for tc in tool_calls if tc.tool_name == name and tc.status == "success")

    return UsageStatsOut(
        total_sessions=len(session_ids),
        total_messages=total_messages,
        total_tool_calls=len(tool_calls),
        tasks_created=db.query(Task).filter(Task.user_id == user.id).count(),
        code_executions=_count("run_code"),
        documents_uploaded=db.query(Document).filter(Document.user_id == user.id).count(),
        searches_run=_count("search"),
    )


# --------------------------------------------------------------- export ---

@router.get("/export", response_class=PlainTextResponse)
def export_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Plain-text export of every message across all of the user's
    sessions, oldest first — good enough to save/print/attach; a nicer
    PDF export can be layered on top of this later if needed.
    """
    sessions = (
        db.query(VoiceSession)
        .filter(VoiceSession.user_id == user.id)
        .order_by(VoiceSession.started_at.asc())
        .all()
    )

    lines = [f"VoxMate conversation export for {user.email}", ""]
    for s in sessions:
        lines.append(f"=== Session {s.id} — started {s.started_at.isoformat()} ===")
        messages = (
            db.query(Message)
            .filter(Message.session_id == s.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        for m in messages:
            lines.append(f"[{m.created_at.isoformat()}] {m.role}: {m.transcript}")
        lines.append("")

    return "\n".join(lines) or "No conversations yet."


# --------------------------------------------------------------- delete ---

@router.delete("/data")
def delete_all_data(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """GDPR-style 'erase my data': deletes every session, message, tool
    call, uploaded document, and webhook belonging to this user. The
    account/login itself is kept (deleting it mid-request would break the
    auth token that's currently authorizing this call) — to close the
    account entirely, delete the user via a separate admin action.
    """
    session_ids = [s.id for s in db.query(VoiceSession.id).filter(VoiceSession.user_id == user.id).all()]
    if session_ids:
        db.query(ToolCall).filter(ToolCall.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(Message).filter(Message.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(VoiceSession).filter(VoiceSession.user_id == user.id).delete(synchronize_session=False)

    document_ids = [d.id for d in db.query(Document.id).filter(Document.user_id == user.id).all()]
    if document_ids:
        db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(document_ids)).delete(synchronize_session=False)
        db.query(Document).filter(Document.user_id == user.id).delete(synchronize_session=False)

    db.query(Task).filter(Task.user_id == user.id).delete(synchronize_session=False)
    db.query(Webhook).filter(Webhook.user_id == user.id).delete(synchronize_session=False)

    db.commit()
    return {"deleted": True}


# ------------------------------------------------------------- webhooks ---

@router.get("/webhooks", response_model=List[WebhookOut])
def list_webhooks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Webhook).filter(Webhook.user_id == user.id).order_by(Webhook.created_at.desc()).all()


@router.post("/webhooks", response_model=WebhookOut)
def create_webhook(
    payload: WebhookCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = payload.name.strip()
    if not name.isidentifier():
        raise HTTPException(status_code=400,
                             detail="name must be a valid identifier (letters/digits/underscore, no spaces)")
    if not payload.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")

    existing = db.query(Webhook).filter(Webhook.user_id == user.id, Webhook.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"a webhook named '{name}' already exists")

    webhook = Webhook(user_id=user.id, name=name, description=payload.description.strip(), url=payload.url)
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.user_id == user.id).first()
    if row is None:
        return {"deleted": False}
    db.delete(row)
    db.commit()
    return {"deleted": True}
