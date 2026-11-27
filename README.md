# VoxMate — AI Voice Assistant, AI Agents & Automation Platform

**VoxMate** is a Generative AI assistant and agent automation platform powered by **Google Gemini**. It combines AI agent orchestration, prompt engineering, tool/function calling, persistent memory, retrieval-augmented generation (RAG), automation, FastAPI APIs, PostgreSQL, Redis, Docker, and a mobile React Native/Expo client.

## 🔗 Live Project

**Live Website:**  
https://voxmate-genai-capstone-bz2f.onrender.com

**GitHub Repository:**  
https://github.com/Aadit23042006/voxmate-ai-agent-platform

**API Documentation:**  
https://voxmate-genai-capstone-bz2f.onrender.com/docs

**OpenAPI Specification:**  
https://voxmate-genai-capstone-bz2f.onrender.com/openapi.json

**Health Check:**  
https://voxmate-genai-capstone-bz2f.onrender.com/health

The live website is served directly by the FastAPI application and provides the Task 6 GenAI capstone interface.

---

# 1. Project Overview

VoxMate is an AI-powered voice assistant and agent automation platform designed to demonstrate how Generative AI can move beyond simple question-and-answer interactions.

The platform can:

- Understand user requests
- Plan task execution
- Route requests to appropriate agent logic
- Select registered tools
- Apply authorization and approval checks
- Execute permitted operations
- Process tool results
- Maintain user-scoped persistent memory
- Retrieve relevant information from knowledge sources
- Perform background automation
- Provide text and voice interaction workflows
- Expose APIs through FastAPI
- Provide a runnable GenAI web interface for Task 6

The core agent workflow is:

```text
Understand Task
      ↓
Plan
      ↓
Route
      ↓
Select Tool
      ↓
Authorize
      ↓
Execute Safely
      ↓
Process Result
      ↓
Generate Response
      ↓
Return Result
```

VoxMate was originally developed for the **Syntecxhub Internship — Task 5: AI Agents, Tools & Automation** and has been extended with the **Module 06 GenAI Capstone — Task 6** implementation.

---

# 2. Task 6 — GenAI Capstone

The Task 6 implementation demonstrates an end-to-end Generative AI workflow using Google Gemini.

### Task 6 flow

```text
User Request
     ↓
Agent Planning
     ↓
RAG / Tool / Direct Selection
     ↓
Execution
     ↓
Knowledge / Tool Results
     ↓
Grounded Gemini Response
     ↓
Web Interface
```

The Task 6 implementation includes:

- Google Gemini integration
- Prompt engineering
- Agent planning
- Tool selection
- Safe calculator execution
- Current-time tool
- Local knowledge-base retrieval
- RAG-style grounded context
- Gemini response generation
- Browser-based interface
- FastAPI API integration
- Production deployment configuration
- Render deployment

---

# 3. Key Capabilities

## AI Agent Platform

- AI-powered conversational assistant
- Agent routing and orchestration
- Task planning
- Tool/function calling
- Tool registry
- Multi-step tool execution
- Tool result processing
- Execution safeguards
- User-scoped persistent memory
- Session/context management

## Voice Assistant

- Audio recording
- Speech-to-text workflow
- AI response generation
- Text-to-speech workflow
- Android audio playback
- WebSocket-based real-time communication
- Conversation-based voice interaction

## Automation

- Reminder management
- Background task execution
- Scheduled jobs
- Workflow automation
- Notification processing
- Webhook integrations

## RAG and Document Intelligence

- Document ingestion
- Content extraction
- Chunking
- Embedding generation
- Retrieval of relevant content
- User-scoped document retrieval
- Grounded responses
- Local Task 6 knowledge-base demonstration

## Developer Capabilities

- Supported Python code execution
- Developer-oriented AI workflows
- GitHub integration support
- Webhook extensibility
- Tool-assisted operations

## Account and Security

- User registration
- User login
- Password verification
- JWT authentication
- Protected API endpoints
- Ownership validation
- Tool approval/rejection workflow
- User preferences
- Usage statistics
- Data export
- Account deletion

## Mobile Application

