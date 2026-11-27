import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest
from app.agents.task5_runtime import Task5Agent, Task5Store, AgentSafetyError, safe_calculate


def test_agent_understand_decide_use_tool_process_respond():
    agent = Task5Agent(Task5Store())
    result = agent.run("u1", "s1", "calculate 12 * (4 + 3)")
    assert result["decision"]["tool"] == "calculator"
    assert result["tool_result"] == {"value": 84}
    assert result["response"] == "The calculated result is 84."
    assert result["agent_state"]["status"] == "completed"


def test_memory_persists_and_is_user_scoped():
    store = Task5Store()
    agent = Task5Agent(store)
    agent.run("alice", "s1", "remember preferred_language = Hindi")
    assert agent.run("alice", "s2", "recall my memory")["tool_result"]["items"] == [
        {"key": "preferred_language", "value": "Hindi"}
    ]
    assert agent.run("bob", "s2", "recall my memory")["tool_result"]["items"] == []


def test_session_state_is_scoped_and_persisted():
    store = Task5Store()
    agent = Task5Agent(store)
    agent.run("alice", "session-1", "calculate 2 + 2")
    state = store.load_state("alice", "session-1")
    assert state.steps == 1 and state.last_tool == "calculator"
    assert store.load_state("bob", "session-1").steps == 0


def test_safe_calculator_rejects_code_execution():
    assert safe_calculate("2 ** 3 + 1") == 9
    with pytest.raises(AgentSafetyError):
        safe_calculate("__import__('os').system('whoami')")


def test_external_api_requires_https_allowlisted_host():
    agent = Task5Agent(Task5Store(), external_fetch=lambda url: {"url": url})
    assert agent.run("u", "s", "api get https://api.github.com/repos")["tool_result"]["url"] == "https://api.github.com/repos"
    with pytest.raises(AgentSafetyError):
        Task5Agent().run("u", "s", "api get http://127.0.0.1/admin")


def test_database_tool_is_read_only():
    agent = Task5Agent(Task5Store())
    with pytest.raises(AgentSafetyError):
        agent.run("u", "s", "database read DELETE FROM agent_memory")


def test_safe_calculator_rejects_complex_and_non_finite_results():
    with pytest.raises(AgentSafetyError):
        safe_calculate("(-1) ** 0.5")
    with pytest.raises(AgentSafetyError):
        safe_calculate("1e308 * 1e308")


def test_safe_calculator_rejects_excessive_results():
    with pytest.raises(AgentSafetyError):
        safe_calculate("999999999999 * 999999999999")


def test_memory_persists_after_reopening_sqlite_store(tmp_path):
    database_path = tmp_path / "agent_state.sqlite3"
    first_store = Task5Store(str(database_path))
    first_store.remember("user-1", "preferred_language", "Hindi")
    first_store.save_state(first_store.load_state("user-1", "session-1"))
    first_store.db.close()

    reopened_store = Task5Store(str(database_path))
    assert reopened_store.recall("user-1") == [
        {"key": "preferred_language", "value": "Hindi"}
    ]
    assert reopened_store.load_state("user-1", "session-1").status == "idle"
    reopened_store.db.close()
