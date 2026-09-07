# Chemistry Planner Prompt Spec

Production model: `qwen/qwen3.7-flash`

Temperature: `0.0`

Output: strict `VideoPlan` JSON schema, locally validated

## Required cases

1. `How does the pH scale work?` — speak the exact question first; retain hydrogen-ion, 0–14, neutral-near-room-temperature, logarithmic tenfold, and variable-example concepts.
2. `Why do atoms form covalent bonds?` — speak the exact question first; explain lower energy and shared electron density without anthropomorphism.
3. `What is the difference between ionic and covalent bonding?` — speak the exact question first; retain transfer/ions/lattice, sharing/electron density, typical properties, exceptions, and continuum concepts.

Failure behavior remains validated fallback: malformed, incomplete, or schema-invalid output retries once, then uses the validated baseline.

## Changelog

### v2 — 2026-09-07

- Ground the three required questions with their curated plans as minimum content baselines.
- Require the exact user question as the first spoken sentence.
- Ban observed anthropomorphic and electron-orbit misconceptions.
- Clarify that endpoint kinds count toward visual diversity and that renderer kinds are literal.

### v1 — 2026-09-06

- Initial inline chemistry planner prompt.
