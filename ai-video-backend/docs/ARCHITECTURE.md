# Architecture

FastAPI only validates requests and reads/writes job records. SQLite is the durable coordination boundary: clients enqueue, while a separate worker atomically claims one job with `BEGIN IMMEDIATE`. A claimed job is retried once, then ends as `completed` or `failed`; startup recovery returns interrupted `running` jobs to the queue.

`VideoGenerator` is the single generation boundary used by CLI and worker. It asks OpenRouter for schema-constrained JSON, validates the full plan, retries once, and uses curated plans for the three required questions if necessary. Manim renders animated educational visuals, Piper synthesizes local speech, and FFmpeg muxes them into H.264/AAC MP4. Replacing any provider only requires supplying the corresponding planner, narrator, renderer, or composer interface.

Each job renders into `artifacts/jobs/<id>/work`. Only after FFmpeg succeeds does the worker atomically move `video.mp4` to the job directory and publish that path in SQLite. Intermediate plans, media, and metadata remain available for diagnosis without exposing partial video through the API.
