from app.utils.datetime import utcnow
"""Google Calendar + Gmail REST integration using OAuth2.

This is additive: the existing Gemini/tools/auth stack is untouched. Google
features are available only after the user connects a Google account.
"""
import base64
import json
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import httpx
from app.config import settings
from app.models.models import GoogleConnection

logger = logging.getLogger("voxmate.google")

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]


def configured():
    return bool(settings.google_client_id and settings.google_client_secret)


def authorization_url(state: str):
    if not configured():
        raise RuntimeError("Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return GOOGLE_AUTH + "?" + urllib.parse.urlencode(params)


def exchange_code(code: str):
    r = httpx.post(TOKEN_URL, data={
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=20)
    r.raise_for_status()
    return r.json()


def _refresh(conn, db):
    if not conn.refresh_token:
        return conn.access_token
    if conn.expires_at and conn.expires_at > utcnow() + timedelta(seconds=60):
        return conn.access_token
    data = exchange_refresh_token(conn.refresh_token)
    conn.access_token = data["access_token"]
    conn.expires_at = utcnow() + timedelta(seconds=int(data.get("expires_in", 3600)))
    db.commit()
    return conn.access_token


def exchange_refresh_token(refresh_token: str):
    r = httpx.post(TOKEN_URL, data={
        "refresh_token": refresh_token,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "grant_type": "refresh_token",
    }, timeout=20)
    r.raise_for_status()
    return r.json()


def connection(db, user):
    return db.query(GoogleConnection).filter(GoogleConnection.user_id == user.id).first()


def _request(db, user, method, url, **kwargs):
    conn = connection(db, user)
    if not conn:
        raise RuntimeError("Google account is not connected. Connect Google in VoxMate Settings first.")
    token = _refresh(conn, db)
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    headers.setdefault("Content-Type", "application/json")
    r = httpx.request(method, url, headers=headers, timeout=30, **kwargs)
    if r.status_code == 401 and conn.refresh_token:
        data = exchange_refresh_token(conn.refresh_token)
        conn.access_token = data["access_token"]
        conn.expires_at = utcnow() + timedelta(seconds=int(data.get("expires_in", 3600)))
        db.commit()
        headers["Authorization"] = f"Bearer {conn.access_token}"
        r = httpx.request(method, url, headers=headers, timeout=30, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def list_calendar_events(db, user, time_min=None, time_max=None, max_results=10):
    now = datetime.now(timezone.utc)
    params = {
        "timeMin": (time_min or now).isoformat().replace("+00:00", "Z"),
        "maxResults": max_results,
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    if time_max:
        params["timeMax"] = time_max.isoformat().replace("+00:00", "Z")
    return _request(db, user, "GET", f"{CALENDAR_BASE}/calendars/primary/events", params=params)


def create_calendar_event(db, user, title, start, end=None, description="", timezone_name="Asia/Kolkata"):
    end = end or start
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start, "timeZone": timezone_name},
        "end": {"dateTime": end, "timeZone": timezone_name},
    }
    return _request(db, user, "POST", f"{CALENDAR_BASE}/calendars/primary/events", json=body)


def send_gmail(db, user, to, subject, body):
    raw = MIMEText(body, "plain", "utf-8")
    raw["To"] = to
    raw["Subject"] = subject
    encoded = base64.urlsafe_b64encode(raw.as_bytes()).decode().rstrip("=")
    return _request(db, user, "POST", f"{GMAIL_BASE}/messages/send", json={"raw": encoded})


def search_gmail(db, user, query, max_results=10):
    return _request(db, user, "GET", f"{GMAIL_BASE}/messages", params={"q": query, "maxResults": max_results})


def get_gmail_message(db, user, message_id):
    return _request(db, user, "GET", f"{GMAIL_BASE}/messages/{message_id}", params={"format": "full"})

