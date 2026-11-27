# Task 6 Final Runbook

## Local

From `backend/`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Create the repository-root `.env` from `.env.example` and set your own `GEMINI_API_KEY`. The key is read at runtime and must not be committed.

Open `http://localhost:8000/`.

## Acceptance smoke test

```bash
curl http://localhost:8000/api/capstone/health

curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message":"How does the RAG pipeline work?"}'
```

Expected Task 6 flow:

`Browser → /api/chat → Gemini planner → RAG/tool/direct action → grounded Gemini answer`

## Tests

```bash
pytest -q tests/test_task6_capstone.py
```

The Task 6 unit tests are designed to run without a live Gemini request.

## Docker

```bash
docker build -t voxmate-task6 ./backend
docker run --rm -p 8000:8000 --env-file .env voxmate-task6
```

## Render

Use `render.yaml`. Set `GEMINI_API_KEY` as a secret environment variable. The Docker build context is `./backend`, matching the repository layout.

## Company submission

After deployment, place the actual GitHub repository URL, live website URL and LinkedIn URL into the company submission form. Record the demo using `docs/task6/DEMO_SCRIPT.md`.
