"""Intent routing for VoxMate's specialized agents."""

from dataclasses import dataclass
from app.agents.llm_client import build_system_prompt


@dataclass(frozen=True)
class Agent:
    key: str
    persona: str
    tool_names: list[str]


AGENTS = {
    "math": Agent(
        key="math",
        persona=(
            "Act as the MATH & LOGIC specialist. Verify calculations, word "
            "problems, logic puzzles, and data-processing questions with the "
            "run_code tool when computation is useful."
        ),
        tool_names=["run_code", "search"],
    ),
    "document": Agent(
        key="document",
        persona=(
            "Act as the DOCUMENT specialist. Answer questions about the "
            "user's uploaded documents using ask_document."
        ),
        tool_names=["ask_document"],
    ),
    "coding": Agent(
        key="coding",
        persona=(
            "Act as the CODING AGENT. Work like a careful senior developer: first inspect "
            "the repository and relevant files, search for existing patterns, reason about "
            "the smallest safe change, then use GitHub branch/file/PR tools only when the "
            "user asks to modify the repository. Never invent unseen code. Explain what "
            "you changed and what should be tested."
        ),
        tool_names=[
            "github_list_repos", "github_get_file", "github_search_code",
            "github_create_branch", "github_write_file", "github_create_pr",
            "run_code", "search",
        ],
    ),
    "general": Agent(
        key="general",
        persona=(
            "Act as the GENERAL assistant. Handle conversation, reminders, "
            "tasks, web search, daily briefings, calculations, images, and "
            "document questions when appropriate."
        ),
        tool_names=[
            "create_reminder", "list_tasks", "search", "run_code",
            "ask_document", "deep_research", "daily_briefing", "calendar_list", "calendar_create_event",
            "gmail_search", "gmail_get_message", "gmail_send", "create_workflow",
            "github_list_repos", "github_get_file", "github_search_code",
        ],
    ),
}

_CODING_KEYWORDS = (
    "code", "coding", "program", "programming", "github", "repository", "repo",
    "pull request", "pull-request", "commit", "branch", "bug", "debug", "fix my code",
    "edit my code", "modify the project", "implement", "refactor", "function", "api",
)
_MATH_KEYWORDS = (
    "calculate", "compute", "solve", "equation", "how many",
    "what is the sum", "what's the sum", "average of", "derivative",
    "factorial", "prime", "sort this list", "logic puzzle",
)
_DOCUMENT_KEYWORDS = (
    "my document", "the document", "uploaded file", "my pdf",
    "in the file", "in my file", "uploaded document",
)


def classify_agent(user_text: str) -> Agent:
    text = (user_text or "").lower()
    if any(k in text for k in _DOCUMENT_KEYWORDS):
        return AGENTS["document"]
    if any(k in text for k in _CODING_KEYWORDS):
        return AGENTS["coding"]
    if any(k in text for k in _MATH_KEYWORDS):
        return AGENTS["math"]
    return AGENTS["general"]


def system_prompt_for(agent: Agent, user=None, db=None) -> str:
    assistant_name = getattr(user, "assistant_name", None) or "VoxMate"
    tone = getattr(user, "tone", None) or "casual"

    extra_tools = None
    if agent.key == "general" and db is not None and user is not None:
        try:
            from app.tools.registry import list_webhook_tool_descriptions
            extra_tools = list_webhook_tool_descriptions(db, user)
        except Exception:
            extra_tools = None

    return build_system_prompt(
        agent.persona,
        agent.tool_names,
        assistant_name=assistant_name,
        tone=tone,
        extra_tool_descriptions=extra_tools,
    )
