from app.tools.briefing_tool import DailyBriefingTool
from app.agents.llm_client import build_system_prompt
from app.agents.router import system_prompt_for, AGENTS
from app.tools.registry import get_tool
from app.tools.webhook_tool import WebhookTool


class _FakeUser:
    def __init__(self, assistant_name="VoxMate", tone="casual"):
        self.assistant_name = assistant_name
        self.tone = tone


def test_build_system_prompt_uses_assistant_name_and_tone():
    prompt = build_system_prompt("test persona", ["search"],
                                  assistant_name="Jarvis", tone="formal")
    assert "You are Jarvis" in prompt
    assert "professional and formal" in prompt


def test_build_system_prompt_defaults_casual():
    prompt = build_system_prompt("test persona", ["search"])
    assert "You are VoxMate" in prompt
    assert "warm, casual" in prompt


def test_build_system_prompt_includes_language_instruction():
    prompt = build_system_prompt("test persona", ["search"])
    assert "same language" in prompt


def test_system_prompt_for_applies_user_prefs():
    prompt = system_prompt_for(AGENTS["general"], user=_FakeUser("Nova", "formal"))
    assert "You are Nova" in prompt
    assert "formal" in prompt


def test_daily_briefing_tool_with_no_tasks(db_session, test_user):
    tool = DailyBriefingTool()
    result = tool.run(db_session, test_user, {})
    assert result["task_count"] == 0
    assert "briefing" in result


def test_get_tool_falls_back_to_webhook(db_session, test_user):
    from app.models.models import Webhook

    webhook = Webhook(user_id=test_user.id, name="check_inventory",
                       description="checks warehouse inventory", url="https://example.com/hook")
    db_session.add(webhook)
    db_session.commit()

    tool = get_tool("check_inventory", db=db_session, user=test_user)
    assert isinstance(tool, WebhookTool)
    assert tool.url == "https://example.com/hook"


def test_get_tool_returns_none_for_unknown_name(db_session, test_user):
    assert get_tool("nonexistent_tool", db=db_session, user=test_user) is None
