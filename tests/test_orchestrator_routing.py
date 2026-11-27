from app.agents.llm_client import _mock_generate
import json


def test_mock_generate_routes_reminder():
    raw = _mock_generate("remind me to call mom tomorrow")
    data = json.loads(raw)
    assert data["tool_call"]["name"] == "create_reminder"


def test_mock_generate_routes_list_tasks():
    raw = _mock_generate("what tasks do I have")
    data = json.loads(raw)
    assert data["tool_call"]["name"] == "list_tasks"


def test_mock_generate_plain_text_for_interview():
    raw = _mock_generate("I have a data science interview tomorrow")
    assert "interview" in raw.lower()
