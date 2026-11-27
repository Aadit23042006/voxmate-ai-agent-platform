from types import SimpleNamespace

import app.agents.orchestrator as orchestrator_module
from app.agents.orchestrator import SessionOrchestrator
from app.agents.planner import build_plan
from app.agents.router import AGENTS


class FakeSearchTool:
    name = "search"

    def __init__(self):
        self.executions = []

    def run(self, db, user, arguments):
        self.executions.append(arguments)
        return {"answer": "This should never execute."}


class FakeLLMClient:
    def __init__(self):
        self.calls = []

    def generate_content(self, contents, config):
        self.calls.append(list(contents))

        if len(self.calls) == 1:
            call = SimpleNamespace(
                name="search",
                args={"query": "restricted search"},
                id="unauthorized-call-001",
            )
            content = SimpleNamespace(
                parts=[SimpleNamespace(function_call=call)]
            )
            return SimpleNamespace(
                candidates=[SimpleNamespace(content=content)],
                text=None,
            )

        content = SimpleNamespace(
            parts=[
                SimpleNamespace(
                    text="The restricted tool was rejected."
                )
            ]
        )
        return SimpleNamespace(
            candidates=[SimpleNamespace(content=content)],
            text="The restricted tool was rejected.",
        )


def test_agent_cannot_execute_unauthorized_tool(monkeypatch):
    fake_llm = FakeLLMClient()
    fake_search = FakeSearchTool()
    orchestrator = SessionOrchestrator()

    monkeypatch.setattr(
        orchestrator_module,
        "get_llm_client",
        lambda: fake_llm,
    )
    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        lambda name, db=None, user=None: (
            fake_search if name == "search" else None
        ),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "confirmation_required",
        lambda name: False,
    )
    monkeypatch.setattr(
        orchestrator_module,
        "validate_tool_arguments",
        lambda tool, args: args,
    )

    monkeypatch.setattr(
        orchestrator,
        "_append_tool_result",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "_mark_plan_tool",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "_finish_plan",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "_learn_from_turn",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "_plan_dict",
        lambda *args, **kwargs: None,
    )

    # Document agent is allowed to use ask_document, not search.
    agent = AGENTS["document"]
    assert "search" not in agent.tool_names

    plan = build_plan(
        "Ask a question about my document",
        agent.tool_names,
    )

    result = orchestrator._run_model_loop(
        session_id="unauthorized-tool-test",
        agent=agent,
        config=None,
        history=[],
        db=None,
        user=None,
        plan=plan,
    )

    # Unauthorized tool must never execute.
    assert fake_search.executions == []

    # Orchestrator should return the rejection to Gemini.
    assert len(fake_llm.calls) == 2

    function_response = (
        fake_llm.calls[1][-1].parts[0].function_response
    )
    assert function_response.name == "search"
    assert "not available to this agent" in (
        function_response.response["error"]
    )

    # No successful tool result should be recorded.
    assert result.tool_results == []
    assert result.text == "The restricted tool was rejected."
