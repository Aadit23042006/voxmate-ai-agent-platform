# Task 6 Acceptance Test

Run from the repository root.

1. `cd backend`
2. `pip install -r requirements.txt`
3. Create `.env` from `.env.example` and set `GEMINI_API_KEY`.
4. `uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Open `/`.
6. Ask `How does the RAG pipeline work?` and verify an answer plus source metadata.
7. Ask `Calculate 125 * 48` and verify the calculator tool appears in the plan/results.
8. Ask `What is VoxMate?` and verify Gemini returns a grounded project answer.
9. Open `/docs` and verify `/api/chat` and `/api/capstone/health`.
10. `pytest` must pass without requiring a live Gemini call.

## Evidence for company review

- GenAI UI: `backend/app/static/index.html`
- Gemini client: `backend/app/agents/llm_client.py`
- Agent planner + grounded generation: `backend/app/capstone/service.py`
- RAG: `backend/app/capstone/service.py` + `backend/app/rag/`
- Tools: `backend/app/tools/` + Task 6 safe tools
- Architecture: `docs/task6/ARCHITECTURE.md`
- Demo: `docs/task6/DEMO_SCRIPT.md`
