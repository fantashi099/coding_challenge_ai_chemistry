# 001 — MVP video pipeline

Build a validated planner, animated Manim slide renderer, Piper narration adapter, and FFmpeg compositor behind one `VideoGenerator`. The three required questions have curated fallbacks; arbitrary questions require OpenRouter. Preserve the plan, intermediate media, metadata, and final MP4 for inspection.

Acceptance: 4–7 coherent scenes, 140–360 narration words, 1280×720 H.264/AAC output lasting 1–3 minutes, and a deterministic offline render test.

## Visual-variety quality gate

- The first scene uses `title`, the final scene uses `recap`, and every plan uses at least three visual kinds.
- No visual kind appears more than twice; invalid LLM plans retry before curated fallback.
- Visual kinds must match their chemistry semantics: `ph_scale` for ranges/examples, `covalent_sharing` only for shared electrons, `ionic_transfer` only for ion formation, and `bond_comparison` only for contrasts.
- Logarithmic rules and concepts without a dedicated diagram use `bullets`.
- The XGBoost reference guides the black/neon visual language, not its branding or subject matter.

## Remaining verification

Run one planner-only request with `qwen/qwen3.7-flash`, confirm it does not fall back and returns varied semantic visual kinds, then render and manually review the resulting MP4. If Qwen continues taking longer than the current 60-second response timeout, evaluate a faster model or a separately configurable planner timeout before changing the rendering pipeline.
