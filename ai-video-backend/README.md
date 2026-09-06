# AI Chemistry Video Service

A small FastAPI service that queues reliable, narrated 1–3 minute chemistry explainers with animated Manim visuals. Every topic is scripted by OpenRouter when configured; validated curated scripts are reliability fallbacks only for the three required questions.

## Setup

Requirements: Python 3.11–3.13, [`uv`](https://docs.astral.sh/uv/), and FFmpeg/ffprobe.

```bash
uv sync
cp .env.example .env
```

Piper downloads the configured voice on first generation. Set `OPENROUTER_API_KEY` to generate plans for questions outside the curated scope.

## Run

```bash
# terminal 1
uv run uvicorn src.api:app --reload

# terminal 2
uv run python -m src.workers.video_worker
```

```bash
curl -X POST http://127.0.0.1:8000/videos \
  -H 'content-type: application/json' \
  -d '{"question":"How does the pH scale work?"}'
curl http://127.0.0.1:8000/videos
```

Open `/docs` for the interactive API. Completed records include an `artifact_url`.

The same generation path is available directly:

```bash
uv run python scripts/generate_video.py \
  --question "How does the pH scale work?" \
  --output artifacts/ph-scale
```

## Test

```bash
uv run pytest
```

The test suite covers plan validation and retry/fallback behavior, atomic claims and all job transitions, API lifecycle responses, and an offline FFmpeg audio/video smoke render.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for boundaries and tradeoffs. Sample inputs are recorded in [artifacts/samples/questions.json](artifacts/samples/questions.json).
