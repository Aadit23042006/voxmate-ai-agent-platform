import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from app.config import settings

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.models.models import VoiceSession
from app.security import create_access_token

client = TestClient(app)


def assert_websocket_denied(url):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(url):
            pass
    assert exc.value.code == 1008


def test_websocket_accepts_valid_token_and_owned_session(test_user, db_session):
    session = VoiceSession(user_id=test_user.id)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    token = create_access_token(subject=str(test_user.id))

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        websocket.close()


def test_websocket_rejects_missing_token(test_user, db_session):
    session = VoiceSession(user_id=test_user.id)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert_websocket_denied(f"/ws/voice/{session.id}")


def test_websocket_rejects_invalid_token(test_user, db_session):
    session = VoiceSession(user_id=test_user.id)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert_websocket_denied(
        f"/ws/voice/{session.id}?token=invalid-token"
    )


def test_websocket_rejects_token_for_nonexistent_user():
    token = create_access_token(subject=str(uuid.uuid4()))

    assert_websocket_denied(
        f"/ws/voice/{uuid.uuid4()}?token={token}"
    )


def test_websocket_rejects_nonexistent_session(test_user):
    token = create_access_token(subject=str(test_user.id))

    assert_websocket_denied(
        f"/ws/voice/{uuid.uuid4()}?token={token}"
    )


def test_websocket_rejects_session_owned_by_another_user(
    test_user, db_session
):
    from app.models.models import User

    other_user = User(
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="test-password",
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    session = VoiceSession(user_id=other_user.id)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    token = create_access_token(subject=str(test_user.id))

    assert_websocket_denied(
        f"/ws/voice/{session.id}?token={token}"
    )

def test_websocket_rejects_expired_token(test_user, db_session):
    session = VoiceSession(user_id=test_user.id)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    expired_token = jwt.encode(
        {
            "sub": str(test_user.id),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    assert_websocket_denied(
        f"/ws/voice/{session.id}?token={expired_token}"
    )
