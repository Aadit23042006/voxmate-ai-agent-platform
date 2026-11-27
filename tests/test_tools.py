import pytest
from app.tools.reminder_tool import ReminderTool
from app.tools.search_tool import SearchTool
from app.tools.base import ToolError


def test_reminder_tool_requires_title():
    tool = ReminderTool()
    with pytest.raises(ToolError):
        tool.validate({})


def test_reminder_tool_valid():
    tool = ReminderTool()
    args = tool.validate({"title": "Review SQL joins"})
    assert args["title"] == "Review SQL joins"


def test_search_tool_requires_query():
    tool = SearchTool()
    with pytest.raises(ToolError):
        tool.validate({})


def test_search_tool_mock_mode_returns_answer_and_sources():
    tool = SearchTool()
    result = tool.run(None, None, {"query": "data science interview tips"})
    assert result["query"] == "data science interview tips"
    assert "answer" in result
    assert "sources" in result
    assert isinstance(result["sources"], list)
