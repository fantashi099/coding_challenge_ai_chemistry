# Progress

## 2026-09-06

- Decision: use validated OpenRouter structured output with one retry and curated fallbacks for only the three required questions.
- Decision: use animated Manim slides and Piper narration; FFmpeg muxes narration and concatenates scenes.
- Decision: SQLite uses `BEGIN IMMEDIATE` for atomic claiming; incomplete artifacts remain inside per-job work directories.
- Validation: pending implementation tests and sample render review.
- Blocker: Piper voice/model is not installed in the initial environment.
- Next action: implement, test, then generate and inspect the three sample videos.
