# Phase 2 — Real-world productivity

This upgrade is additive to the Phase 1 VoxMate project.

## 1. Google Calendar + Gmail

VoxMate now includes OAuth2 connection and agent tools:
- `calendar_list`
- `calendar_create_event`
- `gmail_search`
- `gmail_get_message`
- `gmail_send`

Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` in `.env`.
In Google Cloud Console, enable **Google Calendar API** and **Gmail API**, and add the
redirect URI exactly as configured.

The mobile Settings screen has **Connect Google Calendar + Gmail**. Google access
tokens are stored server-side in the new `google_connections` table.

Mutating actions (`calendar_create_event`, `gmail_send`) use the existing Phase 1
tool-confirmation security layer.

## 2. Smart notifications

- Expo push tokens are stored in `notification_devices`.
- Notifications are durable in `notifications`.
- The Celery worker checks scheduled notifications every minute.
- The mobile Settings screen can request permission and register the device.

Install the new mobile packages with `npm install` after pulling this upgrade.
For a production Expo build, configure an EAS project ID.

## 3. Workflow automation

New `workflows` table and REST endpoints:
- `POST /integrations/workflows`
- `GET /integrations/workflows`
- `POST /integrations/workflows/{id}/run`

Triggers currently supported:
- `schedule` — `{"interval_minutes": 60}`
- `task_due` — `{"within_minutes": 30}`

Actions:
- `notify`
- `send_email`
- `calendar_event`
- `reminder`

The agent can also create workflows through `create_workflow`; Phase 1 confirmation
is required because a workflow can cause external side effects.

## Google setup

The OAuth callback is `/integrations/google/callback`. For a phone connected to a
local development backend, use a reachable HTTPS/tunnel callback or your deployed
backend URL rather than `localhost`.

## Important

This phase does not replace or remove the existing Gemini, voice, WebSocket,
authentication, memory, planner, tool execution, or UI code. It adds integration
services, tools, tables, endpoints, and settings controls.
