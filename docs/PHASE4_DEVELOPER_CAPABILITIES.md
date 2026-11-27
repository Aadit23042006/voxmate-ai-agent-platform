# Phase 4 — Developer Capabilities

This upgrade is additive. Existing voice, attachments, planner, multi-step tools,
memory, meetings, Google integrations, and productivity features remain intact.

## 1. Coding Agent

VoxMate now has a dedicated `coding` agent. It can:
- list the user's GitHub repositories
- inspect repository files before changing them
- search GitHub code
- create a working branch
- commit complete file updates
- open pull requests
- use the existing sandboxed `run_code` tool for verification

Safety:
- GitHub credentials are stored per user and encrypted with Fernet.
- Read-only GitHub operations run automatically.
- Branch creation, file writes, and PR creation require the existing VoxMate confirmation flow.
- The coding agent is deliberately instructed to inspect before modifying; it does not
  invent unseen repository contents.

## 2. Screen Understanding

VoxMate already had multimodal attachment handling through Gemini. Phase 4 adds a
dedicated **Screen** action and **Screen** quick action. The user selects a screenshot
from the device gallery, VoxMate attaches it, and the multimodal agent can explain:
- visible UI
- error messages
- settings and buttons
- code shown on screen
- what to do next

This implementation is intentionally Expo-compatible without requiring a custom native
screen-capture module. It does not silently capture other apps.

## 3. GitHub Integration

Open Settings → Developer capabilities and connect a GitHub fine-grained personal access
token. The token is validated against `/user`, then encrypted at rest.

### Backend configuration

Generate a Fernet key once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the generated value in `.env`:

```env
GITHUB_TOKEN_ENCRYPTION_KEY=<generated-key>
```

Then rebuild/restart:

```bash
docker compose up -d --build
```

For the token, use a GitHub fine-grained PAT with only the repository permissions needed
for the tasks you want VoxMate to perform. Avoid giving unnecessary organization/admin
permissions.

### Example voice commands

- "List my GitHub repositories."
- "Open the README in owner/repo."
- "Search my GitHub for the function called createSession."
- "Create a branch called fix/login-timeout and update the login file."
- "Open a PR for the fix."

The final three mutation operations will show VoxMate's existing confirmation dialog before
they execute.
