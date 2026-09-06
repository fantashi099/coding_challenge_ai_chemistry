# AI Chemistry Video Generator

A runnable CLI that turns a chemistry topic into a narrated 1–3 minute video with animated Manim visuals. OpenRouter writes the script and visual plan; validated curated scripts are reliability fallbacks only for the three required questions.

## Setup

Requirements: Python 3.11–3.13, [`uv`](https://docs.astral.sh/uv/), and FFmpeg/ffprobe.

```bash
uv sync
cp .env.example .env
```

Set `OPENROUTER_API_KEY` in `.env`; Piper downloads the configured voice on first generation. Without an API key, only the three required topics can run through their curated fallbacks.

## Run

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

The test suite covers plan validation, OpenRouter retry/fallback behavior, and an offline Manim/FFmpeg audio-video smoke render.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the pipeline boundaries.
