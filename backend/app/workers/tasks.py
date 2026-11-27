from datetime import datetime, timezone
"""Background jobs for conversation summaries and scheduled automations.

The tasks use the existing SQLAlchemy models and integrations; no schema
migration is required. Live Gemini summarization is used when configured.
Without credentials, a clearly-labelled extractive fallback keeps local
development deterministic and offline-capable.
"""
from datetime import datetime

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.integrations.notifications import process_due_notifications, send_notification
from app.integrations.workflows import run_due_workflows
from app.models.models import Message, Memory, Notification, Task, VoiceSession


@celery_app.task(name="app.workers.tasks.summarize_session")
def summarize_session(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(VoiceSession).filter(VoiceSession.id == session_id).first()
        if session is None:
            return {"session_id": session_id, "status": "not_found"}

        messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .all()
        )
        if not messages:
            return {"session_id": session_id, "status": "no_messages"}

        transcript = "\\n".join(
            f"{(message.role or 'unknown').upper()}: {message.transcript}"
            for message in messages
            if message.transcript and message.transcript.strip()
        )
        if not transcript:
            return {"session_id": session_id, "status": "no_messages"}

        from app.agents.llm_client import get_llm_client

        client = get_llm_client()
        if client.client is None:
            # Do not pretend this is an LLM summary. Keep a bounded transcript
            # extract so the offline project remains usable without API keys.
            summary = "Offline conversation extract (Gemini is not configured):\\n" + transcript[-5000:]
            mode = "offline_fallback"
        else:
            prompt = (
                "Summarize this voice-assistant conversation in concise plain text. "
                "Capture the user's goal, important facts, decisions, and unresolved "
                "actions. Do not invent details.\\n\\n" + transcript[-30000:]
            )
            response = client.generate_content(
                prompt=prompt,
                system_instruction="You summarize conversations accurately and do not invent information.",
                temperature=0.2,
                max_output_tokens=600,
            )
            summary = client._extract_response_text(
                response, default_fallback="The conversation could not be summarized."
            )
            mode = "gemini"

        memory_content = f"[session:{session_id}] {summary}"
        existing = (
            db.query(Memory)
            .filter(
                Memory.user_id == session.user_id,
                Memory.type == "summary",
                Memory.content.like(f"[session:{session_id}]%"),
            )
            .first()
        )
        if existing:
            existing.content = memory_content
        else:
            db.add(Memory(
                user_id=session.user_id,
                type="summary",
                content=memory_content,
                confidence=1.0,
            ))
        db.commit()
        return {
            "session_id": session_id,
            "status": "summarized",
            "mode": mode,
            "message_count": len(messages),
            "memory_saved": True,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.send_reminder_notification")
def send_reminder_notification(task_id: str):
    """Send the queued notification for a task only once it is due."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None:
            return {"task_id": task_id, "status": "not_found"}
        if task.status != "pending":
            return {"task_id": task_id, "status": "task_not_pending"}
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if task.due_at is None:
            return {"task_id": task_id, "status": "no_due_date"}
        if task.due_at > now:
            return {"task_id": task_id, "status": "not_due"}

        candidates = (
            db.query(Notification)
            .filter(
                Notification.user_id == task.user_id,
                Notification.status == "pending",
            )
            .order_by(Notification.created_at.asc())
            .all()
        )
        notification = next(
            (row for row in candidates
             if (row.data or {}).get("task_id") == str(task.id)),
            None,
        )
        if notification is None:
            return {"task_id": task_id, "status": "notification_not_pending"}
        result = send_notification(db, notification)
        return {"task_id": task_id, "status": result.get("status", "unknown")}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.process_smart_notifications")
def process_smart_notifications():
    db = SessionLocal()
    try:
        return process_due_notifications(db)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.process_workflow_automations")
def process_workflow_automations():
    db = SessionLocal()
    try:
        return run_due_workflows(db)
    finally:
        db.close()


