from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from src.jobs import JobStore


def test_create_list_atomic_claim_and_transitions(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    first = store.create("first question")
    second = store.create("second question")
    assert [job.id for job in store.list()] == [second.id, first.id]

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: JobStore(store.path).claim(), range(2)))
    assert {job.id for job in claims if job} == {first.id, second.id}

    store.fail_attempt(first.id, "temporary")
    assert store.get(first.id).status == "queued"
    store.claim()
    store.fail_attempt(first.id, "permanent")
    assert store.get(first.id).status == "failed"
    with pytest.raises(ValueError, match="invalid job transition"):
        store.complete(first.id, tmp_path / "video.mp4")


def test_completion_and_recovery_respect_two_attempt_limit(tmp_path):
    retry_store = JobStore(tmp_path / "retry.sqlite3")
    retry = retry_store.create("retry me")
    retry_store.claim()
    assert retry_store.recover_running() == 1
    assert retry_store.get(retry.id).status == "queued"

    final_store = JobStore(tmp_path / "final.sqlite3")
    final = final_store.create("final attempt")
    final_store.claim()
    final_store.fail_attempt(final.id, "first failure")
    final_store.claim()
    assert final_store.recover_running() == 1
    assert final_store.get(final.id).status == "failed"
    assert final_store.claim() is None

    complete_store = JobStore(tmp_path / "complete.sqlite3")
    completed = complete_store.create("complete me")
    complete_store.claim()
    artifact = tmp_path / "published.mp4"
    complete_store.complete(completed.id, artifact)
    assert complete_store.get(completed.id).artifact_path == str(artifact)


def test_normalized_question_is_deduplicated_concurrently(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")

    def submit(question):
        return JobStore(store.path).get_or_create(question)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, ["  HOW   does pH work? ", "how does ph work?"]))
    assert results[0][0].id == results[1][0].id
    assert sorted(created for _, created in results) == [False, True]
    assert len(store.list()) == 1


def test_legacy_schema_migration_retains_duplicate_rows(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute(
            """CREATE TABLE jobs (
                id TEXT PRIMARY KEY, question TEXT NOT NULL, status TEXT NOT NULL,
                attempts INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                artifact_path TEXT, error TEXT
            )"""
        )
        rows = [
            ("oldest", "Same Question", "completed", 1, "2026-01-01", "2026-01-01", "/first.mp4", None),
            ("newer", " same  question ", "completed", 1, "2026-01-02", "2026-01-02", "/second.mp4", None),
        ]
        db.executemany("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)

    store = JobStore(path)
    canonical, created = store.get_or_create("SAME QUESTION")
    assert canonical.id == "oldest"
    assert created is False
    assert len(store.list()) == 2
