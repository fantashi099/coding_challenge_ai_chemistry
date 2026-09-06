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
