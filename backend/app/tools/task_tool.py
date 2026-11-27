from app.tools.base import BaseTool
from app.models.models import Task


class ListTasksTool(BaseTool):
    name = "list_tasks"

    def validate(self, arguments):
        return arguments or {}

    def run(self, db, user, arguments):
        tasks = db.query(Task).filter(Task.user_id == user.id).order_by(Task.due_at).all()
        return {"tasks": [{"id": t.id, "title": t.title, "status": t.status,
                            "due_at": t.due_at.isoformat() if t.due_at else None} for t in tasks]}
