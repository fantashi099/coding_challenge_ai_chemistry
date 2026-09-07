# Progress

## 2026-09-06

- Decision: use validated OpenRouter structured output with one retry and curated fallbacks for only the three required questions.
- Decision: use animated Manim slides and Piper narration; FFmpeg muxes narration and concatenates scenes.
- Decision: stop after the runnable CLI MVP; defer FastAPI, persistence, and workers until requested.
- Validation: 10 tests passed before scope reduction; the CLI produced a 61.18-second 1280×720 H.264/AAC pH video with Manim visuals and Piper narration.
- Validation: 6 CLI-focused tests pass after removing the service layer; dependency sync and the documented `--help` invocation also pass.
- Validation: the documented direct CLI command imports and runs successfully; Piper downloads its configured voice on first use.
- Blocker: no `OPENROUTER_API_KEY` is available locally, so live LLM generation has not been exercised. The three required topics use validated curated fallbacks.
- Next action: configure an OpenRouter key and review one dynamically scripted video before starting any service layer.
- Decision: match the supplied XGBoost reference's visual language: black canvas, sparse type, cyan/green glow, outlined cards, animated nodes, and progressive reveals; omit its branding and content.
- Finding: Qwen assigned `covalent_sharing` to every scene in the pH sample, causing one animation template to repeat with different text.
- Decision: require title/recap endpoints, at least three visual kinds, no kind more than twice, and explicit chemistry-to-visual selection rules; invalid plans retry before fallback.
- Validation: the first live Qwen check exhausted both attempts and safely selected the varied curated pH plan (`title`, `ph_scale`, `bullets`, `ph_scale`, `recap`).
- Decision: remove a prompt conflict that classified three common pH scenes as `ph_scale` while limiting every kind to two uses; logarithmic rules now route to `bullets`.
- Validation: 7 tests pass after adding the repeated-template regression guard and revising the prompt.
- Validation: a second live Qwen planner check was manually stopped after more than 90 seconds to preserve usage; it had not completed, rendered, or overwritten an artifact.
- Current blocker: `qwen/qwen3.7-flash` response latency prevents confirming the revised prompt against a fresh non-fallback plan within the current usage budget.
- Next action: run one planner-only check when budget permits; inspect returned headings and visual kinds before spending time on a full render.
- Decision: attack the repeated-template failure from three sides: per-scene kind selection with a covalent/pH anti-pattern callout and a worked kind sequence in the prompt; feed the validation error back to the model on retry instead of redrawing a near-identical low-temperature sample; and expose `PLANNER_TIMEOUT_SECONDS` (default 120) because a 60-second budget caused live plans to fall back even when the prompt was satisfied.
- Validation: single live planner request with the revised prompt returned a valid varied non-fallback plan (`title`, `ph_scale`, `bullets`, `ph_scale`, `bullets`, `recap`) in ~110s; a second confirmed run passed with fallback disabled.
- Implementation: added `scripts/check_prompt.py` for one planner-only request (no retry, no fallback, no render) so prompt changes can be judged in a single call.
- User feedback: full renders are too slow to wait on during iteration; the user runs the render and reviews the MP4, then reports back.
- Next action: user runs `uv run python scripts/generate_video.py --question "How does the pH scale work?" --output artifacts/ph-scale_qwen` (with `PLANNER_TIMEOUT_SECONDS=120` in `.env`) and reviews whether scenes now use distinct animations.

## Backend service phase

