import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


def _now() -> str:
    return datetime.now(UTC).isoformat()


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

    def dict(self) -> dict:
        return asdict(self)


class JobStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    artifact_path TEXT,
                    error TEXT
                )"""
            )

    @staticmethod
    def _job(row: sqlite3.Row | None) -> Job | None:
        return Job(**dict(row)) if row else None

    def create(self, question: str) -> Job:
        now = _now()
        job = Job(str(uuid.uuid4()), question, "queued", 0, now, now, None, None)
        with self._connect() as db:
            db.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(job.dict().values()),
            )
        return job

    def get(self, job_id: str) -> Job | None:
        with self._connect() as db:
            return self._job(db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())

    def list(self) -> list[Job]:
        with self._connect() as db:
            return [self._job(row) for row in db.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()]  # type: ignore[misc]

    def claim(self) -> Job | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                db.commit()
                return None
            now = _now()
            db.execute(
                "UPDATE jobs SET status = 'running', attempts = attempts + 1, updated_at = ?, error = NULL WHERE id = ?",
                (now, row["id"]),
            )
            job = self._job(db.execute("SELECT * FROM jobs WHERE id = ?", (row["id"],)).fetchone())
            db.commit()
            return job

    def complete(self, job_id: str, artifact_path: Path) -> None:
        self._transition(job_id, "completed", artifact_path=str(artifact_path))

    def fail_attempt(self, job_id: str, error: str, max_attempts: int = 2) -> None:
        job = self.get(job_id)
        if not job or job.status != "running":
            raise ValueError("only a running job can fail")
        status = "failed" if job.attempts >= max_attempts else "queued"
        self._transition(job_id, status, error=error[:2000])

    def recover_running(self) -> int:
        with self._connect() as db:
            result = db.execute(
                "UPDATE jobs SET status = 'queued', updated_at = ?, error = 'worker interrupted; retrying' WHERE status = 'running'",
                (_now(),),
            )
            return result.rowcount

    def _transition(
        self, job_id: str, status: str, artifact_path: str | None = None, error: str | None = None
    ) -> None:
        with self._connect() as db:
            result = db.execute(
                "UPDATE jobs SET status = ?, updated_at = ?, artifact_path = ?, error = ? WHERE id = ? AND status = 'running'",
                (status, _now(), artifact_path, error, job_id),
            )
            if result.rowcount != 1:
                raise ValueError("invalid job transition")
