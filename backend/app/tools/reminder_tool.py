
from datetime import datetime, timedelta
from app.tools.base import BaseTool, ToolError
from app.models.models import Task


class ReminderTool(BaseTool):
    name = "create_reminder"

    def validate(self, arguments):
        arguments = arguments or {}
        title = arguments.get("title")

        if not isinstance(title, str) or not title.strip():
            raise ToolError("A non-empty task title is required.")

        due_at = self._parse_due_at(arguments.get("due_at"))

        return {"title": title.strip(), "due_at": due_at}

    @staticmethod
    def extract_due_at_from_text(text):
        """Extract an explicit due date from a reminder request."""
        import re

        if not isinstance(text, str) or not text.strip():
            return None

        value = text.strip()
        lower = value.casefold()
        now = datetime.now().astimezone()

        iso_match = re.search(
            r"\b(20\d{2}-\d{2}-\d{2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?)",
            value,
        )
        if iso_match:
            raw = iso_match.group(1).replace(" ", "T", 1)
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone().replace(tzinfo=None)
                elif len(raw) == 10:
                    parsed = parsed.replace(hour=9, minute=0)
                return parsed
            except ValueError:
                return None

        if re.search(r"\btomorrow\b", lower):
            target = (now + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )
        elif re.search(r"\btoday\b", lower):
            target = now.replace(
                hour=23, minute=59, second=0, microsecond=0
            )
        else:
            days_match = re.search(r"\bin\s+(\d+)\s+days?\b", lower)
            if not days_match:
                return None
            target = (now + timedelta(days=int(days_match.group(1)))).replace(
                hour=9, minute=0, second=0, microsecond=0
            )

        time_match = re.search(
            r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
            lower,
        )
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            meridiem = time_match.group(3)
            if hour > 23 or minute > 59 or (meridiem and not 1 <= hour <= 12):
                return None
            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
            target = target.replace(hour=hour, minute=minute)

        return target.replace(tzinfo=None)

    @staticmethod
    def _parse_due_at(value):
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            return value

        if not isinstance(value, str):
            raise ToolError("due_at must be a valid date or datetime.")

        normalized = value.strip().lower()
        now = datetime.now().astimezone()

        if normalized == "tomorrow":
            return (now + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            ).replace(tzinfo=None)

        if normalized == "today":
            return now.replace(
                hour=23, minute=59, second=0, microsecond=0
            ).replace(tzinfo=None)

        try:
            parsed = datetime.fromisoformat(value.strip())
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed
        except ValueError as exc:
            raise ToolError(
                "Invalid due_at. Use an ISO-8601 datetime or 'today'/'tomorrow'."
            ) from exc

    def run(self, db, user, arguments):
        args = self.validate(arguments)

        task = Task(
            user_id=user.id,
            title=args["title"],
            due_at=args["due_at"],
            status="pending",
        )

        try:
            db.add(task)
            db.commit()
            db.refresh(task)

            saved = db.query(Task).filter(
                Task.id == task.id,
                Task.user_id == user.id,
            ).first()

            if saved is None:
                raise ToolError("Task could not be verified after saving.")

        except Exception:
            db.rollback()
            raise

        if task.due_at:
            try:
                from app.integrations.notifications import queue_notification
                queue_notification(
                    db, user, "VoxMate reminder", task.title,
                    {"task_id": str(task.id)}, task.due_at
                )
            except Exception:
                pass

        return {
            "success": True,
            "task_id": str(task.id),
            "title": task.title,
            "status": task.status,
            "due_at": task.due_at.isoformat() if task.due_at else None,
        }
