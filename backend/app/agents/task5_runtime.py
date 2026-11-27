"""Offline-first teaching runtime for Task 5: AI agents, tools and automation.

The production VoxMate path remains SessionOrchestrator + Gemini function calling.
This small deterministic runtime makes the full agent loop reproducible in tests
without network access or paid model credentials.
"""
from __future__ import annotations

import ast
import json
import math
import operator
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any, Callable


class AgentSafetyError(ValueError):
    """Raised when a requested action violates the demo agent's policy."""


@dataclass
class AgentState:
    user_id: str
    session_id: str
    status: str = "idle"
    last_tool: str | None = None
    steps: int = 0


class Task5Store:
    """SQLite-backed session state and user-scoped long-term memory."""
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS agent_sessions (
                user_id TEXT NOT NULL, session_id TEXT NOT NULL,
                state_json TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(user_id, session_id)
            );
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, memory_key TEXT NOT NULL, memory_value TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, memory_key)
            );
        """)
        self.db.commit()

    def save_state(self, state: AgentState) -> None:
        self.db.execute(
            "INSERT INTO agent_sessions(user_id,session_id,state_json) VALUES(?,?,?) "
            "ON CONFLICT(user_id,session_id) DO UPDATE SET state_json=excluded.state_json, "
            "updated_at=CURRENT_TIMESTAMP",
            (state.user_id, state.session_id, json.dumps(asdict(state))),
        )
        self.db.commit()

    def load_state(self, user_id: str, session_id: str) -> AgentState:
        row = self.db.execute(
            "SELECT state_json FROM agent_sessions WHERE user_id=? AND session_id=?",
            (user_id, session_id),
        ).fetchone()
        return AgentState(**json.loads(row["state_json"])) if row else AgentState(user_id, session_id)

    def remember(self, user_id: str, key: str, value: str) -> None:
        if not key.strip() or not value.strip():
            raise ValueError("Memory key and value are required")
        self.db.execute(
            "INSERT INTO agent_memory(user_id,memory_key,memory_value) VALUES(?,?,?) "
            "ON CONFLICT(user_id,memory_key) DO UPDATE SET memory_value=excluded.memory_value",
            (user_id, key.strip(), value.strip()),
        )
        self.db.commit()

    def recall(self, user_id: str) -> list[dict[str, str]]:
        rows = self.db.execute(
            "SELECT memory_key,memory_value FROM agent_memory WHERE user_id=? ORDER BY id",
            (user_id,),
        ).fetchall()
        return [{"key": r["memory_key"], "value": r["memory_value"]} for r in rows]


# Arithmetic is parsed as an AST; eval/exec are deliberately never used.
_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

def safe_calculate(expression: str) -> float | int:
    if len(expression) > 160:
        raise AgentSafetyError("Expression is too long")
    def visit(node):
        if isinstance(node, ast.Expression): return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float): return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 8:
                raise AgentSafetyError("Exponent is outside the allowed range")
            result = _BINOPS[type(node.op)](left, right)
            if isinstance(result, complex) or not math.isfinite(float(result)):
                raise AgentSafetyError("Only finite real-number results are allowed")
            if abs(result) > 10**12:
                raise AgentSafetyError("Result exceeds the allowed range")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](visit(node.operand))
        raise AgentSafetyError("Only basic arithmetic is allowed")
    try:
        return visit(ast.parse(expression, mode="eval"))
    except AgentSafetyError:
        raise
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise AgentSafetyError("Invalid arithmetic expression") from exc


class Task5Agent:
    """Understand -> decide -> call a registered tool -> process -> respond."""
    def __init__(self, store: Task5Store | None = None,
                 external_fetch: Callable[[str], dict] | None = None):
        self.store = store or Task5Store()
        self.external_fetch = external_fetch or self._safe_http_get
        self.tools = {
            "calculator": self._calculator,
            "remember": self._remember,
            "recall_memory": self._recall_memory,
            "external_api_get": self._external_api_get,
            "database_read": self._database_read,
        }

    def run(self, user_id: str, session_id: str, request: str) -> dict[str, Any]:
        if not user_id or not session_id or not request.strip():
            raise ValueError("user_id, session_id and request are required")
        state = self.store.load_state(user_id, session_id)
        state.status = "running"
        tool_name, arguments = self._decide(request)
        result: Any = None
        if tool_name:
            tool = self.tools.get(tool_name)
            if tool is None:
                raise AgentSafetyError("Tool is not registered")
            result = tool(user_id, arguments)
            state.last_tool = tool_name
            state.steps += 1
        state.status = "completed"
        self.store.save_state(state)
        return {
            "response": self._respond(request, tool_name, result),
            "agent_state": asdict(state),
            "decision": {"tool": tool_name, "arguments": arguments},
            "tool_result": result,
            "memory": self.store.recall(user_id),
        }

    def _decide(self, request: str) -> tuple[str | None, dict]:
        text = request.strip()
        lower = text.lower()
        if lower.startswith("remember ") and "=" in text:
            key, value = text[9:].split("=", 1)
            return "remember", {"key": key.strip(), "value": value.strip()}
        if "what do you remember" in lower or "recall my memory" in lower:
            return "recall_memory", {}
        if lower.startswith("calculate "):
            return "calculator", {"expression": text[10:].strip()}
        if lower.startswith("api get "):
            return "external_api_get", {"url": text[8:].strip()}
        if lower.startswith("database read "):
            # This demo only exposes a fixed, read-only query interface.
            return "database_read", {"query": text[14:].strip()}
        return None, {}

    def _calculator(self, _user, args):
        return {"value": safe_calculate(args["expression"])}

    def _remember(self, user_id, args):
        self.store.remember(user_id, args["key"], args["value"])
        return {"saved": True, "key": args["key"]}

    def _recall_memory(self, user_id, _args):
        return {"items": self.store.recall(user_id)}

    def _external_api_get(self, _user, args):
        return self.external_fetch(args["url"])

    def _database_read(self, _user, args):
        query = args["query"].strip()
        if not query.lower().startswith("select ") or ";" in query or "--" in query:
            raise AgentSafetyError("Only a single read-only SELECT query is permitted")
        # The demo database is the agent's own memory store; no arbitrary SQL mutation.
        try:
            rows = self.store.db.execute(query).fetchmany(50)
        except sqlite3.Error as exc:
            raise AgentSafetyError("Database query rejected") from exc
        return {"rows": [dict(r) for r in rows]}

    @staticmethod
    def _safe_http_get(url: str) -> dict:
        parsed = urllib.parse.urlparse(url)
        allowed_hosts = {"api.github.com", "jsonplaceholder.typicode.com", "worldtimeapi.org"}
        if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
            raise AgentSafetyError("External API host is not allowlisted (HTTPS required)")
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise AgentSafetyError("External API redirects are disabled")
        request = urllib.request.Request(url, headers={"User-Agent": "VoxMate-Task5-Demo/1.0"})
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=5) as response:
            if response.status != 200: raise AgentSafetyError("External API request failed")
            raw = response.read(100_000)
        try: data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError): data = {"text": raw.decode("utf-8", "replace")}
        return {"status": 200, "data": data}

    @staticmethod
    def _respond(request: str, tool: str | None, result: Any) -> str:
        if tool == "calculator": return f"The calculated result is {result['value']}."
        if tool == "remember": return f"I saved '{result['key']}' in your private memory."
        if tool == "recall_memory": return f"I found {len(result['items'])} saved memory item(s)."
        if tool == "external_api_get": return "The external API request completed; see the structured result."
        if tool == "database_read": return f"The read-only database query returned {len(result['rows'])} row(s)."
        return f"I understand your request: {request}. No external tool was needed."
