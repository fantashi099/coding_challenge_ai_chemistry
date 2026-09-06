# AI Chemistry Video Service

A FastAPI job service and reusable CLI that turn a chemistry topic into a narrated 1–3 minute video with animated Manim visuals. OpenRouter writes the script and visual plan; validated curated scripts are reliability fallbacks only for the three required questions.

## Setup

Requirements: Python 3.11–3.13, [`uv`](https://docs.astral.sh/uv/), and FFmpeg/ffprobe.

```bash
uv sync
cp .env.example .env
```

Set `OPENROUTER_API_KEY` in `.env`; Piper downloads the configured voice on first generation. Without an API key, only the three required topics can run through their curated fallbacks.

## Run

Start the API and separate worker in two terminals:

```bash
uv run uvicorn src.api:app --reload
```

```bash
uv run python -m src.workers.video_worker
```

The API uses `data/jobs.sqlite3`, stores job artifacts under `artifacts/jobs`, and exposes Swagger UI at `http://127.0.0.1:8000/docs` (`/openapi.json` and `/redoc` are also available). These paths can be changed with `DATABASE_PATH`, `ARTIFACT_ROOT`, and `WORKER_POLL_SECONDS`.

Normalized-identical questions reuse one job and completed artifact, so they do not spend LLM or rendering resources twice. After a new topic renders successfully, its validated LLM plan is saved as a learned fallback. Recovery order is live LLM, learned fallback, then the three hand-curated fallbacks.

```bash
curl -X POST http://127.0.0.1:8000/videos \
  -H 'content-type: application/json' \
  -d '{"question":"How does the pH scale work?"}'

curl http://127.0.0.1:8000/videos
curl http://127.0.0.1:8000/videos/JOB_ID
curl -OJ http://127.0.0.1:8000/videos/JOB_ID/artifact
```

The direct CLI remains available and uses the same generator:

```bash
uv run python scripts/generate_video.py \
  --question "How does the pH scale work?" \
  --output artifacts/ph-scale
```

The output contains the validated `plan.json`, scene animation and narration files, `metadata.json`, and the final `video.mp4`.

## Test

```bash
uv run pytest
```

The test suite covers plan validation, OpenRouter retry/fallback behavior, SQLite claims and transitions, worker retries/publication, API lifecycle behavior, and an offline Manim/FFmpeg render.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the pipeline boundaries.