- Decision: plan the FastAPI/SQLite worker boundary in `docs/plans/002-backend-job-service.md` before continuing implementation.
- Decision: keep the API, SQLite store, polling worker, and artifact publication as separate boundaries while reusing `VideoGenerator` unchanged.
- Decision: cap jobs at two total attempts; startup recovery requeues attempt one but marks an interrupted final attempt failed.
- Validation: all 13 tests pass, covering atomic claims, transitions, recovery, worker publication/retries, API lifecycle/artifacts, planner behavior, and offline rendering.
- Validation: dependency sync completed from cache and `git diff --check` passes.
- Current blocker: none for the local single-worker MVP.
- Next action: start API and worker together and submit one real job using the configured `.env`.
- Requested revision: explicitly document Swagger UI, prevent duplicate jobs for normalized-identical questions, reuse completed artifacts, and promote successfully rendered LLM plans into learned fallbacks for new topics.
- Decision: deduplicate with a database-enforced normalized `question_key`; avoid semantic/fuzzy matching in the MVP.
- Decision: promote learned fallbacks only after end-to-end render success and revalidate them on read. Resolution order will be live LLM, learned fallback, curated fallback, then failure.
- Implementation: added NFKC/case-folded question keys, concurrency-safe `get_or_create`, legacy schema migration, and completed-artifact reuse.
- Implementation: added explicit Swagger response models/media responses and documented `/docs`, `/openapi.json`, and `/redoc`.
- Implementation: added a validated SQLite learned-fallback repository, live → learned → curated resolution, usage tracking, and post-render worker promotion.
- Validation: all 20 tests pass; `git diff --check` passes.
- Current blocker: none.
- Next action: run API and worker with the configured `.env`, submit a new topic, then resubmit a normalized variant to verify real artifact reuse.

## Durable job run log

- Decision: store append-only lifecycle events in SQLite and expose them through `GET /videos/{id}/logs`; keep console logs for operators.
- Implementation: job creation, reuse, claims, retries, recovery, terminal transitions, generation, artifact publication, and learned-fallback promotion now emit ordered events.
- Validation: all 21 tests pass, including event ordering, attempt numbers, detail limits, concurrent reuse, worker milestones, API lookup, and OpenAPI documentation; `git diff --check` passes.
- Current blocker: none.
- Next action: run the API and worker with `.env`, then inspect one real job's `/logs` response while it completes.

## 2026-09-07

