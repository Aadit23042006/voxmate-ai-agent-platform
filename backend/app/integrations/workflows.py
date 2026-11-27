from app.utils.datetime import utcnow
"""Small, durable workflow automation engine."""
from datetime import datetime, timedelta
from app.models.models import Workflow
from app.integrations.notifications import queue_notification
from app.integrations.google import create_calendar_event, send_gmail


def run_action(db, user, action, context=None):
    kind = action.get("type")
    cfg = {**(action.get("config") or {})}
    context = context or {}
    for k, v in list(cfg.items()):
        if isinstance(v, str):
            cfg[k] = v.replace("{{context}}", str(context))
    if kind == "notify":
        row = queue_notification(db, user, cfg.get("title", "VoxMate"), cfg.get("body", str(context)))
        return {"type": kind, "status": "success", "notification_id": row.id}
    if kind == "send_email":
        return {"type": kind, "status": "success", "result": send_gmail(
            db, user, cfg["to"], cfg["subject"], cfg["body"]
        )}
    if kind == "calendar_event":
        return {"type": kind, "status": "success", "result": create_calendar_event(
            db, user, cfg["title"], cfg["start"], cfg.get("end"),
            cfg.get("description", ""), cfg.get("timezone", "Asia/Kolkata")
        )}
    if kind == "reminder":
        from app.tools.reminder_tool import ReminderTool
        return {"type": kind, "status": "success", "result": ReminderTool().run(
            db, user, {"title": cfg["title"], "due_at": cfg.get("due_at")}
        )}
    return {"type": kind, "status": "error", "error": f"Unknown workflow action: {kind}"}


def run_workflow(db, user, workflow, context=None):
    results = []
    for action in workflow.actions or []:
        results.append(run_action(db, user, action, context))
    workflow.last_run_at = utcnow()
    db.commit()
    return results


def run_due_workflows(db):
    now = utcnow()
    rows = db.query(Workflow).filter(Workflow.enabled == True).all()
    from app.models.models import User, Task
    out = []
    for wf in rows:
        cfg = wf.trigger_config or {}
        should_run = False
        context = {"time": now.isoformat(), "trigger": wf.trigger_type}
        if wf.trigger_type == "schedule":
            interval = int(cfg.get("interval_minutes", 60))
            should_run = not wf.last_run_at or (now - wf.last_run_at).total_seconds() >= interval * 60
        elif wf.trigger_type == "task_due":
            # Trigger when a pending task enters the configured look-ahead window.
            minutes = int(cfg.get("within_minutes", 30))
            due_limit = now + timedelta(minutes=minutes)
            task = db.query(Task).filter(Task.user_id == wf.user_id, Task.status == "pending",
                Task.due_at != None, Task.due_at >= now, Task.due_at <= due_limit).order_by(Task.due_at).first()
            should_run = task is not None and (not wf.last_run_at or task.due_at > wf.last_run_at)
            if task:
                context.update({"task_id": str(task.id), "task_title": task.title, "due_at": task.due_at.isoformat()})
        if should_run:
            user = db.query(User).filter(User.id == wf.user_id).first()
            if user:
                out.append(run_workflow(db, user, wf, context))
    return out