- React Native
- Expo
- Android application workflow
- API integration
- WebSocket integration
- Audio interaction
- Push notification integration

---

# 4. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| AI | Google Gemini |
| API Documentation | OpenAPI / Swagger |
| Database | PostgreSQL |
| Cache / Message Broker | Redis |
| Background Processing | Celery |
| Scheduling | Celery Beat |
| Agent Orchestration | Python |
| Authentication | JWT |
| Real-Time Communication | WebSockets |
| Mobile Application | React Native, Expo |
| Mobile Language | TypeScript |
| Audio | Expo Audio |
| Push Notifications | Expo Notifications / Firebase Cloud Messaging |
| Retrieval | RAG / Embeddings |
| Testing | Pytest |
| Containerization | Docker / Docker Compose |
| Version Control | Git / GitHub |
| Deployment | Render |

---

# 5. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │   React Native App   │
                         │       / Android      │
                         └──────────┬───────────┘
                                    │
                           HTTPS / WebSocket
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FastAPI API      │
                         │ Authentication / API │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Agent Orchestrator   │
                         │ Planning / Routing    │
                         └───────┬───────┬──────┘
                                 │       │
                    ┌────────────┘       └─────────────┐
                    ▼                                  ▼
             ┌─────────────┐                    ┌─────────────┐
             │ Tool System │                    │ Gemini AI   │
             │   Registry  │                    │ Integration │
             └──────┬──────┘                    └──────┬──────┘
                    │                                  │
                    ├──────────────┐                   │
                    ▼              ▼                   ▼
             ┌────────────┐  ┌────────────┐    ┌────────────┐
             │ RAG / Docs │  │Integrations│    │ AI Response│
             └────────────┘  └────────────┘    └────────────┘
                    │              │
                    └──────┬───────┘
                           ▼
                  ┌──────────────────┐
                  │ PostgreSQL / Redis│
                  │ Memory / Sessions │
                  └──────────────────┘
```

The repository also contains background workers and scheduled automation through Celery and Redis.

---

# 6. Repository Structure

```text
voxmate-ai-agent-platform/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── capstone/
│   │   ├── integrations/
│   │   ├── memory/
│   │   ├── models/
│   │   ├── rag/
│   │   ├── realtime/
│   │   ├── static/
│   │   ├── tools/
│   │   ├── workers/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── security.py
│   │
│   ├── knowledge/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── mobile/
│   ├── src/
│   ├── App.tsx
│   ├── app.json
│   ├── eas.json
│   ├── package.json
│   └── tsconfig.json
│
├── tests/
│   ├── test_auth.py
│   ├── test_background_tasks.py
│   ├── test_new_tools.py
│   ├── test_orchestrator_function_calling.py
│   ├── test_orchestrator_multi_hop.py
│   ├── test_orchestrator_routing.py
│   ├── test_orchestrator_tool_failure.py
│   ├── test_orchestrator_tool_permissions.py
│   ├── test_personalization.py
│   ├── test_phase4_developer.py
│   ├── test_task5_runtime.py
│   ├── test_task6_capstone.py
│   └── ...
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PHASE1_AGENT_UPGRADE.md
│   ├── PHASE2_PRODUCTIVITY_UPGRADE.md
│   ├── PHASE3_KNOWLEDGE_UPGRADE.md
│   ├── PHASE4_DEVELOPER_CAPABILITIES.md
│   ├── PHASE5_PLATFORM.md
│   ├── task5/
│   └── task6/
│
├── examples/
│   └── task5_agent_demo.py
│
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── render.yaml
├── pytest.ini
├── run_task6_api_smoke.py
├── TASK5_COMPLETION_REPORT.md
├── TASK6_SUBMISSION.md
└── README.md
```

The committed repository is the source of truth for individual files and implementation details.

---

# 7. AI Agent Architecture

VoxMate uses an agent-oriented execution model.

## Agent Execution Lifecycle

```text
User Request
     │
     ▼
Understand
     │
     ▼
Plan
     │
     ▼
Route to Agent
     │
     ▼
Select Tool
     │
     ▼
