# LinkedIn post — Task 5: AI Agents, Tools & Automation

I’m excited to share my Task 5 project: **VoxMate — an AI Agent, Tools & Automation Assistant**.

This project explores how an AI agent goes beyond a traditional chatbot. Instead of only generating text, it can understand a task, plan an action, select a registered tool, process the tool result, maintain state and memory, and then respond.

**Key capabilities:**
- Agent routing and planning with a multi-step tool-execution loop
- LLM function calling with Google Gemini (plus a mock mode for local testing)
- Tool integrations for search, documents/RAG, GitHub, Google services and webhooks
- User-scoped memory and persisted agent/session state
- Tool validation, approval gates and safer execution policies
- A deterministic offline demo for calculations, memory, read-only database access and allowlisted HTTPS API requests

**Agent workflow:** Understand Task → Decide Action → Use Tool → Process Result → Respond.

I also added automated tests for the Task 5 demonstration, including memory isolation, state persistence, calculator safety, API allowlisting and read-only database access.

**Tech stack:** Python, FastAPI, Google Gemini, SQLAlchemy, SQLite/PostgreSQL, React Native/Expo, REST APIs and WebSockets.

This is a learning and portfolio project. Live third-party integrations require the relevant account credentials and permissions.

#AI #AIAgents #Automation #Python #FastAPI #LLM #FunctionCalling #Gemini #VoxMate #SoftwareDevelopment
