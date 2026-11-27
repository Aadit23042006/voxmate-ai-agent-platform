from app.agents.router import classify_agent
from app.tools.registry import TOOL_REGISTRY, TOOL_SCHEMAS
from app.tools.security import confirmation_required


def test_coding_agent_routes_github_requests():
    assert classify_agent("inspect my GitHub repository and fix the login bug").key == "coding"


def test_github_tools_registered():
    expected = {
        "github_list_repos", "github_get_file", "github_search_code",
        "github_create_branch", "github_write_file", "github_create_pr",
    }
    assert expected.issubset(TOOL_REGISTRY)
    assert expected.issubset(TOOL_SCHEMAS)


def test_github_mutations_require_confirmation():
    assert confirmation_required("github_create_branch")
    assert confirmation_required("github_write_file")
    assert confirmation_required("github_create_pr")
    assert not confirmation_required("github_get_file")
    assert not confirmation_required("github_search_code")