Authorization / Approval
     │
     ▼
Execute Safely
     │
     ▼
Process Result
     │
     ▼
Generate Response
     │
     ▼
Return Result
```

### Execution Stages

1. **Understand** — interpret the user's request.
2. **Plan** — determine the required task and possible execution path.
3. **Route** — select appropriate agent logic.
4. **Select Tool** — identify the required registered tool.
5. **Authorize** — validate permissions and approval requirements.
6. **Execute** — execute the permitted operation.
7. **Process** — interpret the returned result.
8. **Respond** — generate the final user-facing response.

The orchestrator can process multiple tool interactions until the task is completed or the configured execution limit is reached.

---

# 8. Task 6 Agent Planning and Tools

The Task 6 capstone service contains a deterministic and auditable planning layer.

The planner can select actions such as:

```text
retrieve_knowledge
calculator
current_time
direct
```

### Knowledge Retrieval

Project-related requests can be routed to the local knowledge base.

The Task 6 knowledge demonstration uses:

```text
backend/knowledge/
```

Knowledge files are loaded by the capstone service and relevant content is selected using token-based retrieval before being supplied to Gemini.

### Calculator Tool

The calculator uses a restricted AST-based arithmetic evaluator.

Supported operations include:

- Addition
- Subtraction
- Multiplication
- Division
- Power
- Modulo
- Floor division
- Unary positive/negative values

Arbitrary Python execution is not used for this calculator operation.

### Current Time Tool

The Task 6 agent can provide the current local system time using timezone-aware datetime handling.

---

# 9. Tools and Automation

VoxMate provides a tool-oriented architecture so the assistant can perform actions rather than only generate text.

## Tool Categories

| Tool category | Purpose |
|---|---|
| Reminder tools | Create and manage reminders |
| Task tools | Manage user tasks |
| Code execution | Execute supported Python computations |
| Search integration | Retrieve relevant information |
| Document tools | Retrieve information from uploaded documents |
| Memory tools | Save and retrieve user context |
| Notification tools | Deliver configured notifications |
| Webhook tools | Connect supported external services |
| Background jobs | Process asynchronous operations |
| Integration tools | Connect supported third-party services |

Actual tool availability depends on application configuration, credentials, permissions, and integration setup.

## Tool Approval and Security

Sensitive operations can require explicit approval before execution.

The approval workflow supports controls such as:

- Pending approval
- Approval
- Rejection
- Ownership validation
- Session validation
- Duplicate execution protection
- Expiration of unresolved approvals

Unauthorized or rejected operations must not be executed.

---

# 10. RAG and Document Intelligence

VoxMate includes document-oriented retrieval capabilities.

The supported document workflow includes:

```text
Document
   ↓
Text Extraction
   ↓
Chunking
   ↓
Embedding Generation
   ↓
Metadata / Storage
   ↓
Retrieval
   ↓
Relevant Context
   ↓
Gemini
   ↓
Grounded Response
```

The RAG-oriented architecture supports:

1. Receiving supported document content.
2. Extracting usable text.
3. Splitting content into manageable chunks.
4. Generating embeddings.
5. Storing document and retrieval metadata.
6. Retrieving relevant content.
7. Supplying retrieved context to supported AI requests.
8. Generating responses grounded in retrieved information.

The Task 6 website additionally includes a small local knowledge-base demonstration so the capstone workflow can be demonstrated without requiring an authenticated document upload first.

---

# 11. Memory and Personalization

VoxMate supports persistent user context.

## Memory Capabilities

- Save useful user-scoped information
- Retrieve previously stored context
- Maintain user-specific memory
- Persist memory across application restarts
- Use retrieved context during supported AI interactions

## Personalization

Supported preferences can include:

- Assistant name
- Response tone
- Text-to-speech voice

Personalization is designed to improve consistency across conversations while maintaining user-scoped data boundaries.

---

# 12. Voice Assistant and Real-Time Communication

The mobile application communicates with the FastAPI backend using authenticated API requests and WebSocket connections.

## Voice Workflow

```text
User speaks
     │
     ▼
Mobile audio recording
     │
     ▼
