from google.genai import types

from app.tools.reminder_tool import ReminderTool
from app.tools.task_tool import ListTasksTool
from app.tools.search_tool import SearchTool
from app.tools.code_execution_tool import CodeExecutionTool
from app.tools.document_tool import DocumentQATool
from app.tools.briefing_tool import DailyBriefingTool
from app.tools.research_tool import DeepResearchTool
from app.tools.google_tools import CalendarListTool, CalendarCreateTool, GmailSearchTool, GmailSendTool, GmailGetTool, WorkflowCreateTool
from app.tools.github_tools import (
    GitHubListReposTool, GitHubGetFileTool, GitHubSearchCodeTool,
    GitHubCreateBranchTool, GitHubWriteFileTool, GitHubCreatePRTool,
)

TOOL_REGISTRY = {
    tool.name: tool
    for tool in [
        ReminderTool(),
        ListTasksTool(),
        SearchTool(),
        CodeExecutionTool(),
        DocumentQATool(),
        DailyBriefingTool(), DeepResearchTool(),
        CalendarListTool(), CalendarCreateTool(), GmailSearchTool(), GmailSendTool(), GmailGetTool(), WorkflowCreateTool(),
        GitHubListReposTool(), GitHubGetFileTool(), GitHubSearchCodeTool(),
        GitHubCreateBranchTool(), GitHubWriteFileTool(), GitHubCreatePRTool(),
    ]
}

# JSON schemas exposed to Gemini function calling. These describe the
# existing tool interfaces; the tools themselves remain unchanged.
TOOL_SCHEMAS = {
    "create_reminder": {
        "description": "Create a reminder/task for the current user.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Reminder title."},
                "due_at": {
                    "type": "string",
                    "description": "Optional ISO-8601 due date/time. Convert explicit user dates such as tomorrow, today, or in N days into ISO-8601. Use 09:00 for tomorrow or a future day without a specified time; use 23:59 for today. Preserve an explicitly requested time. Omit only when the user gives no due date.",
                },
            },
            "required": ["title"],
        },
    },
    "list_tasks": {
        "description": "List the current user's pending and existing tasks/reminders.",
        "parameters": {"type": "object", "properties": {}},
    },
    "search": {
        "description": "Search the web for current information and return grounded sources.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Web search query."}},
            "required": ["query"],
        },
    },
    "run_code": {
        "description": "Run a short safe Python program to verify calculations, logic, or data-processing results.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code to execute."}},
            "required": ["code"],
        },
    },
    "ask_document": {
        "description": "Answer a question using the user's uploaded documents.",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "Question about uploaded documents."}},
            "required": ["question"],
        },
    },

    "calendar_list": {"description": "List upcoming Google Calendar events.", "parameters": {"type":"object","properties":{"max_results":{"type":"integer"}}}},
    "calendar_create_event": {"description": "Create a Google Calendar event.", "parameters": {"type":"object","properties":{"title":{"type":"string"},"start":{"type":"string","description":"ISO datetime"},"end":{"type":"string","description":"ISO datetime"},"description":{"type":"string"},"timezone":{"type":"string"}},"required":["title","start"]}},
    "gmail_search": {"description": "Search the user's Gmail mailbox.", "parameters": {"type":"object","properties":{"query":{"type":"string"},"max_results":{"type":"integer"}},"required":["query"]}},
    "gmail_get_message": {"description": "Read a Gmail message by message id.", "parameters": {"type":"object","properties":{"message_id":{"type":"string"}},"required":["message_id"]}},
    "gmail_send": {"description": "Send an email from the user's connected Gmail account.", "parameters": {"type":"object","properties":{"to":{"type":"string"},"subject":{"type":"string"},"body":{"type":"string"}},"required":["to","subject","body"]}},
    "create_workflow": {"description": "Create an automated workflow with a trigger and ordered actions. Actions can be notify, send_email, calendar_event, or reminder.", "parameters": {"type":"object","properties":{"name":{"type":"string"},"trigger_type":{"type":"string","enum":["schedule","task_due","webhook"]},"trigger_config":{"type":"object"},"actions":{"type":"array","items":{"type":"object"}}},"required":["name","trigger_type","actions"]}},
    "deep_research": {"description": "Perform multi-source deep research and synthesize findings with sources.", "parameters": {"type":"object","properties":{"query":{"type":"string"},"depth":{"type":"integer"}},"required":["query"]}},
    "github_list_repos": {"description": "List repositories available in the user's connected GitHub account.", "parameters": {"type":"object","properties":{"per_page":{"type":"integer"}}}},
    "github_get_file": {"description": "Read a text file from a GitHub repository. Use this to inspect code before proposing changes.", "parameters": {"type":"object","properties":{"owner":{"type":"string"},"repo":{"type":"string"},"path":{"type":"string"},"ref":{"type":"string"}},"required":["owner","repo","path"]}},
    "github_search_code": {"description": "Search code in repositories accessible to the user.", "parameters": {"type":"object","properties":{"query":{"type":"string"},"per_page":{"type":"integer"}},"required":["query"]}},
    "github_create_branch": {"description": "Create a coding-agent branch from a base branch.", "parameters": {"type":"object","properties":{"owner":{"type":"string"},"repo":{"type":"string"},"branch":{"type":"string"},"from_ref":{"type":"string"}},"required":["owner","repo","branch"]}},
    "github_write_file": {"description": "Write/commit a complete file to a GitHub branch. Use only after inspecting the current file.", "parameters": {"type":"object","properties":{"owner":{"type":"string"},"repo":{"type":"string"},"path":{"type":"string"},"content":{"type":"string"},"message":{"type":"string"},"branch":{"type":"string"},"sha":{"type":"string"}},"required":["owner","repo","path","content","message","branch"]}},
    "github_create_pr": {"description": "Create a pull request from a coding-agent branch.", "parameters": {"type":"object","properties":{"owner":{"type":"string"},"repo":{"type":"string"},"title":{"type":"string"},"body":{"type":"string"},"head":{"type":"string"},"base":{"type":"string"}},"required":["owner","repo","title","body","head"]}},
    "daily_briefing": {
        "description": "Create a concise spoken-friendly briefing from the user's pending tasks.",
        "parameters": {"type": "object", "properties": {}},
    },
}


