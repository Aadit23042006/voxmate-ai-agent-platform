# Phase 5 — Platform

VoxMate Phase 5 adds four additive platform capabilities:

1. **Multi-Agent system** — delegates a task to independent specialist workers and a lead synthesizer.
2. **Plugin marketplace** — safe declarative marketplace entries that enable existing VoxMate tools per user.
3. **Custom agents/personas** — user-owned agent names, instructions and tool preferences.
4. **Analytics dashboard** — sessions, messages, tools, latency, agent runs, installed plugins and top tools.

## API
- `GET/POST/PUT/DELETE /platform/agents`
- `GET /platform/plugins`
- `POST/DELETE /platform/plugins/{id}/install`
- `POST /platform/multi-agent`
- `GET /platform/analytics`

The marketplace intentionally does **not** execute arbitrary downloaded Python/JavaScript. Marketplace entries map to already-registered VoxMate tools. This keeps the platform extensible without turning plugin installation into remote-code execution.

## Mobile
Settings → Developer capabilities → **Open Platform** exposes Agents, Marketplace, Analytics and Multi-Agent.

Existing voice, memory, workflows, knowledge/RAG, coding/GitHub and productivity features remain intact.
