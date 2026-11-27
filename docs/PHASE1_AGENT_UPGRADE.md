# VoxMate Phase 1 — Agent Upgrade

This is an additive Phase 1 upgrade. Existing voice, text, attachments, tools,
Gemini routing, and UI remain in place.

## Included

1. **Agent Planner**
   - Creates an explicit plan for every turn.
   - Persists plans in `agent_plans`.
   - Sends an `agent_plan` WebSocket event.
   - Gemini still performs the final tool selection.

2. **Multi-step Tool Execution**
   - Existing Gemini function-call loop is retained.
   - Plans track each tool step and dependencies.
   - Up to the existing four tool hops remain unchanged.

3. **Tool Confirmation / Security**
   - Read-only tools can continue automatically.
   - Mutating tools such as `create_reminder` and `run_code` require approval.
   - User webhooks require approval by default.
   - Approvals are persisted in `tool_approvals`.
   - Mobile displays a native confirmation dialog.

4. **Better Long-term Memory**
   - Explicit facts/preferences are automatically remembered.
   - Duplicate memories are ignored.
   - Relevant memories are injected into the agent context.
   - A best-effort Gemini embedding index is stored in `memory_embeddings`;
     keyword recall remains as a fallback if embeddings are unavailable.

## New database tables

`Base.metadata.create_all()` already runs at startup, so these new tables are
created automatically without altering existing table definitions:

- `agent_plans`
- `tool_approvals`
- `memory_embeddings`

For production deployments, use Alembic migrations instead of `create_all`.

## Configuration

Optional:

`VOXMATE_CONFIRM_TOOLS=create_reminder,run_code`

If unset, the built-in security policy is used. Unknown/user webhook tools
require approval by default.

## WebSocket additions

Server → mobile:

- `agent_plan`
- `tool_confirmation`

Mobile → server:

- `tool_confirmation` with `approval_id` and `approved`

No existing message types were removed.
