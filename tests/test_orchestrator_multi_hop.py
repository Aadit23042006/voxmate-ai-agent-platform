from types import SimpleNamespace

import app.agents.orchestrator as orchestrator_module
from app.agents.orchestrator import SessionOrchestrator
from app.agents.planner import build_plan
from app.agents.router import AGENTS


class FakeTool:
    def __init__(self, name, result):
        self.name = name
        self.result = result
        self.executions = []

    def run(self, db, user, arguments):
        self.executions.append(arguments)
        return self.result


class FakeLLMClient:
    def __init__(self):
        self.calls = []

    def generate_content(self, contents, config):
        self.calls.append(list(contents))
        step = len(self.calls)

        if step == 1:
            call = SimpleNamespace(
                name="search",
                args={"query": "Python developer jobs"},
                id="call-search-001",
            )
            content = SimpleNamespace(
                parts=[SimpleNamespace(function_call=call)]
            )
            return SimpleNamespace(
                candidates=[SimpleNamespace(content=content)],
                text=None,
            )

        if step == 2:
            call = SimpleNamespace(
                name="list_tasks",
                args={},
                id="call-tasks-002",
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
                    text="Search and task listing completed successfully."
                )
            ]
        )
        return SimpleNamespace(
            candidates=[SimpleNamespace(content=content)],
            text="Search and task listing completed successfully.",
        )


def test_orchestrator_executes_multiple_tool_hops(monkeypatch):
    fake_llm = FakeLLMClient()

    search_tool = FakeTool(
        "search",
        {"answer": "Found three Python jobs."},
    )
    tasks_tool = FakeTool(
        "list_tasks",
        {"tasks": [{"title": "Finish VoxMate"}]},
    )

    tools = {
        "search": search_tool,
        "list_tasks": tasks_tool,
    }

    orchestrator = SessionOrchestrator()

    monkeypatch.setattr(
        orchestrator_module,
        "get_llm_client",
        lambda: fake_llm,
    )
    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        lambda name, db=None, user=None: tools.get(name),
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
        "Search Python developer jobs and list my tasks",
        agent.tool_names,
    )

    result = orchestrator._run_model_loop(
        session_id="multi-hop-test-session",
        agent=agent,
        config=None,
        history=[],
        db=None,
        user=None,
        plan=plan,
    )

    # Two tool-call rounds followed by a final model response.
    assert len(fake_llm.calls) == 3

    # Both tools executed exactly once.
    assert len(search_tool.executions) == 1
    assert len(tasks_tool.executions) == 1

    # Both tool results were captured.
    assert len(result.tool_results) == 2
    assert [item["tool"] for item in result.tool_results] == [
        "search",
        "list_tasks",
    ]
    assert all(
        item["status"] == "success"
        for item in result.tool_results
    )

    # First tool result was sent back to Gemini.
    first_response = fake_llm.calls[1][-1].parts[0].function_response
    assert first_response.name == "search"
    assert first_response.response["answer"] == (
        "Found three Python jobs."
    )

    # Second tool result was also sent back to Gemini.
    second_response = fake_llm.calls[2][-1].parts[0].function_response
    assert second_response.name == "list_tasks"
    assert second_response.response["tasks"][0]["title"] == (
        "Finish VoxMate"
    )

    assert result.text == (
        "Search and task listing completed successfully."
    )