Backend WebSocket / API workflow
     │
     ▼
Speech recognition
     │
     ▼
AI agent orchestration
     │
     ▼
Tool execution, if required
     │
     ▼
AI response generation
     │
     ▼
Speech synthesis
     │
     ▼
Android audio playback
```

### Voice Capabilities

- Microphone-based input
- Audio recording
- Speech transcription workflow
- AI response generation
- Text-to-speech
- Android playback
- Conversation-based interaction

Continuous streaming transcription or advanced barge-in behavior should not be assumed unless explicitly implemented and verified in the deployed environment.

---

# 13. Code Execution and Developer Capabilities

VoxMate includes developer-oriented AI capabilities.

The platform supports generating and executing supported Python code through its code-execution tooling.

Code execution is a security-sensitive feature.

For production use with untrusted workloads, the execution environment should provide:

- Strong process isolation
- Resource limits
- CPU and memory controls
- Restricted filesystem access
- Restricted network access
- Execution time limits
- Appropriate monitoring

The platform also provides extensibility for supported:

- GitHub workflows
- Webhook workflows
- External API integrations
- Tool-driven developer tasks

---

# 14. Background Tasks and Automation

VoxMate uses **Celery + Redis** for asynchronous processing.

Supported infrastructure includes:

- Background task execution
- Scheduled jobs
- Notification processing
- Workflow automation
- Periodic task scheduling

Celery workers execute queued jobs while Celery Beat is configured for scheduled processing.

---

# 15. Push Notifications

The Android application supports push notification integration through Expo Notifications and Firebase Cloud Messaging.

The notification workflow can include:

- Android notification permission handling
- Notification channel configuration
- Device push-token registration
- Backend device-token storage
- Provider-based notification delivery

Actual notification delivery depends on valid Firebase, Expo, and deployment configuration.

---

# 16. Authentication and Account Management

The backend provides authentication and account-management functionality.

Supported areas include:

- User registration
- User login
- Password verification
- JWT-based authentication
- Protected API endpoints
- User-specific sessions and data
- Ownership validation
- Account preferences
- Usage statistics
- Data export
- Account data deletion

Sensitive operations must remain protected by appropriate authentication and ownership controls.

---

# 17. Installation and Setup

## Prerequisites

Install:

| Requirement | Purpose |
|---|---|
| Python 3.11+ | Backend runtime |
| Node.js | Mobile development |
| npm | JavaScript dependencies |
| Docker Desktop | Containerized infrastructure |
| Git | Version control |
| Android device/emulator | Mobile testing |

A compatible Gemini API key is required for Gemini-powered functionality.

Optional integrations may require additional credentials.

---

# 18. Clone the Repository

```bash
git clone https://github.com/Aadit23042006/voxmate-ai-agent-platform.git
cd voxmate-ai-agent-platform
```

---

# 19. Configure Environment Variables

Copy the example environment configuration.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Configure the required values in `.env`.

Important variables include:

```text
DATABASE_URL
REDIS_URL
JWT_SECRET
JWT_ALGORITHM
JWT_EXPIRE_MINUTES
GEMINI_API_KEY
GEMINI_TEXT_MODEL
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
PUBLIC_BASE_URL
CORS_ALLOWED_ORIGINS
EXPO_ACCESS_TOKEN
GITHUB_TOKEN_ENCRYPTION_KEY
GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET
GITHUB_REDIRECT_URI
```

Not every integration is mandatory for local operation.

**Never commit the real `.env` file or production secrets.**

---

# 20. Start the Docker Stack

From the project root:

```bash
docker compose up --build -d
```

Check service status:

```bash
docker compose ps
```

Expected infrastructure includes:

- FastAPI backend
- PostgreSQL
- Redis
- Celery worker

---

# 21. Check Backend Health

Local health endpoint:

```text
http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

---

# 22. Open API Documentation

Local Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

---

# 23. Running the Backend Without Docker

Create a virtual environment:

