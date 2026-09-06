# Repository guidance

- Use `uv` for Python dependency management and commands.
- Keep changes minimal and reuse `src.generator.VideoGenerator` from every entry point.
- Do not mark work complete until relevant tests and artifact checks pass.
- Record dated decisions, validation, blockers, and the next action in `docs/PROGRESS.md`.
- Keep secrets in an ignored `.env`; document variables in `.env.example`.
