# Task 5 — Module 05: AI Agents, Tools & Automation

**Project:** VoxMate — Agentic Voice & Workflow Assistant  
**Scope:** Additive Task 5 implementation. Existing voice, authentication, integrations, mobile client, RAG, tools and APIs are retained.

## Requirement-to-implementation traceability

| Company objective | Implementation evidence | How to demonstrate |
|---|---|---|
| Understand AI agents, state management, chatbot vs agent | `backend/app/agents/orchestrator.py`, `planner.py`, `router.py`; `task5_runtime.py` | Run `python examples/task5_agent_demo.py`; inspect returned `decision`, `tool_result`, `agent_state`. |
| Function/tool calling and connect LLMs to external APIs and databases | Gemini function declarations and execution in `tools/registry.py` + `agents/orchestrator.py`; integrations in `tools/search_tool.py`, `google_tools.py`, `github_tools.py`; Task 5 API and database tools in `task5_runtime.py` | Inspect tool schemas and run the offline tests. Live integrations require the user's own provider credentials. |
| Agent memory and state; frameworks, safety and limitations | `memory/memory_service.py`, `models/models.py`, `tools/security.py`, `task5_runtime.py` | Use `remember ... = ...` then `recall my memory`; tests verify per-user isolation, state persistence and safety. |
| Working agent: Understand → Decide → Use Tool → Process Result → Respond | `Task5Agent.run()` and production `SessionOrchestrator.handle_turn()` | Demo a calculation, memory action, read-only DB query, or allowlisted API request. |
| GitHub Repo + LinkedIn Post deliverables | Root `README.md`, `GITHUB_SETUP.md`, `docs/task5/LINKEDIN_POST.md` | Publish this project to the user's GitHub account and publish/adapt the included post. |

## Chatbot vs agent

- **Chatbot:** primarily maps a message to a conversational response.
- **Agent:** interprets a goal, selects an action/tool, checks policy, executes the action, observes the result, updates state/memory and responds. It may perform multiple steps when required.

VoxMate's production implementation uses Gemini function calling. The deterministic Task 5 runtime is an offline reproducible demonstration of the same lifecycle; it is not a replacement for the production Gemini orchestrator.

## Architecture

```text
User request
    ↓
Agent router / intent understanding
    ↓
Planner creates observable plan
    ↓
Policy + tool allowlist + approval gate
    ↓
Gemini function call (production) / deterministic decision (offline demo)
    ↓
Tool registry → API / database / calculation / memory tool
    ↓
Tool result returned to agent
    ↓
Agent state + memory updated
    ↓
Final response + execution events
```

## Tool and integration examples

- **LLM:** Google Gemini client (`backend/app/agents/llm_client.py`); mock fallback supports local development without a key.
- **External APIs:** web search, GitHub, Google Calendar/Gmail and user-configured webhooks are exposed through registered tools. The Task 5 standalone demo adds an HTTPS host allowlist for its API GET tool.
- **Database:** SQLAlchemy-backed app models persist users, sessions, plans, tool approvals, tasks and memories. The standalone demo uses SQLite to persist scoped state/memory and permits only read-only SELECT access through its database demonstration tool.
- **Memory:** explicit user facts/preferences are saved and relevant context can be recalled; demo memory is scoped by `user_id`.

## Safety controls

- Tool declarations are restricted by the selected agent's allowed tool list.
- Mutating tools can require explicit user confirmation before execution.
- Tool arguments are validated before a tool runs.
- The standalone calculator parses a restricted arithmetic AST; it never uses `eval` or `exec`.
- The standalone external API tool requires HTTPS and an allowlisted hostname; the standalone DB tool rejects mutation statements.
- Memory and session state are scoped by user ID.

## Known limitations (disclose in review)

- A live Gemini API key is required for real LLM responses; mock mode is for local testing and does not prove model quality.
- Calendar, Gmail, GitHub and webhook actions require user-owned credentials/consent and appropriate scopes. They are not represented as connected unless configured.
- The deterministic Task 5 demo intentionally supports a small command set. The production Gemini orchestrator is the natural-language path.
- The standalone API allowlist is a teaching/demo boundary. Production deployments should add egress controls, DNS/IP rebinding protections, request budgets, audit retention and secret management at the infrastructure layer.
- The existing app documentation notes that schema creation currently uses SQLAlchemy `create_all`; production schema evolution should use versioned Alembic migrations.
- This ZIP cannot publish a GitHub repository or LinkedIn post on the user's behalf; those require signing in to the user's accounts.

## Run and verify

```bash
# From project root; Python 3.11+ recommended
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt
python -m pytest tests/test_task5_runtime.py -v
python examples/task5_agent_demo.py
```

Demo commands:

```text
calculate 12 * (4 + 3)
remember preferred_language = Hindi
recall my memory
database read SELECT memory_key, memory_value FROM agent_memory
```

The API example performs a real request only when the user enters an HTTPS URL on the allowlist (`api.github.com`, `jsonplaceholder.typicode.com`, or `worldtimeapi.org`). Unit tests inject a fake fetcher and do not require network access.
