"""Deep Research: iterative grounded searches followed by synthesis."""
import json
from app.tools.base import BaseTool, ToolError
from app.agents.llm_client import web_search, get_llm_client
from app.models.models import ResearchReport

class DeepResearchTool(BaseTool):
    name = "deep_research"

    def validate(self, arguments):
        q = (arguments or {}).get("query")
        if not q or not isinstance(q, str):
            raise ToolError("deep_research requires a non-empty query")
        depth = int((arguments or {}).get("depth", 3))
        return {"query": q.strip(), "depth": max(2, min(depth, 5))}

    def run(self, db, user, arguments):
        args = self.validate(arguments)
        q = args["query"]
        # Deliberately different angles to reduce single-result bias.
        angles = [
            f"{q} overview key facts latest developments",
            f"{q} evidence statistics primary sources risks limitations",
            f"{q} expert analysis alternatives practical implications",
            f"{q} recent news updates {q}",
            f"{q} official documentation research sources",
        ][:args["depth"]]
        findings, sources = [], []
        for angle in angles:
            try:
                r = web_search(angle)
                findings.append({"query": angle, "answer": r.get("answer", "")})
                sources.extend(r.get("sources", []))
            except Exception as exc:
                findings.append({"query": angle, "error": str(exc)})
        # Deduplicate sources while preserving order.
        seen = set(); unique_sources = []
        for s in sources:
            u = s.get("url")
            if u and u not in seen:
                seen.add(u); unique_sources.append(s)
        synthesis_prompt = (
            "You are VoxMate Deep Research. Synthesize the research below into "
            "a factual, structured answer. Clearly distinguish evidence from "
            "inference, mention uncertainty/conflicting evidence, and finish "
            "with a concise Sources section. Do not invent citations.\n\n"
            f"QUESTION:\n{q}\n\nRESEARCH:\n{json.dumps(findings, ensure_ascii=False)}\n\n"
            f"SOURCES:\n{json.dumps(unique_sources, ensure_ascii=False)}"
        )
        response = get_llm_client().generate_content(contents=synthesis_prompt)
        answer = getattr(response, "text", str(response))
        row = ResearchReport(user_id=user.id, query=q, answer=answer, sources=unique_sources)
        db.add(row); db.commit(); db.refresh(row)
        return {"report_id": row.id, "query": q, "answer": answer, "sources": unique_sources}
