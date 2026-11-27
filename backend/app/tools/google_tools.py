from datetime import datetime, timezone
from app.tools.base import BaseTool, ToolError
from app.integrations.google import list_calendar_events, create_calendar_event, send_gmail, search_gmail

class CalendarListTool(BaseTool):
    name = "calendar_list"
    def validate(self, a): return a or {}
    def run(self, db, user, a):
        return list_calendar_events(db, user, max_results=int(a.get("max_results", 10)))

class CalendarCreateTool(BaseTool):
    name = "calendar_create_event"
    def validate(self, a):
        if not a.get("title") or not a.get("start"): raise ToolError("title and start are required")
        return a
    def run(self, db, user, a):
        return create_calendar_event(db, user, a["title"], a["start"], a.get("end"), a.get("description",""), a.get("timezone","Asia/Kolkata"))

class GmailSearchTool(BaseTool):
    name = "gmail_search"
    def validate(self, a):
        if not a.get("query"): raise ToolError("query is required")
        return a
    def run(self, db, user, a): return search_gmail(db, user, a["query"], int(a.get("max_results",10)))

class GmailSendTool(BaseTool):
    name = "gmail_send"
    def validate(self, a):
        for x in ("to","subject","body"):
            if not a.get(x): raise ToolError(f"{x} is required")
        return a
    def run(self, db, user, a): return send_gmail(db, user, a["to"], a["subject"], a["body"])

class WorkflowCreateTool(BaseTool):
    name = "create_workflow"
    def validate(self, a):
        if not a.get("name") or not a.get("trigger_type") or not isinstance(a.get("actions"), list):
            raise ToolError("name, trigger_type and actions are required")
        return a
    def run(self, db, user, a):
        from app.models.models import Workflow
        wf=Workflow(user_id=user.id,name=a["name"],trigger_type=a["trigger_type"],
                    trigger_config=a.get("trigger_config",{}),actions=a["actions"],enabled=True)
        db.add(wf); db.commit(); db.refresh(wf)
        return {"id": wf.id, "name": wf.name, "enabled": wf.enabled}

class GmailGetTool(BaseTool):
    name = "gmail_get_message"
    def validate(self, a):
        if not a.get("message_id"): raise ToolError("message_id is required")
        return a
    def run(self, db, user, a):
        from app.integrations.google import get_gmail_message
        return get_gmail_message(db, user, a["message_id"])
