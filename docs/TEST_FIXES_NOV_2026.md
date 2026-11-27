# Test remediation — November 2026

## Corrected defects

- `build_system_prompt` is now a pure function and accepts assistant name, tone,
  context, guidelines, and additional tool descriptions without requiring Gemini credentials.
- Default prompt personalization now includes the VoxMate name, casual tone, and
  an instruction to answer in the user's language.
- `LLMClient` can be constructed without an API key in local/test mode. Gemini
  operations still fail with a clear configuration error if live generation is requested
  without credentials.
- Daily briefings with no pending tasks return a deterministic empty-state message.
- Development-mode web search returns a structured, explicitly labelled mock response
  (`query`, `answer`, `sources`, `mode`) when Gemini is not configured.
- Live web search continues to use Gemini Google Search grounding and only returns
  source URLs present in grounding metadata.
- Pytest's async fixture loop scope is configured explicitly.

## Configuration

For live Gemini functionality, set `GEMINI_API_KEY` in your local `.env` file.
Do not commit `.env`; use `.env.example` as the template. The offline mock mode is
for local development and tests only. In production, missing Gemini credentials
cause live search/briefing generation to fail clearly rather than pretending to
have live results.

## Verification performed in this environment

The focused suite covering personalization, tools, orchestrator routing, Task 5 runtime,
new tools, and Phase 4 developer tools passed: **31 passed**.

The full suite could not be independently confirmed in this Linux packaging environment:
the uploaded archive contains a Windows virtual environment, whose compiled native
extensions cannot run on Linux. In the available Linux interpreter, the two auth tests
also lacked a platform-compatible bcrypt backend. Re-run the full suite in the project's
Windows virtual environment after installing `requirements-dev.txt`.
