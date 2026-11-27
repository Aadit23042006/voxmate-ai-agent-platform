# Task 6 Architecture — VoxMate GenAI Capstone

```mermaid
flowchart TD
    U[User] --> W[Task 6 Web UI / Mobile App]
    W --> API[FastAPI API + WebSocket Gateway]
    API --> R[Agent Router]
    R --> P[Planner / Intent Understanding]
    P --> G[Google Gemini LLM]
    G -->|Function Calls| T[Tool Registry]
    T --> X[Search / GitHub / Google / Tasks / Research / Code Tools]
    G --> Q[RAG Service]
    Q --> K[(Knowledge / Documents)]
    G --> M[Memory Service]
    M --> DB[(PostgreSQL)]
    T --> DB
    API --> DB
    API --> C[Redis / Celery]
    C --> B[Background Automation]
    G --> F[Final Grounded Response]
    F --> W
```

## Agent lifecycle

**Understand → Plan → Select Tool → Validate/Authorize → Execute → Observe Result → Update State/Memory → Respond**.

The production Gemini path and the deterministic Task 5 runtime both make the agent lifecycle observable and testable.

## Task 6 demonstration path

1. Open the web UI.
2. Enter a normal question to demonstrate Gemini generation.
3. Ask a knowledge question to demonstrate RAG.
4. Ask for a calculation or another tool-supported action to demonstrate function/tool calling.
5. Show the execution metadata and explain the agent plan.
6. Open `/docs` to demonstrate the FastAPI API surface.
7. Show the repository documentation and deployment files.
