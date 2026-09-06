# 002 — Backend job service

Status: deduplication, Swagger, and learned-fallback revision implemented and verified on 2026-09-06.

## Goal

Wrap the existing `VideoGenerator` in a small asynchronous backend: clients submit a chemistry question, poll its durable status, and download the MP4 only after generation succeeds.

## Scope

Build only:

- a FastAPI HTTP API;
- a SQLite job store using Python `sqlite3`;
- one separately launched polling worker;
- a local per-job artifact directory;
- Swagger/OpenAPI documentation;
- exact normalized-question deduplication;
- a learned fallback-plan library;
- focused store, worker, and API tests.

Do not add authentication, a frontend, Redis/Celery, cloud storage, webhooks, cancellation, or distributed workers. SQLite and one worker are sufficient for the prototype.

## Boundaries

- `src/api.py`: validate HTTP input, enqueue jobs, expose state, and stream completed artifacts. It never generates video.
- `src/jobs.py`: own persistence and valid state transitions. API and worker share no in-memory state.
- `src/workers/video_worker.py`: claim jobs, invoke the existing `VideoGenerator`, publish completed artifacts, and record failures.
- `src/generator.py`: remain the single generation path used by both the CLI and worker.
- `src/fallbacks.py`: validate, store, and retrieve learned fallback plans without coupling the planner to SQLite.
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

## Question identity and deduplication

Create a deterministic `question_key` by applying Unicode NFKC normalization, trimming, collapsing whitespace, case-folding, and removing surrounding punctuation. Preserve internal punctuation and do not use embeddings: normalized matching remains predictable and cannot accidentally reuse a different lesson.

- Add `question_key TEXT NOT NULL UNIQUE` to jobs.
- Replace plain creation with a transactional `get_or_create(question)` using the unique constraint as the concurrency authority.
- Concurrent identical submissions must return the same UUID.
- A duplicate `queued`, `running`, `completed`, or `failed` job is returned unchanged; this phase does not add implicit retries or duplicate history.
- A completed duplicate reuses its existing artifact and performs no LLM, Piper, Manim, or FFmpeg work.
- Return `202` for a newly created or unfinished job and `200` when reusing a terminal job. Include `reused: true|false` in the response.

Use `PRAGMA user_version` for the schema upgrade. Backfill keys for existing rows before creating the unique index; if legacy duplicates exist, retain the oldest canonical job and document the reconciliation rather than silently deleting artifacts.

## Learned fallback plans

Keep the three hand-curated plans as permanent seed fallbacks. Add a local fallback repository so successful new topics become reusable:

```text
fallback_plans
  question_key TEXT PRIMARY KEY
  question TEXT NOT NULL
  plan_json TEXT NOT NULL
  source_model TEXT NOT NULL
  created_at TEXT NOT NULL
  updated_at TEXT NOT NULL
  last_used_at TEXT
  use_count INTEGER NOT NULL DEFAULT 0
```

- Promote a plan only after its complete narrated MP4 renders successfully; never cache an unvalidated or partially rendered plan.
- Store the exact validated `VideoPlan` JSON and model provenance.
- Validate cached JSON again on every read. Ignore and report corrupt or schema-incompatible entries.
- Planner recovery order is: two live LLM attempts → learned fallback → hand-curated fallback → clear failure.
- Record `fallback_source` as `none|learned|curated` in generation metadata.
- Increment fallback usage only when a learned plan is actually selected.
- Exact duplicate requests normally stop at job/artifact reuse. The learned plan exists for recovery after artifact loss, deliberate regeneration, or future job-retention cleanup.
- Deletion, expiry, manual approval, semantic matching, and fallback version history are deferred until demonstrated necessary.

## HTTP contract

- `POST /videos` with `{"question": "..."}` creates or reuses the normalized question's job and returns the job plus `reused`.
- `GET /videos` returns jobs newest first.
- `GET /videos/{id}` returns status, attempts, timestamps, error, and `artifact_url` only when completed.
- `GET /videos/{id}/artifact` streams the MP4; return `404` for an unknown job or missing published file and `409` while unfinished.
- `/docs` serves FastAPI's Swagger UI; `/openapi.json` is the machine-readable OpenAPI contract and `/redoc` remains available.
- Add request/response models, route summaries, tags, examples, and documented `200`, `202`, `404`, `409`, and `422` responses so Swagger is useful without reading source code.

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
4. Deduplication tests submit normalized variants and concurrent identical requests, verify one row/UUID, and prove completed duplicates do not invoke generation.
5. Learned-fallback tests cover promotion only after successful rendering, validated lookup, corrupt-entry rejection, resolution order, provenance metadata, and use counts.
6. Swagger tests assert `/docs` loads and `/openapi.json` documents every public route and response model.
7. Run the complete existing CLI/render suite to ensure the service wrapper does not change generation behavior.
8. Run `git diff --check` and document results in `docs/PROGRESS.md` before the phase commit.

Result: all 20 repository tests pass, including concurrent deduplication, schema migration, Swagger contracts, learned fallback behavior, worker promotion, and the existing render smoke test; `git diff --check` passes.

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
