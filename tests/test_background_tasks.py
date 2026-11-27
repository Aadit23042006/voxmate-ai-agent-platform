from datetime import datetime, timedelta, timezone
import uuid

from app.database import SessionLocal
from app.models.models import Message, Memory, Notification, Task, User, VoiceSession
from app.workers import tasks as worker_tasks


def _create_user():
    db = SessionLocal()
    user = User(email=f"worker-{uuid.uuid4().hex}@example.com", hashed_password="test")
    db.add(user)
    db.commit()
    user_id = str(user.id)
    db.close()
    return user_id


def test_summarize_session_saves_user_scoped_memory(monkeypatch):
    user_id = _create_user()
    seed_db = SessionLocal()
    session = VoiceSession(user_id=user_id)
    seed_db.add(session)
    seed_db.commit()
    seed_db.refresh(session)
    session_id = str(session.id)
    seed_db.add_all([
        Message(session_id=session_id, role="user", transcript="Help me plan a study schedule."),
        Message(session_id=session_id, role="assistant", transcript="We will divide topics across five days."),
    ])
    seed_db.commit()
    seed_db.close()

    class OfflineClient:
        client = None

    monkeypatch.setattr(worker_tasks, "SessionLocal", lambda: SessionLocal())
    monkeypatch.setattr("app.agents.llm_client.get_llm_client", lambda: OfflineClient())

    result = worker_tasks.summarize_session.run(session_id)
    assert result["status"] == "summarized"
    assert result["mode"] == "offline_fallback"
    check_db = SessionLocal()
    saved = check_db.query(Memory).filter(
        Memory.user_id == user_id,
        Memory.type == "summary",
    ).all()
    assert len(saved) == 1
    assert "study schedule" in saved[0].content
    check_db.close()

    # Re-running updates the existing session summary instead of duplicating it.
    worker_tasks.summarize_session.run(session_id)
    check_db = SessionLocal()
    assert check_db.query(Memory).filter(
        Memory.user_id == user_id,
        Memory.type == "summary",
    ).count() == 1
    check_db.close()

def test_summarize_session_handles_missing_session(monkeypatch):
    monkeypatch.setattr(worker_tasks, "SessionLocal", lambda: SessionLocal())
    result = worker_tasks.summarize_session.run("missing-session")
    assert result["status"] == "not_found"


def test_send_reminder_notification_skips_future_task(monkeypatch):
    user_id = _create_user()
    seed_db = SessionLocal()
    task = Task(
        user_id=user_id,
        title="Future reminder",
        due_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status="pending",
    )
    seed_db.add(task)
    seed_db.commit()
    task_id = str(task.id)
    seed_db.close()

    monkeypatch.setattr(worker_tasks, "SessionLocal", lambda: SessionLocal())
    result = worker_tasks.send_reminder_notification.run(task_id)
    assert result["status"] == "not_due"


def test_send_reminder_notification_sends_due_task_once(monkeypatch):
    user_id = _create_user()
    seed_db = SessionLocal()
    task = Task(
        user_id=user_id,
        title="Due reminder",
        due_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        status="pending",
    )
    seed_db.add(task)
    seed_db.commit()
    seed_db.refresh(task)
    task_id = str(task.id)
    notification = Notification(
        user_id=user_id,
        title="Reminder",
        body=task.title,
        data={"task_id": task_id},
        scheduled_for=task.due_at,
        status="pending",
    )
    seed_db.add(notification)
    seed_db.commit()
    seed_db.close()

    monkeypatch.setattr(worker_tasks, "SessionLocal", lambda: SessionLocal())

    def fake_send(db, row):
        row.status = "sent"
        db.commit()
        return {"status": "sent"}

    monkeypatch.setattr(worker_tasks, "send_notification", fake_send)
    result = worker_tasks.send_reminder_notification.run(task_id)
    assert result["status"] == "sent"

    check_db = SessionLocal()
    assert check_db.query(Notification).filter(
        Notification.data["task_id"].as_string() == task_id
    ).one().status == "sent"
    check_db.close()
    assert worker_tasks.send_reminder_notification.run(task_id)["status"] == "notification_not_pending"

