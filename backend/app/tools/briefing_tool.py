from app.models.models import Task
from app.agents.llm_client import summarize_briefing
from app.tools.base import BaseTool


class DailyBriefingTool(BaseTool):
    name = "daily_briefing"

    def validate(self, arguments):
        return arguments or {}

    def run(self, db, user, arguments):
        tasks = (
            db.query(Task)
            .filter(Task.user_id == user.id, Task.status == "pending")
            .order_by(Task.due_at)
            .all()
        )
        task_dicts = [
            {"title": t.title, "due_at": t.due_at.isoformat() if t.due_at else None}
            for t in tasks
        ]
        briefing = summarize_briefing(task_dicts)
        return {
            "briefing": briefing,
            "task_count": len(task_dicts),
            "tasks": task_dicts,
        }
