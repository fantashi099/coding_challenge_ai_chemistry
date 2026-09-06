# 002 — Backend job service

Expose generation as a FastAPI job API backed by SQLite. A separate polling worker atomically claims queued jobs, retries each at most twice, recovers interrupted work at startup, and publishes an artifact only after successful generation.

Lifecycle: `queued → running → completed | queued (retry) → failed`.
