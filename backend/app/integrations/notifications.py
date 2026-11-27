from app.utils.datetime import utcnow
"""Smart notification service (Expo push + durable DB notification queue)."""
import httpx
from datetime import datetime
from app.config import settings
from app.models.models import Notification, NotificationDevice

EXPO_URL = "https://exp.host/--/api/v2/push/send"


def register_device(db, user, token, platform=None):
    row = db.query(NotificationDevice).filter(NotificationDevice.expo_push_token == token).first()
    if row:
        row.user_id = user.id
        row.enabled = True
        row.platform = platform
    else:
        row = NotificationDevice(user_id=user.id, expo_push_token=token, platform=platform)
        db.add(row)
    db.commit()
    return row


def queue_notification(db, user, title, body, data=None, scheduled_for=None):
    row = Notification(
        user_id=user.id, title=title, body=body, data=data or {},
        scheduled_for=scheduled_for,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if scheduled_for is None:
        send_notification(db, row)
    return row


def send_notification(db, notification):
    devices = db.query(NotificationDevice).filter(
        NotificationDevice.user_id == notification.user_id,
        NotificationDevice.enabled == True,
    ).all()
    if not devices:
        notification.status = "failed"
        db.commit()
        return {"status": "no_device"}
    messages = [{
        "to": d.expo_push_token,
        "title": notification.title,
        "body": notification.body,
        "data": notification.data or {},
        "sound": "default",
    } for d in devices]
    headers = {"Content-Type": "application/json"}
    if settings.expo_access_token:
        headers["Authorization"] = f"Bearer {settings.expo_access_token}"
    try:
        r = httpx.post(EXPO_URL, json=messages, headers=headers, timeout=20)
        r.raise_for_status()
        notification.sent_at = utcnow()
        notification.status = "sent"
        db.commit()
        return {"status": "sent", "response": r.json()}
    except Exception as exc:
        notification.status = "failed"
        db.commit()
        return {"status": "failed", "error": str(exc)}


def process_due_notifications(db):
    now = utcnow()
    rows = db.query(Notification).filter(
        Notification.status == "pending",
        Notification.scheduled_for <= now,
    ).limit(100).all()
    return [send_notification(db, row) for row in rows]

