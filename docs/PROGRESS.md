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
- Next action: render and review a chemistry sample with the reference-inspired theme.
