# VoxMate Task 6 Capstone Knowledge Base

VoxMate is a Generative AI assistant and agent automation platform. It uses Google Gemini for language-model capabilities and combines prompt engineering, tool/function calling, agent orchestration, persistent memory, and retrieval-augmented generation.

## Task 6 demonstration

The capstone demo flow is: User Request → Agent Planning → RAG or Tool Selection → Tool/Retrieval Execution → Grounded Gemini Response.

## Gemini

The project reads GEMINI_API_KEY from the runtime environment. Real credentials must not be committed to GitHub. The existing production LLM client is in backend/app/agents/llm_client.py.

## RAG

VoxMate already contains a document ingestion and retrieval service. Documents are chunked, embeddings can be generated with Gemini, and relevant chunks are retrieved for grounded answers. The Task 6 demo layer also provides a small local knowledge-base demonstration so the capstone website can be shown without requiring an authenticated document upload first.

## Tools

The platform contains a tool registry and multiple tools for reminders, tasks, search, documents, code execution, GitHub, Google integrations, webhooks, notifications and more. Task 6's public demo exposes only safe calculator and current-time operations.

## Agents

The production agent architecture uses routing, planning, policy checks, tool declarations, tool execution, state and memory. The Task 6 demo makes this lifecycle visible through the Agent Plan shown under each answer.

## Submission

Required Task 6 submission items are a GitHub repository, a live website, and a LinkedIn post, with documentation, architecture and a demo video supporting the implementation.