```powershell
python -m venv .venv_task6
.\.venv_task6\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

Configure PostgreSQL and Redis separately and ensure the corresponding environment variables are available.

Start FastAPI:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

For local development, reload mode may be used:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

Production deployments should use an appropriate production server/process configuration rather than relying on development reload mode.

---

# 24. Running the Mobile Application

Navigate to the mobile project:

```bash
cd mobile
npm install
```

Configure the backend URL according to the actual Expo configuration used by the application.

Example:

```env
EXPO_PUBLIC_API_URL=http://YOUR_COMPUTER_LAN_IP:8000
```

For a standard Android emulator:

```env
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000
```

For a physical Android device, use the computer's current LAN IP address.

Start Expo:

```bash
npx expo start
```

For Android development or release builds, use the configured Expo/EAS workflow.

---

# 25. Running the Tests

VoxMate uses **Pytest** for backend verification.

Install development dependencies:

```powershell
python -m pip install -r backend/requirements-dev.txt
```

Run the complete backend test suite:

```powershell
python -m pytest .\tests -q --tb=short
```

Run with detailed output:

```powershell
python -m pytest .\tests -v
```

## Verified Task 6 Test Result

```text
88 passed
```

Therefore:

**88/88 automated backend tests are passing.**

There are currently **0 outstanding automated backend tests** in the verified Task 6 suite.

Dependency deprecation warnings may appear during execution. Warnings are not test failures.

---

# 26. Task 5 — AI Agents, Tools & Automation

The original Task 5 implementation established the core agent workflow:

```text
Understand Task
      ↓
Decide Action
      ↓
Use Tool
      ↓
Process Result
      ↓
Respond
```

### Task 5 Implementation Areas

| Requirement area | Implementation |
|---|---|
| AI agent orchestration | Agent orchestration layer |
| Planning | Task planning components |
| Agent routing | Agent routing logic |
| Tool selection | Tool registry |
| Tool execution | Registered tools |
| Memory | Persistent user memory |
| Tool authorization | Approval workflow |
| Automation | Background workers and scheduled jobs |
| Error handling | Validation and execution safeguards |
| Demonstration | Agent demonstration assets |

Task 5 documentation is maintained under:

```text
docs/task5/
```

---

# 27. Task 6 — GenAI Capstone

The repository includes the additive **Module 06 GenAI Capstone** implementation.

Task 6 demonstrates:

- Generative AI
- Google Gemini
- Prompt engineering
- Agent planning
- RAG
- Tool execution
- Grounded response generation
- Runnable web UI
- API integration

## Task 6 Deliverables

```text
TASK6_SUBMISSION.md
docs/task6/COMPANY_REQUIREMENTS.md
docs/task6/ARCHITECTURE.md
docs/task6/ACCEPTANCE_TEST.md
docs/task6/DEMO_SCRIPT.md
docs/task6/LINKEDIN_POST.md
docs/task6/SUBMISSION_CHECKLIST.md
backend/app/static/index.html
```

---

# 28. Task 6 Runtime Flow

The Task 6 web interface uses the existing VoxMate application stack.

```text
Browser
   │
   ▼
Task 6 Web UI
   │
   ▼
FastAPI /api/chat
   │
   ▼
Gemini Agent Planner
   │
   ├── RAG Retrieval
   │
   ├── Safe Tool Execution
   │
   └── Direct Generation
   │
   ▼
Grounded Gemini Response
   │
   ▼
