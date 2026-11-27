from types import SimpleNamespace

import app.agents.orchestrator as orchestrator_module
from app.agents.orchestrator import SessionOrchestrator
from app.agents.planner import build_plan
from app.agents.router import AGENTS


class FakeSearchTool:
    name = "search"

    def run(self, db, user, arguments):
        return {
            "answer": "Found three Python developer jobs.",
            "sources": ["source-1", "source-2"],
            "query": arguments["query"],
        }


class FakeLLMClient:
    def __init__(self):
        self.calls = []

    def generate_content(self, contents, config):
        self.calls.append(list(contents))

        if len(self.calls) == 1:
            function_call = SimpleNamespace(
                name="search",
                args={"query": "Python developer jobs"},
                id="call-search-001",
            )
            content = SimpleNamespace(
                parts=[
                    SimpleNamespace(function_call=function_call)
                ]
            )
            return SimpleNamespace(
                candidates=[SimpleNamespace(content=content)],
                text=None,
            )

        content = SimpleNamespace(
            parts=[
                SimpleNamespace(
                    text="I found three Python developer jobs."
                )
            ]
        )
        return SimpleNamespace(
            candidates=[SimpleNamespace(content=content)],
            text="I found three Python developer jobs.",
        )


def test_gemini_function_call_executes_tool_and_returns_result(monkeypatch):
    fake_llm = FakeLLMClient()
    fake_tool = FakeSearchTool()
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
            fake_tool if name == "search" else None
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

    agent = AGENTS["general"]
    plan = build_plan(
        "Search for Python developer jobs",
        agent.tool_names,
    )

    history = []

    result = orchestrator._run_model_loop(
        session_id="integration-test-session",
        agent=agent,
        config=None,
        history=history,
        db=None,
        user=None,
        plan=plan,
    )

    # Gemini first requested the search tool, then returned a final answer.
    assert len(fake_llm.calls) == 2

    # The real registered-tool execution path returned the expected result.
    assert len(result.tool_results) == 1
    assert result.tool_results[0]["tool"] == "search"
    assert result.tool_results[0]["status"] == "success"
    assert result.tool_results[0]["result"]["answer"] == (
        "Found three Python developer jobs."
    )

    # The tool result was forwarded to Gemini as a function response.
    second_history = fake_llm.calls[1]
    assert len(second_history) == 2

    function_response = (
        second_history[1].parts[0].function_response
    )
    assert function_response.name == "search"
    assert function_response.response["answer"] == (
        "Found three Python developer jobs."
    )

    # The final model response reached the caller.
    assert result.text == "I found three Python developer jobs."
    assert result.agent == "general"
