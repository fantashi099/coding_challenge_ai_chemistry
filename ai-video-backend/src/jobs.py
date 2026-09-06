from __future__ import annotations

import sqlite3
import unicodedata
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


def _now() -> str:
    return datetime.now(UTC).isoformat()


def question_key(question: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", question).casefold().split())
    while normalized and unicodedata.category(normalized[0]).startswith("P"):
        normalized = normalized[1:].lstrip()
    while normalized and unicodedata.category(normalized[-1]).startswith("P"):
        normalized = normalized[:-1].rstrip()
    return normalized


@dataclass(frozen=True)
class Job:
    id: str
    question: str
    status: str
    attempts: int
    created_at: str
    updated_at: str
    artifact_path: str | None
    error: str | None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobEvent:
    id: int
    job_id: str
    event: str
    attempt: int | None
    detail: str | None
    created_at: str

    def as_dict(self) -> dict:
        return asdict(self)


class JobStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            db.execute(
                """CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    question_key TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    artifact_path TEXT,
                    error TEXT
                )"""
            )
            if version < 4:
                db.execute("DROP INDEX IF EXISTS jobs_question_key")
            self._migrate_question_keys(db, rebuild=version < 4)
            db.execute("CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(status, created_at)")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS jobs_question_key ON jobs(question_key)")
            db.execute(
                """CREATE TABLE IF NOT EXISTS job_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id),
                    event TEXT NOT NULL,
                    attempt INTEGER,
                    detail TEXT,
                    created_at TEXT NOT NULL
                )"""
            )
            db.execute("CREATE INDEX IF NOT EXISTS job_events_job ON job_events(job_id, id)")
            db.execute("PRAGMA user_version=4")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _event(
        db: sqlite3.Connection,
        job_id: str,
        event: str,
        attempt: int | None = None,
        detail: str | None = None,
    ) -> None:
        db.execute(
            "INSERT INTO job_events (job_id, event, attempt, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, event, attempt, detail[:1000] if detail else None, _now()),
        )

    @staticmethod
    def _job(row: sqlite3.Row | None) -> Job | None:
        return Job(**dict(row)) if row else None

    @staticmethod
    def _migrate_question_keys(db: sqlite3.Connection, rebuild: bool = False) -> None:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
        if "question_key" not in columns:
            db.execute("ALTER TABLE jobs ADD COLUMN question_key TEXT")
            rebuild = True
        if not rebuild:
            return
        seen: set[str] = set()
        for row in db.execute("SELECT id, question FROM jobs ORDER BY created_at, id"):
            key = question_key(row["question"])
            stored_key = key if key not in seen else f"{key}::legacy::{row['id']}"
            db.execute("UPDATE jobs SET question_key = ? WHERE id = ?", (stored_key, row["id"]))
            seen.add(key)

    def create(self, question: str) -> Job:
        return self.get_or_create(question)[0]

    def get_or_create(self, question: str) -> tuple[Job, bool]:
        key = question_key(question)
        now = _now()
        job = Job(str(uuid.uuid4()), question, "queued", 0, now, now, None, None)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT id, question, status, attempts, created_at, updated_at, artifact_path, error FROM jobs WHERE question_key = ?",
                (key,),
            ).fetchone()
            if existing:
                self._event(db, existing["id"], "reused", existing["attempts"])
                db.commit()
                return Job(**dict(existing)), False
            db.execute(
                """INSERT INTO jobs
                   (id, question, question_key, status, attempts, created_at, updated_at, artifact_path, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job.id, job.question, key, job.status, job.attempts, job.created_at, job.updated_at, None, None),
            )
            self._event(db, job.id, "queued", 0)
            db.commit()
        return job, True

    def get(self, job_id: str) -> Job | None:
        with self._connect() as db:
            return self._job(db.execute(
                "SELECT id, question, status, attempts, created_at, updated_at, artifact_path, error FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone())

    def list(self) -> list[Job]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, question, status, attempts, created_at, updated_at, artifact_path, error FROM jobs ORDER BY created_at DESC"
            ).fetchall()
        return [Job(**dict(row)) for row in rows]

    def events(self, job_id: str) -> list[JobEvent]:
        if not self.get(job_id):
            raise KeyError(job_id)
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, job_id, event, attempt, detail, created_at FROM job_events WHERE job_id = ? ORDER BY id",
                (job_id,),
            ).fetchall()
        return [JobEvent(**dict(row)) for row in rows]

    def record_event(
        self, job_id: str, event: str, attempt: int | None = None, detail: str | None = None
    ) -> None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone():
                db.rollback()
                raise KeyError(job_id)
            self._event(db, job_id, event, attempt, detail)
            db.commit()

    def claim(self) -> Job | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM jobs WHERE status = 'queued' AND attempts < 2 ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                db.commit()
                return None
            db.execute(
                "UPDATE jobs SET status = 'running', attempts = attempts + 1, updated_at = ?, error = NULL WHERE id = ?",
                (_now(), row["id"]),
            )
            job = self._job(db.execute(
                "SELECT id, question, status, attempts, created_at, updated_at, artifact_path, error FROM jobs WHERE id = ?",
                (row["id"],),
            ).fetchone())
            self._event(db, row["id"], "running", job.attempts)
            db.commit()
            return job

    def complete(self, job_id: str, artifact_path: Path) -> None:
        self._transition(job_id, "completed", artifact_path=str(artifact_path))

    def fail_attempt(self, job_id: str, error: str) -> None:
        job = self.get(job_id)
        if not job or job.status != "running":
            raise ValueError("only a running job can fail")
        self._transition(job_id, "failed" if job.attempts >= 2 else "queued", error=error[:2000])

    def recover_running(self) -> int:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            running = db.execute("SELECT id, attempts FROM jobs WHERE status = 'running'").fetchall()
            retry = db.execute(
                "UPDATE jobs SET status = 'queued', updated_at = ?, error = 'worker interrupted; retrying' WHERE status = 'running' AND attempts < 2",
                (_now(),),
            ).rowcount
            failed = db.execute(
                "UPDATE jobs SET status = 'failed', updated_at = ?, error = 'worker interrupted during final attempt' WHERE status = 'running'",
                (_now(),),
            ).rowcount
            for row in running:
                event = "recovered" if row["attempts"] < 2 else "failed"
                detail = "worker interrupted; retrying" if event == "recovered" else "worker interrupted during final attempt"
                self._event(db, row["id"], event, row["attempts"], detail)
            db.commit()
        return retry + failed

    def _transition(
        self, job_id: str, status: str, artifact_path: str | None = None, error: str | None = None
    ) -> None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute(
                "UPDATE jobs SET status = ?, updated_at = ?, artifact_path = ?, error = ? WHERE id = ? AND status = 'running'",
                (status, _now(), artifact_path, error, job_id),
            ).rowcount
            if changed == 1:
                event = "retry_scheduled" if status == "queued" else status
                job = db.execute("SELECT attempts FROM jobs WHERE id = ?", (job_id,)).fetchone()
                self._event(db, job_id, event, job["attempts"], error)
            db.commit()
        if changed != 1:
            raise ValueError("invalid job transition")
