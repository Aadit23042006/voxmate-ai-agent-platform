from datetime import datetime, timedelta

from app.tools.reminder_tool import ReminderTool


def test_extract_tomorrow_defaults_to_nine_am():
    result = ReminderTool.extract_due_at_from_text("Create a reminder due tomorrow.")
    expected = datetime.now().astimezone() + timedelta(days=1)
    assert result.date() == expected.date()
    assert (result.hour, result.minute) == (9, 0)


def test_extract_tomorrow_preserves_requested_time():
    result = ReminderTool.extract_due_at_from_text("Remind me tomorrow at 5:30 pm.")
    assert (result.hour, result.minute) == (17, 30)


def test_extract_today_defaults_to_1159_pm():
    result = ReminderTool.extract_due_at_from_text("Remind me today.")
    assert result.date() == datetime.now().astimezone().date()
    assert (result.hour, result.minute) == (23, 59)


def test_extract_in_three_days():
    result = ReminderTool.extract_due_at_from_text("Remind me in 3 days.")
    expected = datetime.now().astimezone() + timedelta(days=3)
    assert result.date() == expected.date()
    assert (result.hour, result.minute) == (9, 0)


def test_extract_iso_date():
    result = ReminderTool.extract_due_at_from_text("Due on 2030-05-20.")
    assert result == datetime(2030, 5, 20, 9, 0)


def test_no_date_returns_none():
    assert ReminderTool.extract_due_at_from_text("Create a shopping task.") is None
