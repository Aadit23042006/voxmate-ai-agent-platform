# Task 6 Demo Video Script — 3 to 5 minutes

## 0:00–0:30 — Introduction
“Hello, this is VoxMate, my Generative AI Capstone Project. It demonstrates a complete GenAI application using Google Gemini, prompt engineering, RAG, tools and agents.”

## 0:30–1:15 — Gemini application
Open `/` and ask: `Explain how VoxMate works.` Explain that the request reaches `/api/chat`, Gemini creates the agent plan, and Gemini generates the final answer.

## 1:15–2:00 — RAG
Ask: `How does the RAG pipeline work?` Show source metadata and explain that retrieved project knowledge is supplied to Gemini as evidence.

## 2:00–2:45 — Tool execution
Ask: `Calculate 125 * 48`. Show the tool result and plan metadata. Explain that the calculator is an allow-listed safe tool.

## 2:45–3:30 — Agent architecture
Open `docs/task6/ARCHITECTURE.md` and explain `User → Agent Planner → RAG/Tool → Gemini Grounded Response → User`.

## 3:30–4:15 — Repository
Show README, `backend/app/capstone/`, RAG, tools, agents, tests, Dockerfile and `render.yaml`.

## 4:15–5:00 — Deployment and submission
Show the deployed URL if configured, open `/docs`, and show the GitHub repository and LinkedIn post.