Browser
```

The browser UI is served by the FastAPI application at:

```text
/
```

Task 6 API routes include:

```text
/api/chat
/api/capstone/health
```

Interactive API documentation:

```text
/docs
```

A valid `GEMINI_API_KEY` is required for live Gemini requests.

---

# 29. Task 6 Local Knowledge Base

The Task 6 capstone contains a local knowledge-base demonstration.

Knowledge files are stored under:

```text
backend/knowledge/
```

The capstone service loads the knowledge directory relative to the backend application and retrieves relevant Markdown content before generating a Gemini response.

This allows the Task 6 website to demonstrate the RAG-style flow without requiring an authenticated document-upload workflow for the initial capstone demonstration.

---

# 30. Task 6 Local Launch

From the repository root:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Before making live Gemini requests, configure:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

The real API key must never be committed to GitHub.

---

# 31. Production Environment Configuration

Production secrets must be configured through the hosting provider.

Required/important Render variables include:

```text
GEMINI_API_KEY
GEMINI_TEXT_MODEL
JWT_SECRET
ENV
LOG_LEVEL
DATABASE_URL
REDIS_URL
PUBLIC_BASE_URL
GOOGLE_REDIRECT_URI
GITHUB_REDIRECT_URI
CORS_ALLOWED_ORIGINS
```

Do not place production secrets inside `render.yaml`.

The Render configuration uses managed service connections for the deployed PostgreSQL and Redis infrastructure.

---

# 32. CORS Configuration

VoxMate uses environment-driven CORS configuration.

The backend reads:

```env
CORS_ALLOWED_ORIGINS
```

as a comma-separated list of trusted frontend origins.

Example local configuration:

```env
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

Production deployments should override this value with the actual trusted frontend origin(s).

The production backend does **not** intentionally use unrestricted:

```python
allow_origins=["*"]
```

CORS configuration.

---

# 33. Security

Security is an important part of the VoxMate architecture.

Implemented security-related controls include:

- JWT authentication
- Protected API endpoints
- User ownership validation
- Tool authorization
- Tool approval/rejection workflows
- Duplicate approval protection
- Session validation
- User-scoped memory
- User-scoped document access
- Environment-based credential configuration
- Restricted CORS configuration
- Execution safeguards
- Production-oriented configuration separation

## Security Rules

1. Never commit `.env`.
2. Never commit API keys.
3. Never commit OAuth client secrets.
4. Never commit JWT signing secrets.
5. Never commit Firebase service-account private keys.
6. Never publish private keys or certificates.
7. Use strong, unique production secrets.
8. Restrict PostgreSQL and Redis network access.
9. Use HTTPS in production.
10. Use secure WebSockets in production.
11. Review third-party integration permissions.
12. Harden code execution before exposing it to untrusted multi-user workloads.
13. Rotate credentials immediately if accidental exposure occurs.

The repository contains `.env.example` with placeholders rather than production credentials.

---

# 34. GitHub Security

The repository is prepared for public GitHub publication with local secret protection.

The root `.gitignore` excludes sensitive local configuration such as:

```text
.env
.env.*
```

while allowing:

```text
.env.example
```

Before pushing to GitHub, verify:

```powershell
git status
git diff --cached --name-only
```

Confirm that the real `.env` and other sensitive files are not included.

Never bypass `.gitignore` with:

```bash
git add -f .env
```

If a credential is ever accidentally committed or exposed, revoke/rotate it immediately and review Git history.

---

# 35. Render Deployment

VoxMate is configured for deployment on Render.

The repository contains:

```text
render.yaml
```

The deployed web service uses:

```text
/health
```

as its health-check path.

## Production Web Service

```text
Service:
voxmate-genai-capstone-bz2f
```

## Live Website

```text
https://voxmate-genai-capstone-bz2f.onrender.com
```

## Production Endpoints

### Main Website

```text
https://voxmate-genai-capstone-bz2f.onrender.com/
```

### Health

```text
https://voxmate-genai-capstone-bz2f.onrender.com/health
```

### Swagger

```text
https://voxmate-genai-capstone-bz2f.onrender.com/docs
```

### OpenAPI

```text
https://voxmate-genai-capstone-bz2f.onrender.com/openapi.json
```

### Task 6 Chat API

```text
https://voxmate-genai-capstone-bz2f.onrender.com/api/chat
```

The public Render deployment has been configured as the live Task 6 web application.

---

# 36. Live Website Verification

The deployed Render service has successfully responded to the following requests:

```text
GET /
GET /health
GET /docs
GET /openapi.json
```

Expected production behavior:

```text
/              → 200 OK
/health        → 200 OK
/docs          → 200 OK
/openapi.json  → 200 OK
```

Render health-check requests also return:

```text
200 OK
```

The Task 6 browser interface is therefore hosted by the deployed FastAPI service.

The `/api/chat` endpoint additionally requires:

