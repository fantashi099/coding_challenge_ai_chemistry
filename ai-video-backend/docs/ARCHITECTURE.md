# Architecture

The CLI calls one `VideoGenerator`. It asks OpenRouter for schema-constrained JSON, validates the full plan, retries once, and uses curated plans only for the three required questions if generation still fails. Manim renders animated educational visuals, Piper synthesizes local speech, and FFmpeg muxes them into H.264/AAC MP4.

The output directory retains `plan.json`, per-scene visuals and audio, generation metadata, and `video.mp4`. Planner, narrator, renderer, and composer boundaries remain replaceable without adding a service layer before it is needed.
