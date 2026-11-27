from types import SimpleNamespace

import app.agents.orchestrator as orchestrator_module
from app.agents.orchestrator import SessionOrchestrator
from app.agents.planner import build_plan
from app.agents.router import AGENTS


class FailingSearchTool:
    name = "search"

    def run(self, db, user, arguments):
        raise RuntimeError("Simulated search service failure")


class FakeLLMClient:
    def __init__(self):
        self.calls = []

    def generate_content(self, contents, config):
        self.calls.append(list(contents))

        if len(self.calls) == 1:
            call = SimpleNamespace(
                name="search",
                args={"query": "Python developer jobs"},
                id="failing-search-001",
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
                    text="Search failed, but I recovered and can continue."
                )
            ]
        )
        return SimpleNamespace(
            candidates=[SimpleNamespace(content=content)],
            text="Search failed, but I recovered and can continue.",
        )


def test_tool_failure_is_returned_to_model_without_crashing(monkeypatch):
    fake_llm = FakeLLMClient()
    failing_tool = FailingSearchTool()
    orchestrator = SessionOrchestrator()

    monkeypatch.setattr(
        orchestrator_module, "get_llm_client", lambda: fake_llm
    )
    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        lambda name, db=None, user=None: (
            failing_tool if name == "search" else None
        ),
    )
    monkeypatch.setattr(
        orchestrator_module, "confirmation_required", lambda name: False
    )
    monkeypatch.setattr(
        orchestrator_module,
        "validate_tool_arguments",
        lambda tool, args: args,
    )

    monkeypatch.setattr(
        orchestrator, "_append_tool_result", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        orchestrator, "_mark_plan_tool", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        orchestrator, "_finish_plan", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        orchestrator, "_learn_from_turn", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        orchestrator, "_plan_dict", lambda *a, **kw: None
    )

    agent = AGENTS["general"]
    plan = build_plan(
        "Search for Python developer jobs",
        agent.tool_names,
    )

    result = orchestrator._run_model_loop(
        session_id="tool-failure-recovery-test",
        agent=agent,
        config=None,
        history=[],
        db=None,
        user=None,
        plan=plan,
    )

    assert len(fake_llm.calls) == 2
    assert len(result.tool_results) == 1
    assert result.tool_results[0]["tool"] == "search"
    assert result.tool_results[0]["status"] == "error"
    assert "Simulated search service failure" in (
        result.tool_results[0]["result"]["error"]
    )

    function_response = (
        fake_llm.calls[1][-1].parts[0].function_response
    )
    assert function_response.name == "search"
    assert "Simulated search service failure" in (
        function_response.response["error"]
    )

    assert result.text == (
        "Search failed, but I recovered and can continue."
    )