- Valid Gemini credentials
- Correct production environment configuration
- Correct knowledge-base filesystem permissions
- Successful Gemini API availability

---

# 37. Production Knowledge-Base Path

The Task 6 capstone knowledge directory is located at:

```text
backend/knowledge/
```

The capstone service resolves this directory relative to the backend application package so that the Docker deployment does not attempt to create the knowledge directory at the container filesystem root.

This keeps the Task 6 knowledge-base path aligned with the repository structure.

---

# 38. Verification Status

| Verification Area | Status |
|---|---|
| Python compilation | PASS |
| Backend automated test suite | PASS — 88/88 |
| Remaining automated backend tests | 0 |
| Production `datetime.utcnow()` audit | PASS |
| CORS hardening audit | PASS |
| Environment configuration audit | PASS |
| Recognizable secret-pattern audit | PASS |
| Hard-coded secret audit | PASS |
| GitHub-sensitive-file pre-check | PASS |
| Code-quality audit | PASS |
| TODO/FIXME audit | PASS — 0 |
| Direct `print()` audit | PASS — 0 |
| Debug/reload production-code audit | PASS |
| Docker stack verification | PASS |
| PostgreSQL health | PASS |
| Redis health | PASS |
| FastAPI `/` | PASS — 200 |
| FastAPI `/health` | PASS — 200 |
| FastAPI `/docs` | PASS — 200 |
| FastAPI `/openapi.json` | PASS — 200 |
| Render configuration | PASS |
| Render `healthCheckPath` | PASS — `/health` |
| Public Render website | PASS |
| Task 6 web interface | Deployed |
| Task 6 `/api/chat` | Requires final runtime verification after latest knowledge-path deployment |

## Automated Test Result

```text
88 passed
```

No automated backend tests are currently outstanding in the verified Task 6 suite.

Dependency-level deprecation warnings may appear during testing. Warnings are not equivalent to failed tests.

---

# 39. Documentation

Additional documentation is available under `docs/`.

