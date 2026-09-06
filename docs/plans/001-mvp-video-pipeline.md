# 001 — MVP video pipeline

Build a validated planner, animated Manim slide renderer, Piper narration adapter, and FFmpeg compositor behind one `VideoGenerator`. The three required questions have curated fallbacks; arbitrary questions require OpenRouter. Preserve the plan, intermediate media, metadata, and final MP4 for inspection.

Acceptance: 4–7 coherent scenes, 140–360 narration words, 1280×720 H.264/AAC output lasting 1–3 minutes, and a deterministic offline render test.

## Visual-variety quality gate

- The first scene uses `title`, the final scene uses `recap`, and every plan uses at least three visual kinds.
- No visual kind appears more than twice; invalid LLM plans retry before curated fallback.
- Visual kinds must match their chemistry semantics: `ph_scale` for ranges/examples, `covalent_sharing` only for shared electrons, `ionic_transfer` only for ion formation, and `bond_comparison` only for contrasts.
- Logarithmic rules and concepts without a dedicated diagram use `bullets`.
- The XGBoost reference guides the black/neon visual language, not its branding or subject matter.

- Every kind's definition carries an anti-pattern clause (a pH/ion/rules scene is never `covalent_sharing`), plus a worked kind sequence and a final self-count instruction.
- On retry, the planner returns the schema error to the model instead of resampling the same low-temperature plan; `PLANNER_TIMEOUT_SECONDS` (default 120) is separately configurable because 60 seconds timed out live Qwen responses.

## Remaining verification

`scripts/check_prompt.py` performs one planner-only request (no retry, no fallback, no render) for fast prompt iteration. A single live check with the revised prompt passed validation with varied kinds (`title`, `ph_scale`, `bullets`, `ph_scale`, `bullets`, `recap`). Remaining: render the scripted video locally and confirm distinct animations per scene in the MP4, then repeat for the bond topics if desired.