- Finding: the three non-fallback Qwen plans paraphrased the opening question, dropped curated qualifications, introduced anthropomorphic or misleading chemistry language, and sometimes selected unrelated renderers solely to increase visual-kind diversity.
- Decision: version the production prompt as Chemistry Planner v2, use the validated curated plan as a minimum factual baseline for each required question, set production temperature to 0.0, and reject any required-topic plan whose first narration sentence does not copy the question exactly.
- Validation: all three required prompts passed live against `qwen/qwen3.7-flash` with `fallback_used: false`; each exact question opened its narration, baseline concepts and caveats were retained, and visual kinds matched scene content. All 32 automated tests and the render smoke test pass; `git diff --check` passes.
- Next action: restart the worker and generate fresh artifacts; completed jobs remain immutable and will otherwise be reused by question deduplication.
- Finding: job `8ed8fb33-2993-443e-ab8a-63c5bc594fec` reached Qwen successfully twice but fell back because both responses mislabeled the deterministic first/final scene visual kinds.
- Fix: normalize the first `visual_kind` to `title` and the final one to `recap` before validating the remaining LLM plan, avoiding retries for positional labels the application already mandates.
- Validation: all 28 tests pass; a live Qwen3.7 Flash pH request then succeeded on attempt one with HTTP 200 and `fallback_used: false`; `git diff --check` passes.
- Next action: restart the worker; completed job metadata remains historical, while new jobs use the repaired planner.
- Fix: stop requiring native support for every OpenRouter parameter. Qwen3.7 Flash supports JSON output but not JSON-schema enforcement, so `require_parameters: true` excluded its only provider and caused HTTP 404; local `VideoPlan` validation continues to enforce the schema.
- Validation: all 27 tests pass, including a planner request regression assertion that no incompatible provider filter is sent; `git diff --check` passes. A live Qwen3.7 Flash probe reached OpenRouter, received HTTP 200, corrected one invalid plan on retry, and completed with `fallback_used: false`.
- Current blocker: restart the worker before retrying affected jobs so it loads the corrected request configuration; historical metadata remains unchanged.
- Next action: restart the worker so new jobs use the fix; completed job `db98736e-0776-4767-997b-6d7fe107a1e0` remains an immutable record of its fallback run.
- Fix: accept OpenRouter structured content as either a JSON string or decoded object, require providers that support request parameters, cap Qwen reasoning at 1,000 tokens and total output at 2,500, and retry transient 429/502/503/504 responses with bounded `Retry-After` backoff.
- Validation: all 27 tests pass, including decoded structured objects and a validation failure followed by a transient provider error and successful third attempt.
- Current blocker: live OpenRouter behavior has not been exercised by this change; existing jobs and metadata are unchanged.
- Next action: restart the worker and regenerate either reported fallback job to confirm a non-fallback plan and inspect its persisted planner-attempt diagnostics.
- Fix: deduplicate questions that differ only by surrounding punctuation, including `?`, while preserving meaningful internal punctuation such as chemical notation; migrate existing version-3 keys with the oldest job remaining canonical.
- Validation: all 25 tests pass, including concurrent punctuation-insensitive submission, preservation of `Na+`, and migration of punctuation-colliding legacy rows.
- Current blocker: none.
- Next action: restart the API and worker so the live SQLite database migrates to question-key version 4, then submit the with/without-`?` variants and confirm `reused: true`.
- Implementation: persist sanitized diagnostics for every OpenRouter attempt in early-written generation metadata and durable `planner_attempt_succeeded|failed` job events; learned and curated fallbacks retain the primary attempt history.
- Security: allowlist token/cost fields, store HTTP status without response bodies, omit rejected Pydantic inputs, cap validation detail, and never persist request headers, prompts, URLs, raw responses, or stack traces.
- Validation: all 24 tests pass, covering successful, invalid-plan, HTTP-error, fallback, and post-planning generation-failure paths.
- Current blocker: none; existing jobs do not gain diagnostics retroactively.
- Next action: restart the worker and regenerate the covalent question to read its exact planner outcome from `/videos/{id}/logs` and `metadata.json`.
- Decision: increase the planner request timeout default from 120 to 300 seconds for slow Qwen responses; with two attempts, a job may now wait up to roughly ten minutes before fallback.
- Decision: publish only the three accepted jobs' final MP4 files, not WAVs, intermediate clips, Manim caches, or machine-local concat manifests.
- Validation: all three published samples contain H.264 video and AAC audio, play under `ffprobe`, and run 61.892–114.025 seconds; the root README links each question directly to its MP4.
- Decision: prefer ElevenLabs River with `eleven_turbo_v2_5` when `ELEVENLABS_API_KEY` is configured; otherwise retain local Piper without changing entry points or the generation pipeline.
- Implementation: added direct HTTPX speech generation and FFmpeg MP3-to-WAV conversion using the existing dependencies; voice and model remain environment-configurable.
- Validation: all 23 tests pass, including provider selection, ElevenLabs request parameters, and audio conversion invocation. Live ElevenLabs generation was not attempted with the exposed credential.
- Current blocker: rotate the ElevenLabs key disclosed in chat before using the integration, then place only the replacement in the ignored `.env`.
- Next action: generate one scene with the rotated key and review River's pronunciation, pacing, and audio quality.
- Documentation: added the durable job-log storage location and `GET /videos/{id}/logs` example to the backend README.
- Finding: scene reveals consumed a fixed 68% of narration time, making complex visuals crawl; the title scene also subtracted an unplayed timing segment and clipped about 1.5 seconds of narration.
- Implementation: capped visual reveals at six seconds, grouped the pH cells into one staged reveal, and padded each rendered scene by one frame so FFmpeg preserves the complete WAV.
- Validation: all 21 tests pass; the reported pH job was re-rendered without new LLM/TTS calls as a 123.349-second H.264/AAC MP4, and its 19.367-second title visual fully covers the 19.365-second narration.
- Current blocker: none.
- Next action: review the updated pH artifact and tune the six-second reveal cap only if its perceived pace is still too slow or fast.
