import base64
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


def fake_turn_result(text="Audio AI response"):
    return SimpleNamespace(
        text=text,
        plan=None,
        tool_results=[],
        confirmation=None,
    )


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


def send_audio(websocket, audio_bytes=b"fake-audio", mime_type="audio/wav"):
    websocket.send_json({
        "type": "audio_utterance",
        "audio": base64.b64encode(audio_bytes).decode("utf-8"),
        "mime_type": mime_type,
    })


def receive_turn_events(websocket):
    events = []

    for _ in range(10):
        event = websocket.receive_json()
        events.append(event)

        if event.get("type") == "turn_complete":
            return events

    pytest.fail("WebSocket did not send turn_complete event")


def test_audio_transcript_reaches_orchestrator(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    transcription_calls = []
    orchestrator_calls = []

    def fake_transcribe(**kwargs):
        transcription_calls.append(kwargs)
        return "Set a reminder for tomorrow"

    def fake_orchestrator(**kwargs):
        orchestrator_calls.append(kwargs)
        return fake_turn_result()

    monkeypatch.setattr(gateway, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(
        gateway, "orchestrator_handle_turn", fake_orchestrator
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        send_audio(websocket, b"sample-audio", "audio/webm")
        receive_turn_events(websocket)

    assert len(transcription_calls) == 1
    assert transcription_calls[0]["audio_bytes"] == b"sample-audio"
    assert transcription_calls[0]["mime_type"] == "audio/webm"

    assert len(orchestrator_calls) == 1
    assert orchestrator_calls[0]["user_input"] == "Set a reminder for tomorrow"
    assert orchestrator_calls[0]["session_id"] == str(session.id)
    assert orchestrator_calls[0]["user"].id == test_user.id


def test_audio_returns_transcript_and_ai_response(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    monkeypatch.setattr(
        gateway,
        "transcribe_audio",
        lambda **kwargs: "Hello VoxMate",
    )
    monkeypatch.setattr(
        gateway,
        "orchestrator_handle_turn",
        lambda **kwargs: fake_turn_result("Hello from VoxMate AI"),
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        send_audio(websocket)

        events = receive_turn_events(websocket)

    transcript_events = [
        event for event in events
        if event.get("type") == "final_transcript"
    ]
    agent_events = [
        event for event in events
        if event.get("type") == "agent_text"
    ]

    assert len(transcript_events) == 1
    assert transcript_events[0]["data"] == "Hello VoxMate"

    assert len(agent_events) == 1
    assert agent_events[0]["data"] == "Hello from VoxMate AI"
    assert events[-1]["type"] == "turn_complete"


def test_empty_audio_transcription_returns_error(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    orchestrator_calls = []

    monkeypatch.setattr(
        gateway,
        "transcribe_audio",
        lambda **kwargs: "",
    )
    monkeypatch.setattr(
        gateway,
        "orchestrator_handle_turn",
        lambda **kwargs: orchestrator_calls.append(kwargs),
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        send_audio(websocket)
        event = websocket.receive_json()

    assert event["type"] == "error"
    assert "No spoken words detected" in event["message"]
    assert orchestrator_calls == []


def test_audio_transcription_exception_returns_error(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    orchestrator_calls = []

    def failing_transcription(**kwargs):
        raise RuntimeError("Simulated transcription failure")

    monkeypatch.setattr(
        gateway, "transcribe_audio", failing_transcription
    )
    monkeypatch.setattr(
        gateway,
        "orchestrator_handle_turn",
        lambda **kwargs: orchestrator_calls.append(kwargs),
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        send_audio(websocket)
        event = websocket.receive_json()

    assert event["type"] == "error"
    assert event["message"] == "Failed to transcribe audio speech."
    assert orchestrator_calls == []


def test_audio_transcription_timeout_returns_error(
    test_user, db_session, monkeypatch
):
    session = create_voice_session(test_user, db_session)
    token = create_access_token(subject=str(test_user.id))
    prepare_gateway(monkeypatch)

    orchestrator_calls = []

    def timeout_transcription(**kwargs):
        raise TimeoutError("Simulated transcription timeout")

    monkeypatch.setattr(
        gateway, "transcribe_audio", timeout_transcription
    )
    monkeypatch.setattr(
        gateway,
        "orchestrator_handle_turn",
        lambda **kwargs: orchestrator_calls.append(kwargs),
    )

    with client.websocket_connect(
        f"/ws/voice/{session.id}?token={token}"
    ) as websocket:
        send_audio(websocket)
        event = websocket.receive_json()

    assert event["type"] == "error"
    assert event["message"] == "Transcription operation timed out."
    assert orchestrator_calls == []
