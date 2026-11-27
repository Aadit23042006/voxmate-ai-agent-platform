# Task 6 — Module 06: GenAI Capstone Project

This document maps the VoxMate implementation to the company Task 6 brief.

| Company requirement | Implementation evidence | Status |
|---|---|---|
| Build a Generative AI application | `backend/app/static/index.html` + FastAPI `/api/chat` + Gemini-backed agent pipeline | Complete |
| Integrate LLM API | `backend/app/agents/llm_client.py` uses Google Gemini API with `GEMINI_API_KEY` | Complete |
| Prompt Engineering | `backend/app/capstone/service.py` contains planner and grounded-response system prompts; existing agent prompts remain in `backend/app/agents/` | Complete |
| RAG | `backend/app/rag/` + Task 6 knowledge file + capstone retrieval pipeline | Complete |
| Tools | Existing `backend/app/tools/` registry plus Task 6 safe calculator/time tools | Complete |
| Agents | Existing router/planner/orchestrator plus Gemini-backed Task 6 planner | Complete |
| GitHub Repository | Clean repository structure, README, `.gitignore`, CI and deployment files | Ready for publish |
| Documentation | Root README + Task 6 requirement mapping + architecture + demo script | Complete |
| Architecture diagram | `docs/task6/ARCHITECTURE.md` | Complete |
| Demo video | `docs/task6/DEMO_SCRIPT.md` | Ready to record |
| Live website | Root `/` serves the Task 6 web application; Docker/Render config included | Deployable; requires owner deployment |
| LinkedIn post | `docs/task6/LINKEDIN_POST.md` | Ready to publish |

## Gemini configuration

Set the user’s own key in `.env`:

```env
GEMINI_API_KEY=your_real_key_here
```

The key is intentionally not stored in Git. `.env` is ignored by `.gitignore`.

## Task 6 runtime

```text
Browser
  ↓
POST /api/chat
  ↓
Gemini Agent Planner
  ↓
RAG retrieval OR safe tool execution OR direct response
  ↓
Gemini grounded final generation
  ↓
Browser + execution metadata
```

The `/api/capstone/health` endpoint reports whether the Gemini key is configured.

## What a source ZIP cannot perform

The source package cannot authenticate into the user’s accounts or publish external assets. GitHub publication, live-host activation, video upload, and LinkedIn publication must be performed by the repository owner. The package contains the code/configuration and submission assets required for those actions.
