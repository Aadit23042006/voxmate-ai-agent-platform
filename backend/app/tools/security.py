"""Tool confirmation and security policy.

Read-only tools continue automatically. Mutating/external tools require an
explicit user approval before execution. The policy is additive and can be
configured with VOXMATE_CONFIRM_TOOLS.
"""
import os
from typing import Any, Dict, Set

from app.tools.base import ToolError


DEFAULT_CONFIRM_TOOLS: Set[str] = {
    "create_reminder",
    "run_code",
    "calendar_create_event",
    "gmail_send",
    "create_workflow",
    "github_create_branch",
    "github_write_file",
    "github_create_pr",
    # User-created webhooks can call arbitrary external systems.
}


def confirmation_required(tool_name: str) -> bool:
    configured = os.getenv("VOXMATE_CONFIRM_TOOLS")
    if configured is not None:
        names = {x.strip() for x in configured.split(",") if x.strip()}
        return tool_name in names
    return tool_name in DEFAULT_CONFIRM_TOOLS or tool_name not in {
        "list_tasks", "search", "ask_document", "daily_briefing", "github_list_repos", "github_get_file", "github_search_code"
    }


def validate_tool_arguments(tool, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if tool is None:
        raise ToolError("Unknown tool.")
    validator = getattr(tool, "validate", None)
    return validator(arguments or {}) if callable(validator) else (arguments or {})
