# 002 — Backend job service

## Goal

Wrap the existing `VideoGenerator` in a small asynchronous backend: clients submit a chemistry question, poll its durable status, and download the MP4 only after generation succeeds.

## Scope

Build only:

- a FastAPI HTTP API;
- a SQLite job store using Python `sqlite3`;
- one separately launched polling worker;
- a local per-job artifact directory;
- focused store, worker, and API tests.

Do not add authentication, a frontend, Redis/Celery, cloud storage, webhooks, cancellation, or distributed workers. SQLite and one worker are sufficient for the prototype.

## Boundaries

- `src/api.py`: validate HTTP input, enqueue jobs, expose state, and stream completed artifacts. It never generates video.
- `src/jobs.py`: own persistence and valid state transitions. API and worker share no in-memory state.
- `src/workers/video_worker.py`: claim jobs, invoke the existing `VideoGenerator`, publish completed artifacts, and record failures.
- `src/generator.py`: remain the single generation path used by both the CLI and worker.
- `artifacts/jobs/<job-id>/work/`: hold plans and intermediate media.
- `artifacts/jobs/<job-id>/video.mp4`: appear only after successful generation.

## Job lifecycle

```text
queued → running → completed
                 ↘ queued → running → failed
```

- Creating a job sets `queued` with zero attempts.
- Claiming atomically changes one oldest queued job to `running` and increments attempts.
- A failed first attempt returns to `queued` with a concise error.
- A failed second attempt becomes `failed`.
- Worker startup returns interrupted attempt-one jobs to `queued`; an interrupted final attempt becomes `failed`, preserving the two-attempt ceiling.
- Only a `running` job may transition to `completed`, `queued`, or `failed`.

## SQLite record

Each job stores:

- UUID `id`;
- learner `question`;
- `status` constrained to `queued|running|completed|failed`;
- integer `attempts`;
- UTC `created_at` and `updated_at` timestamps;
- nullable final `artifact_path`;
- nullable `error`, capped before persistence.

Use WAL mode, an index on `(status, created_at)`, and `BEGIN IMMEDIATE` while selecting and updating a claim so two workers cannot receive the same job.

## HTTP contract

- `POST /videos` with `{"question": "..."}` returns `202` and the queued job.
- `GET /videos` returns jobs newest first.
- `GET /videos/{id}` returns status, attempts, timestamps, error, and `artifact_url` only when completed.
- `GET /videos/{id}/artifact` streams the MP4; return `404` for an unknown job or missing published file and `409` while unfinished.
- FastAPI's generated OpenAPI document is the contract for this MVP.

## Artifact publication

The worker renders inside the job's `work` directory. After `VideoGenerator.generate()` succeeds, use an atomic filesystem rename to publish `video.mp4`, then mark the database row completed. The API never exposes the work directory or a partial MP4.

## Configuration

Add local defaults for:

- `DATABASE_PATH=data/jobs.sqlite3`
- `ARTIFACT_ROOT=artifacts/jobs`
- `WORKER_POLL_SECONDS=2`

Continue using the existing `.env` configuration for OpenRouter and Piper. Add only FastAPI and Uvicorn dependencies.

## Verification

1. Store tests cover creation, newest-first listing, concurrent atomic claiming, retry, terminal failure, completion, invalid transitions, and startup recovery at both attempt counts.
2. Worker tests use a fake generator to prove success publication, first-attempt requeue, and second-attempt failure without invoking OpenRouter, Piper, Manim, or FFmpeg.
3. API tests cover creation, listing, lookup, unknown jobs, unfinished artifacts, completed artifact streaming, missing completed files, and visible failure details.
4. Run the complete existing CLI/render suite to ensure the service wrapper does not change generation behavior.
5. Run `git diff --check` and document results in `docs/PROGRESS.md` before the phase commit.

## Run contract

```bash
# terminal 1
uv run uvicorn src.api:app --reload

# terminal 2
uv run python -m src.workers.video_worker
```

The CLI remains available unchanged:

```bash
uv run python scripts/generate_video.py --question "How does the pH scale work?" --output artifacts/ph-scale
```
