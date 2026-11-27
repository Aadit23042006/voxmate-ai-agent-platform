# VoxMate Phase 3 — Knowledge

## Deep Research
- Multi-angle grounded web research using the existing Gemini search integration.
- 2–5 research passes with different evidence angles.
- Synthesis that distinguishes evidence, inference, uncertainty and conflicting findings.
- Persisted report with deduplicated sources.
- New Gemini tool: `deep_research`.

## Advanced Document Workspace
- List and open uploaded documents.
- Full extracted text and chunk inspection.
- Rename documents with revision history.
- Delete documents.
- Add persistent notes.
- Generate structured document summaries.
- Existing RAG ingestion and `ask_document` behavior is unchanged.

## Meeting Assistant
- Start/end a persistent meeting from the existing WebSocket.
- Existing microphone audio continues through the same transcription pipeline.
- When meeting mode is active, transcripts are stored instead of being treated as normal assistant turns.
- Finish meeting to generate summary, decisions, action items and open questions.
- Meeting data is persisted and can be retrieved through REST APIs.
- Mobile quick action now exposes Meeting mode.

All Phase 1 and Phase 2 components remain in place; this phase is additive.
