# AI Chemistry Video Service

A FastAPI job service and reusable CLI that turn a chemistry topic into a narrated 1–3 minute video with animated Manim visuals. OpenRouter writes the script and visual plan; validated curated scripts are reliability fallbacks only for the three required questions.

## Setup

Requirements: Python 3.11–3.13, [`uv`](https://docs.astral.sh/uv/), and FFmpeg/ffprobe.

```bash
uv sync
cp .env.example .env
```

Set `OPENROUTER_API_KEY` in `.env`. Optionally set `ELEVENLABS_API_KEY` to use the River voice with the `eleven_turbo_v2_5` model; without it, narration automatically uses local Piper, which downloads its configured voice on first generation. Without an OpenRouter key, only the three required topics can run through their curated fallbacks.

## Run

Start the API and separate worker in two terminals:

```bash
uv run uvicorn src.api:app --reload
```

```bash
uv run python -m src.workers.video_worker
```

The API uses `data/jobs.sqlite3`, stores job artifacts under `artifacts/jobs`, and exposes Swagger UI at `http://127.0.0.1:8000/docs` (`/openapi.json` and `/redoc` are also available). Durable job run logs are stored in the SQLite `job_events` table; worker operational logs print to its terminal. These paths can be changed with `DATABASE_PATH`, `ARTIFACT_ROOT`, and `WORKER_POLL_SECONDS`.

Questions that differ only by Unicode form, case, whitespace, or surrounding punctuation reuse one job and completed artifact, so they do not spend LLM or rendering resources twice. After a new topic renders successfully, its validated LLM plan is saved as a learned fallback. Recovery order is live LLM, learned fallback, then the three hand-curated fallbacks.

```bash
curl -X POST http://127.0.0.1:8000/videos \
  -H 'content-type: application/json' \
  -d '{"question":"How does the pH scale work?"}'

curl http://127.0.0.1:8000/videos
curl http://127.0.0.1:8000/videos/JOB_ID
curl http://127.0.0.1:8000/videos/JOB_ID/logs
curl -OJ http://127.0.0.1:8000/videos/JOB_ID/artifact
```

The direct CLI remains available and uses the same generator:

```bash
uv run python scripts/generate_video.py \
  --question "How does the pH scale work?" \
  --output artifacts/ph-scale
```

To judge the planner prompt alone (one LLM call, no fallback, no render), use `uv run python scripts/check_prompt.py --question "..."`. Planner requests default to a 300-second timeout, configurable with `PLANNER_TIMEOUT_SECONDS` in `.env`.

The output contains the validated `plan.json`, scene animation and narration files, `metadata.json`, and the final `video.mp4`.

## Test

```bash
uv run pytest
```

The test suite covers plan validation, OpenRouter retry/fallback behavior, SQLite claims and transitions, worker retries/publication, API lifecycle behavior, and an offline Manim/FFmpeg render.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the pipeline boundaries.
