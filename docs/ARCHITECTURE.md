# VoxMate Architecture

## Flow
```
Mobile App (Expo/React Native)
   │  WebSocket (JSON events)
   ▼
Voice Gateway (FastAPI /ws/voice/{session_id})
   │  auth check, session lookup
   ▼
Agent Orchestrator (app/agents/orchestrator.py)
   │  loads short-term history, calls LLM, routes tool calls
   ├──▶ LLM client (Gemini or mock)
   ├──▶ Tool registry (reminders, tasks, search)
   └──▶ Memory service (Postgres)
   ▼
Postgres (users, sessions, messages, tasks, tool_calls, memories)
Redis (session/cache state — not yet used for session pinning in this
       scaffold; hook point is in voice_gateway.py)
```

## Why this shape
- **Stateless API/gateway**: the FastAPI process holds no long-lived
  per-user state beyond the open WebSocket connection itself; all
  conversation state is in Postgres, so you can run multiple backend
  replicas behind a load balancer.
- **Provider adapters**: `llm_client.py` and the STT/TTS stubs in
  `voice_gateway.py` isolate vendor-specific code so you can swap Gemini
  for another LLM, or add Deepgram/Google STT, without touching the
  orchestrator or tools.
- **Tool validation boundary**: every tool implements `validate()` before
  `run()`; the LLM never writes to the database directly — this matches
  the "never allow the LLM to directly modify the database without
  application-level validation" principle from the blueprint.
- **Idempotency hook**: `ToolCall.idempotency_key` exists so you can
  de-duplicate retried actions like reminder creation.

## Scaling notes (see blueprint §8)
- Run `backend` behind a load balancer with N replicas; sessions aren't
  pinned to a process because state lives in Postgres.
- Move `summarize_session` / `send_reminder_notification` off the
  request path into Celery (already wired, see `app/workers/`).
- Add Redis-backed rate limiting on `/ws/voice/*` and `/auth/*` before
  opening this up publicly.
- Add read replicas + indexes on `messages.session_id`,
  `tool_calls.session_id`, `tasks.user_id` once query volume grows.

## Load testing plan (not implemented here)
1. Use `locust` or `k6` to open N concurrent WebSocket sessions.
2. Send a fixed conversation script per session (mirrors
   `tests/manual_ws_client.py`).
3. Record: time-to-first-response, end-to-end turn latency, error rate,
   concurrent session ceiling before latency degrades.
4. Document results and bottlenecks in the README per blueprint §15.


## Background jobs (Task 5 handoff)

Celery tasks live in `backend/app/workers/tasks.py`. Session summaries use
Gemini when configured and are stored as user-scoped `Memory` rows with type
`summary`; offline mode stores a labelled transcript extract. Reminder delivery
uses the existing queued `Notification` and `NotificationDevice` records.
Celery Beat schedules pending-notification and workflow processors every
60 seconds. The worker is started with `--beat` by Docker Compose.
