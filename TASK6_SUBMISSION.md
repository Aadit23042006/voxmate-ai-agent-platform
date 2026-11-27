# Task 6 Submission Package â€” VoxMate GenAI Capstone

This repository package is aligned to the Module 06 brief shown in the Task 6 requirements screenshot.

## Required deliverables

- GitHub Repository â€” source package is GitHub-ready.
- Live Website â€” the FastAPI application serves the Task 6 web UI at `/` and includes Docker/Render deployment configuration.
- LinkedIn Post â€” `docs/task6/LINKEDIN_POST.md` is ready to publish.

## Task 6 technical requirements

- Generative AI application: `backend/app/static/index.html` + `/api/chat`
- LLM API: Google Gemini through `backend/app/agents/llm_client.py`
- Prompt Engineering: planner + grounded response prompts in `backend/app/capstone/service.py`
- RAG: `backend/app/capstone/service.py` and `backend/app/rag/`
- Tools: existing tool registry plus safe Task 6 calculator/current-time actions
- Agents: existing VoxMate routing/planning/orchestration plus Gemini Task 6 planning
- Documentation: root README and `docs/task6/`
- Architecture: `docs/task6/ARCHITECTURE.md`
- Demo: `docs/task6/DEMO_SCRIPT.md`
- Automated acceptance tests: `tests/test_task6_capstone.py`

## Gemini key

Put your own key in `.env`:

```env
GEMINI_API_KEY=YOUR_REAL_GEMINI_API_KEY
```

Never commit `.env` or paste the real key into source code.

## Verified locally

The Task 6 acceptance test passes without requiring a live Gemini request:

```text
4 passed
```

External publication/deployment actions still require the repository owner's GitHub, hosting and LinkedIn accounts.


## Security Verification

Verified security controls include:

- Environment secrets are excluded from Git using `.gitignore`.
- `.env` files are not intended for GitHub publication.
- `.env.example` contains safe placeholders only.
- Firebase and Google service-account credential files are ignored.
- Private-key and certificate files are ignored.
- Credential, token and secret files are ignored.
- Recognizable hard-coded secret-pattern scan passed.
- Production `datetime.utcnow()` audit passed with zero production occurrences.
- Production configuration is environment-driven.
- Unrestricted wildcard CORS is not configured.
- Production secrets must be supplied through secure environment-variable/secret management.


## CORS Configuration

VoxMate uses the `CORS_ALLOWED_ORIGINS` environment variable to configure trusted CORS origins.

Local configuration example:

``env
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
``

Production deployments must replace development origins with the actual trusted frontend origin(s). Wildcard `*` CORS is not used.


## Production Configuration Verification

Verified production-oriented configuration includes:

- Required database and Redis configuration is environment-driven.
- Root `.env` loading works independently of the backend working directory.
- Production environment variables can override local values.
- Docker Compose configuration is available.
- Render web-service configuration is available.
- Render health check is configured as `/health`.
- FastAPI provides `/health` for deployment monitoring.
- Production application code contains zero `datetime.utcnow()` occurrences.
- Production CORS configuration is environment-driven.
- Debug/reload configuration is not enabled in the backend.
- Recognizable hard-coded secret-pattern scan passed.

Local Docker/API verification passed for `/`, `/openapi.json`, `/docs` and `/health` with HTTP 200 responses.

The public production deployment remains dependent on the actual Render deployment and its public HTTPS URL.


