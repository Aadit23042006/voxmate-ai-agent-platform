from datetime import datetime, timedelta

import pytest

from app.models.models import Task, User
from app.tools.base import ToolError
from app.tools.reminder_tool import ReminderTool


def test_reminder_tomorrow_parses_to_next_day_at_9am():
    before = datetime.now().astimezone()
    result = ReminderTool._parse_due_at("tomorrow")
    after = datetime.now().astimezone()

    assert result.date() in {
        (before + timedelta(days=1)).date(),
        (after + timedelta(days=1)).date(),
    }
    assert (result.hour, result.minute, result.second) == (9, 0, 0)
    assert result.tzinfo is None


def test_reminder_today_parses_to_1159pm():
    result = ReminderTool._parse_due_at("today")

    assert result.date() == datetime.now().astimezone().date()
    assert (result.hour, result.minute, result.second) == (23, 59, 0)
    assert result.tzinfo is None


def test_reminder_parses_iso_datetime():
    value = "2030-05-20T14:30:00"
    result = ReminderTool._parse_due_at(value)

    assert result == datetime(2030, 5, 20, 14, 30, 0)


def test_reminder_rejects_invalid_datetime():
    with pytest.raises(ToolError):
        ReminderTool._parse_due_at("not-a-real-date")


def test_reminder_rejects_empty_title():
    with pytest.raises(ToolError):
        ReminderTool().validate({"title": "   "})


def test_reminder_saves_task_and_verifies_user_ownership(
    db_session, test_user
):
    tool = ReminderTool()

    result = tool.run(
        db_session,
        test_user,
        {"title": "Complete VoxMate Task 5 testing"},
    )

    assert result["success"] is True
    assert result["title"] == "Complete VoxMate Task 5 testing"
    assert result["status"] == "pending"
    assert result["task_id"]

    saved = (
        db_session.query(Task)
        .filter(
            Task.id == result["task_id"],
            Task.user_id == test_user.id,
        )
        .first()
    )

    assert saved is not None
    assert saved.title == result["title"]
    assert saved.status == "pending"


def test_reminder_task_is_not_visible_to_another_user(
    db_session, test_user
):
    other_user = User(
        email="other-" + test_user.id + "@example.com",
        hashed_password="test-password",
    )
    db_session.add(other_user)
    db_session.commit()

    result = ReminderTool().run(
        db_session,
        test_user,
        {"title": "Private reminder"},
    )

    other_user_task = (
        db_session.query(Task)
        .filter(
            Task.id == result["task_id"],
            Task.user_id == other_user.id,
        )
        .first()
    )

    assert other_user_task is None

