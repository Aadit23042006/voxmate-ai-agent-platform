"""Additive agent planning layer for VoxMate.

The planner is deliberately local and deterministic: it creates an explicit
execution plan before Gemini's function-calling loop. Gemini remains the
reasoning/argument-selection engine, so existing behavior is preserved.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
import re
import uuid


@dataclass
class PlanStep:
    id: str
    tool: str
    purpose: str
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class AgentPlan:
    id: str
    goal: str
    steps: List[PlanStep]
    status: str = "active"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status,
            "steps": [
                {
                    "id": s.id,
                    "tool": s.tool,
                    "purpose": s.purpose,
                    "depends_on": s.depends_on,
                    "status": s.status,
                }
                for s in self.steps
            ],
        }


def build_plan(user_text: str, available_tools: List[str]) -> AgentPlan:
    text = (user_text or "").strip()
    lower = text.lower()
    steps: List[PlanStep] = []

    def add(tool: str, purpose: str):
        if tool in available_tools and not any(s.tool == tool for s in steps):
            sid = str(uuid.uuid4())
            deps = [steps[-1].id] if steps and _looks_sequential(lower, tool, steps[-1].tool) else []
            steps.append(PlanStep(sid, tool, purpose, deps))

    # Explicit multi-step intent first.
    if any(x in lower for x in ("research", "find", "look up", "search")):
        add("search", "Gather current information and sources.")

    if any(x in lower for x in ("calculate", "compute", "solve", "total", "average")):
        add("run_code", "Verify calculations or logic safely.")

    if any(x in lower for x in ("document", "pdf", "uploaded file", "my file")):
        add("ask_document", "Retrieve relevant information from the user's documents.")

    if any(x in lower for x in ("remind me", "reminder", "remember at", "set a reminder", "add a task")):
        add("create_reminder", "Create the requested reminder/task after confirmation if required.")

    if any(x in lower for x in ("what tasks", "my tasks", "pending tasks", "list tasks")):
        add("list_tasks", "Retrieve the user's current tasks.")

    if any(x in lower for x in ("daily briefing", "briefing", "what do i have today")):
        add("daily_briefing", "Build a concise briefing from pending tasks.")

    if any(x in lower for x in ("calendar", "schedule", "meeting", "appointment")):
        add("calendar_list", "Check upcoming calendar events.")
        if any(x in lower for x in ("create", "schedule", "book", "add")):
            add("calendar_create_event", "Create the requested calendar event.")
    if any(x in lower for x in ("gmail", "email", "inbox", "mail")):
        add("gmail_search", "Search Gmail for relevant messages.")
        if any(x in lower for x in ("read", "open", "show", "message")):
            add("gmail_get_message", "Read the requested Gmail message.")
        if any(x in lower for x in ("send", "email to", "mail to")):
            add("gmail_send", "Send the requested email after confirmation.")
    if any(x in lower for x in ("workflow", "automate", "automation", "every morning", "every day")):
        add("create_workflow", "Create the requested automation workflow.")

    if not steps:
        steps.append(PlanStep(
            id=str(uuid.uuid4()),
            tool="conversation",
            purpose="Understand the request and respond directly.",
        ))

    return AgentPlan(id=str(uuid.uuid4()), goal=text, steps=steps)


def _looks_sequential(text: str, current: str, previous: str) -> bool:
    if previous == "search" and current in {"run_code", "create_reminder", "daily_briefing"}:
        return any(x in text for x in ("then", "after", "based on", "and remind", "and set"))
    return False