def get_tool(name: str, db=None, user=None):
    """Look up a built-in tool, then a user-defined webhook tool."""
    tool = TOOL_REGISTRY.get(name)
    if tool is not None:
        return tool

    if db is not None and user is not None:
        from app.models.models import Webhook
        from app.tools.webhook_tool import WebhookTool

        webhook = (
            db.query(Webhook)
            .filter(Webhook.user_id == user.id, Webhook.name == name)
            .first()
        )
        if webhook is not None:
            return WebhookTool(webhook.name, webhook.url, webhook.description)

    return None


def list_webhook_tool_descriptions(db, user) -> list[str]:
    from app.models.models import Webhook

    webhooks = db.query(Webhook).filter(Webhook.user_id == user.id).all()
    return [f"{w.name}(arguments): {w.description}" for w in webhooks]


def get_tool_declarations(tool_names=None, db=None, user=None):
    """Return Gemini function declarations for the allowed tools."""
    names = list(tool_names or TOOL_REGISTRY.keys())

    # User webhooks are only exposed to the general agent.
    if db is not None and user is not None:
        try:
            from app.models.models import Webhook
            webhooks = db.query(Webhook).filter(Webhook.user_id == user.id).all()
            names.extend(w.name for w in webhooks if w.name not in names)
        except Exception:
            pass

    declarations = []
    for name in names:
        schema = TOOL_SCHEMAS.get(name)
        if schema:
            declarations.append(types.FunctionDeclaration(
                name=name,
                description=schema["description"],
                parameters_json_schema=schema["parameters"],
            ))
            continue

        # Dynamic webhook tools do not store a JSON schema in this scaffold,
        # so expose a permissive object schema.
        tool = get_tool(name, db=db, user=user)
        if tool is not None and getattr(tool, "description", None):
            declarations.append(types.FunctionDeclaration(
                name=name,
                description=tool.description,
                parameters_json_schema={
                    "type": "object",
                    "properties": {},
                },
            ))

    return [types.Tool(function_declarations=declarations)] if declarations else []


def get_all_tools(db=None, user=None):
    """Compatibility helper returning Gemini-compatible tool declarations."""
    return get_tool_declarations(db=db, user=user)
