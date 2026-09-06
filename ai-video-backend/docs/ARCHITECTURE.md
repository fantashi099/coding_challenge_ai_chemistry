# Architecture

FastAPI validates requests and persists jobs; it never renders video. Unicode-normalized, case-folded question keys have a database uniqueness constraint, so concurrent duplicate requests return one job and reuse its artifact. SQLite is the durable coordination boundary, with `BEGIN IMMEDIATE` ensuring only one worker can claim a queued job. The separately launched worker retries once and recovers interrupted work without exceeding two total attempts.

The CLI and worker both call the same `VideoGenerator`. It asks OpenRouter for schema-constrained JSON, validates the full plan, retries once, and uses curated plans only for the three required questions if generation still fails. Manim renders animated educational visuals, Piper synthesizes local speech, and FFmpeg muxes them into H.264/AAC MP4.

After an end-to-end successful live-LLM render, the worker promotes its validated plan into the SQLite learned-fallback repository. If both later LLM attempts fail, the planner wrapper revalidates and uses that learned plan before consulting the three curated plans. Corrupt cache entries are reported and ignored; cache failures never discard an already completed video.

Each job renders into `artifacts/jobs/<id>/work`. The worker atomically moves the completed MP4 to `artifacts/jobs/<id>/video.mp4` before marking the job completed, so the API never serves partial output. Intermediate plans, visuals, audio, and metadata remain in the work directory for diagnosis.
