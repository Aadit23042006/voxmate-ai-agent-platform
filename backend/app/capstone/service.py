from __future__ import annotations

import ast
import json
import operator as op
import re
from pathlib import Path
from datetime import datetime, timezone

from app.agents.llm_client import LLMClient
from app.config import settings

_ALLOWED_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv,
}
_ALLOWED_UNARY = {ast.UAdd: op.pos, ast.USub: op.neg}


class CapstoneService:
    """Small, auditable Task 6 demo pipeline built on VoxMate's existing Gemini stack."""

    def __init__(self) -> None:
        self.llm = LLMClient(api_key=settings.gemini_api_key)
        self.knowledge = self._load_knowledge()

    def _load_knowledge(self) -> list[tuple[str, str]]:
        root = Path(__file__).resolve().parents[2] / "knowledge"
        root.mkdir(parents=True, exist_ok=True)
        results = []
        for p in root.glob("*.md"):
            results.append((p.name, p.read_text(encoding="utf-8")))
        return results

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+", text.lower()))

    def retrieve(self, query: str, k: int = 4) -> list[tuple[str, str]]:
        q = self._tokens(query)
        scored = []
        for source, text in self.knowledge:
            for chunk in re.split(r"\n\s*\n", text):
                chunk = chunk.strip()
                if not chunk:
                    continue
                words = self._tokens(chunk)
                score = len(q & words) / max(1, len(q))
                if score:
                    scored.append((score, source, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(source, chunk) for _, source, chunk in scored[:k]]

    @staticmethod
    def _safe_calculate(expression: str) -> str:
        expression = expression.strip().replace("^", "**")
        if len(expression) > 120 or not re.fullmatch(r"[0-9+\-*/%().\s*]+", expression):
            raise ValueError("Only basic arithmetic is allowed.")
        node = ast.parse(expression, mode="eval").body

        def ev(n):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return n.value
            if isinstance(n, ast.UnaryOp) and type(n.op) in _ALLOWED_UNARY:
                return _ALLOWED_UNARY[type(n.op)](ev(n.operand))
            if isinstance(n, ast.BinOp) and type(n.op) in _ALLOWED_BINOPS:
                return _ALLOWED_BINOPS[type(n.op)](ev(n.left), ev(n.right))
            raise ValueError("Unsupported arithmetic expression.")

        return str(ev(node))

    def _plan(self, message: str) -> list[str]:
        """Use Gemini for agent planning, with a deterministic safe fallback."""
        planner_prompt = f"""
You are the VoxMate Task 6 agent planner.
Return ONLY a JSON array containing zero or more of these action names:
["retrieve_knowledge", "calculator", "current_time", "direct"]
Choose retrieve_knowledge for project/VoxMate/RAG/agent/Gemini questions.
Choose calculator for arithmetic. Choose current_time for time questions.
Use direct for normal conversation.
User request: {message}
"""
        try:
            response = self.llm.generate_content(prompt=planner_prompt, system_instruction="Return valid JSON only. Never include markdown.", temperature=0.0, max_output_tokens=120)
            raw = getattr(response, "text", "") or ""
            match = re.search(r"\[[\s\S]*?\]", raw)
            if match:
                actions = json.loads(match.group(0))
                allowed = {"retrieve_knowledge", "calculator", "current_time", "direct"}
                cleaned = [a for a in actions if a in allowed]
                if cleaned:
                    return cleaned
        except Exception:
            pass
        text = message.lower()
        if re.search(r"\b(calculate|compute|solve)\b|[0-9]+\s*[+\-*/%]\s*[0-9]+", text):
            return ["calculator"]
        if any(x in text for x in ("current time", "what time", "time now")):
            return ["current_time"]
        if any(x in text for x in ("voxmate", "rag", "agent", "gemini", "project", "architecture", "capstone")):
            return ["retrieve_knowledge"]
        return ["direct"]

    def run(self, message: str, session_history: list[dict] | None = None) -> dict:
        plan = self._plan(message)
        sources: list[tuple[str, str]] = []
        tools: list[dict] = []

        if "retrieve_knowledge" in plan:
            sources = self.retrieve(message)
        elif "calculator" in plan:
            expression = re.sub(r"(?i)^.*?\b(calculate|compute|solve)\b", "", message).strip(" :?")
            if not expression:
                expression = message
            try:
                tools.append({"tool": "calculator", "result": self._safe_calculate(expression)})
            except Exception as exc:
                tools.append({"tool": "calculator", "error": str(exc)})
        elif "current_time" in plan:
            tools.append({"tool": "current_time", "result": datetime.now(timezone.utc).astimezone().isoformat()})

        context = "\n\n".join(f"[Source: {s}]\n{c}" for s, c in sources) or "(no retrieved project evidence)"
        tool_text = "\n".join(f"{t['tool']}: {t.get('result', t.get('error'))}" for t in tools) or "(no tool execution)"
        history = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in (session_history or [])[-6:]) or "(new session)"

        system = (
            "You are VoxMate's Task 6 capstone assistant. Use the supplied project evidence and tool results. "
            "Never invent project features or sources. If evidence is absent, say that clearly. "
            "Be concise and answer in the user's language."
        )
        prompt = f"""User request:\n{message}\n\nAgent plan: {plan}\n\nProject evidence:\n{context}\n\nTool results:\n{tool_text}\n\nRecent history:\n{history}\n\nGive the final answer."""
        answer = self.llm.generate_content(prompt=prompt, system_instruction=system, temperature=0.2, max_output_tokens=900).text
        return {
            "answer": answer.strip() if answer else "Gemini returned an empty response.",
            "plan": plan,
            "sources": [s for s, _ in sources],
            "tool_results": tools,
        }