| Document | Purpose |
|---|---|
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/PHASE1_AGENT_UPGRADE.md` | Agent architecture evolution |
| `docs/PHASE2_PRODUCTIVITY_UPGRADE.md` | Productivity capabilities |
| `docs/PHASE3_KNOWLEDGE_UPGRADE.md` | Knowledge and document capabilities |
| `docs/PHASE4_DEVELOPER_CAPABILITIES.md` | Developer-oriented capabilities |
| `docs/PHASE5_PLATFORM.md` | Platform capabilities |
| `docs/task5/COMPANY_REQUIREMENTS.md` | Task 5 requirement mapping |
| `docs/task5/LINKEDIN_POST.md` | Task 5 presentation copy |
| `docs/task5/SUBMISSION_CHECKLIST.md` | Task 5 submission checklist |
| `docs/task6/COMPANY_REQUIREMENTS.md` | Task 6 requirement mapping |
| `docs/task6/ARCHITECTURE.md` | Task 6 architecture |
| `docs/task6/ACCEPTANCE_TEST.md` | Task 6 acceptance verification |
| `docs/task6/DEMO_SCRIPT.md` | Task 6 demo script |
| `docs/task6/LINKEDIN_POST.md` | Task 6 LinkedIn copy |
| `docs/task6/RUNBOOK.md` | Task 6 operational runbook |
| `docs/task6/SUBMISSION_CHECKLIST.md` | Task 6 submission checklist |
| `TASK6_SUBMISSION.md` | Final Task 6 submission documentation |

---

# 40. Company / Internship Requirements

The project demonstrates the following engineering and AI capabilities:

- Generative AI integration
- Google Gemini integration
- Prompt-driven AI workflows
- AI agent orchestration
- Tool calling
- Tool authorization
- RAG
- Persistent memory
- API development
- Authentication
- Database integration
- Redis-based infrastructure
- Background processing
- Scheduled automation
- Mobile application integration
- Voice interaction
- WebSocket communication
- Dockerized development
- Production-oriented configuration
- Security controls
- Automated testing
- Deployment configuration
- Technical documentation

Task-specific requirement mappings are maintained in:

```text
docs/task5/
docs/task6/
```

---

# 41. Known Limitations

Some features depend on external providers and deployment configuration.

- Gemini functionality requires valid Gemini credentials.
- Google OAuth requires valid OAuth application configuration.
- GitHub integrations require valid GitHub credentials and permissions.
- Push notifications require valid Firebase/Expo configuration.
- External providers may impose rate limits and usage costs.
- Code execution requires additional sandbox hardening for untrusted production workloads.
- Continuous audio streaming and advanced barge-in behavior should not be assumed unless explicitly implemented and verified.
- Production deployment requires monitoring, backups, secure secret management, and operational controls.
- OAuth callback functionality requires correctly configured production redirect URLs.
- Live Gemini requests require a valid production `GEMINI_API_KEY`.
- The Task 6 knowledge-base demo requires the deployed knowledge directory to be readable by the application process.

---

# 42. Future Enhancements

Potential future improvements include:

- Additional specialist agents
- More advanced long-term memory retrieval
- Stronger code-execution isolation
- Enhanced real-time voice streaming
- Improved interruption/barge-in support
- Additional external integrations
- Observability dashboards
- Performance and load testing
- Automated deployment pipelines
- Expanded mobile capabilities
- Additional enterprise security controls

---

# 43. GitHub Publication Checklist

```text
[✓] README.md reviewed
[✓] .gitignore configured
[✓] Real .env excluded
[✓] .env.example included
[✓] mobile/.env.example included
[✓] Sensitive credential filenames checked
[✓] Secret-pattern audit passed
[✓] Backend compilation passed
[✓] 88/88 automated tests passed
[✓] CORS audit passed
[✓] Production datetime audit passed
[✓] Docker/API verification passed
[✓] Task 6 documentation audit passed
[✓] Render configuration verified
[✓] GitHub repository published
[✓] Render web service deployed
[✓] Live Website URL available
[✓] Live /health verified
[✓] Live /docs verified
[✓] Live /openapi.json verified
[ ] Final /api/chat verification after latest knowledge-path deployment
```

The remaining runtime verification item concerns the latest `/knowledge` filesystem-path fix and should be marked complete after the updated commit is deployed and `/api/chat` returns a successful response.

---

# 44. Internship Submission

**Project:** VoxMate — AI Voice Assistant, AI Agents & Automation Platform

**Primary Module:** Task 5 — AI Agents, Tools & Automation

**Capstone Module:** Task 6 — GenAI Capstone

**Organization:** Syntecxhub Internship

**GitHub Repository:**

https://github.com/Aadit23042006/voxmate-ai-agent-platform

**Live Website:**

https://voxmate-genai-capstone-bz2f.onrender.com

**API Documentation:**

https://voxmate-genai-capstone-bz2f.onrender.com/docs

The project demonstrates the integration of:

**AI Agents + Gemini + Tool Calling + RAG + Memory + Automation + FastAPI + Mobile Voice + Security + Docker + Testing + Deployment**

For detailed requirement mapping, refer to:

```text
docs/task5/COMPANY_REQUIREMENTS.md
docs/task6/COMPANY_REQUIREMENTS.md
TASK6_SUBMISSION.md
```

---

# 45. Final Project Summary

VoxMate demonstrates how a modern AI assistant can move beyond simple question-and-answer interactions by combining:

```text
User Request
      ↓
AI Understanding
      ↓
Planning
      ↓
Agent Routing
      ↓
Tool Selection
      ↓
Authorization
      ↓
Safe Execution
      ↓
RAG / Memory / External Services
      ↓
Result Processing
      ↓
Gemini Response
      ↓
Text / Voice / Mobile Experience
```

The project combines AI engineering, backend development, mobile development, automation, security, testing, and deployment configuration into a single application.

## Live Demo

**Website:**  
https://voxmate-genai-capstone-bz2f.onrender.com

**Swagger API:**  
https://voxmate-genai-capstone-bz2f.onrender.com/docs

**GitHub:**  
https://github.com/Aadit23042006/voxmate-ai-agent-platform

---

## VoxMate

**Turning voice commands into intelligent, actionable workflows.**