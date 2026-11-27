from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.models import VoiceSession
from app.security import create_access_token
from app.realtime import voice_gateway as gateway


client = TestClient(app)


def create_voice_session(test_user, db_session):
    session = VoiceSession(user_id=test_user.id)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def fake_turn_result(text="Test AI response"):
    return SimpleNamespace(
        text=text,
        plan=None,
        tool_results=[],
        confirmation=None,
    )


def receive_turn_events(websocket):
    events = []

    for _ in range(10):
        event = websocket.receive_json()
        events.append(event)

        if event.get("type") == "turn_complete":
            return events

    pytest.fail("WebSocket did not send turn_complete event")


def prepare_gateway(monkeypatch):
    monkeypatch.setattr(
        gateway,
        "get_default_client",
        lambda: object(),
    )
    monkeypatch.setattr(
        gateway,
        "synthesize_speech",
        lambda **kwargs: b"fake-audio",
    )


def test_text_message_reaches_orchestrator(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    calls = []

    def fake_orchestrator(**kwargs):
        calls.append(kwargs)
        return fake_turn_result()

    monkeypatch.setattr(
        gateway,
        "orchestrator_handle_turn",
        fake_orchestrator,
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        websocket.send_json({
            "type": "text",
            "text": "Hello VoxMate",
        })

        receive_turn_events(websocket)

    assert len(calls) == 1
    assert calls[0]["user_input"] == "Hello VoxMate"
    assert calls[0]["session_id"] == str(session.id)
    assert calls[0]["user"].id == test_user.id


def test_orchestrator_response_returns_to_websocket(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    monkeypatch.setattr(
        gateway,
        "orchestrator_handle_turn",
        lambda **kwargs: fake_turn_result("Hello from AI"),
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        websocket.send_json({
            "type": "text_utterance",
            "text": "Say hello",
        })

        events = receive_turn_events(websocket)

    agent_events = [
        event for event in events
        if event.get("type") == "agent_text"
    ]

    assert len(agent_events) == 1
    assert agent_events[0]["data"] == "Hello from AI"
    assert agent_events[0]["agent"] == "voice"


def test_empty_text_is_ignored_safely(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    calls = []

    def fake_orchestrator(**kwargs):
        calls.append(kwargs["user_input"])
        return fake_turn_result()

    monkeypatch.setattr(
        gateway,
        "orchestrator_handle_turn",
        fake_orchestrator,
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        websocket.send_json({
            "type": "text",
            "text": "",
        })

        websocket.send_json({
            "type": "text",
            "text": "Continue",
        })

        receive_turn_events(websocket)

    assert calls == ["Continue"]


def test_orchestrator_error_returns_fallback_response(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    def failing_orchestrator(**kwargs):
        raise RuntimeError("Simulated orchestrator failure")

    monkeypatch.setattr(
        gateway,
        "orchestrator_handle_turn",
        failing_orchestrator,
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        websocket.send_json({
            "type": "text",
            "text": "Test error handling",
        })

        events = receive_turn_events(websocket)

    agent_events = [
        event for event in events
        if event.get("type") == "agent_text"
    ]

    assert len(agent_events) == 1
    assert "encountered an error" in agent_events[0]["data"]
    assert events[-1]["type"] == "turn_complete"
