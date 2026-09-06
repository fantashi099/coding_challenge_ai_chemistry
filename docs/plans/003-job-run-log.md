# 003 — Durable job run log

Status: implemented and verified on 2026-09-06.

## Goal

Keep an ordered, durable history for each video job so API clients and developers can understand enqueueing, reuse, worker attempts, recovery, generation, fallback promotion, artifact publication, and failures after process restarts.

## Storage

Add an append-only SQLite table:

```text
job_events
  id INTEGER PRIMARY KEY AUTOINCREMENT
  job_id TEXT NOT NULL
  event TEXT NOT NULL
  attempt INTEGER
  detail TEXT
  created_at TEXT NOT NULL
```

Index `(job_id, id)`. State-transition events must be inserted in the same transaction as the corresponding job update so status and history cannot disagree.

## Events

- `queued`: new job created.
- `reused`: a normalized duplicate returned the existing job.
- `running`: worker claimed an attempt.
- `generation_started` and `generation_finished`: worker entered and returned from `VideoGenerator`.
- `planner_attempt_succeeded` and `planner_attempt_failed`: sanitized OpenRouter outcome, elapsed time, HTTP status, validation detail, and allowlisted usage/cost.
- `fallback_promoted` or `fallback_promotion_failed`: learned-fallback result.
- `artifact_published`: final MP4 was atomically moved into place.
- `retry_scheduled`: first attempt failed.
- `failed`: final attempt failed or was interrupted.
- `recovered`: interrupted attempt-one job returned to the queue.
- `completed`: terminal success persisted.

Details are optional, capped at 1,000 characters, and must never include API keys, authorization headers, raw provider responses, complete prompts, narration, or stack traces.

## API

Add `GET /videos/{id}/logs`, returning events oldest first. Return `404` for an unknown job. Document the event response model and endpoint in Swagger/OpenAPI.

## Scope limits

- Keep existing console logs for operators; SQLite events are the user-visible durable record.
- Do not add log files, external observability services, live streaming, pagination, or retention policies for this MVP.
- Do not modify `VideoGenerator` solely for per-scene progress. Add callbacks later only if real users need that granularity.

## Verification

1. New, duplicate, claim, retry, completion, failure, and recovery paths produce ordered events with correct attempt numbers.
2. Concurrent duplicate submissions still create one job while recording reuse.
3. Worker tests cover generation, artifact, and fallback-promotion events.
4. API tests cover log retrieval, unknown jobs, response schema, and Swagger documentation.
5. Run the complete suite and `git diff --check`, then update `docs/PROGRESS.md`.
