from concurrent.futures import ThreadPoolExecutor

import pytest

from src.jobs import JobStore


def test_atomic_claim_and_transitions(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    created = store.create("How does the pH scale work?")

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: JobStore(store.path).claim(), range(2)))

    claimed = [job for job in claims if job]
    assert len(claimed) == 1
    assert claimed[0].id == created.id
    assert claimed[0].status == "running"
    assert claimed[0].attempts == 1

    store.fail_attempt(created.id, "temporary")
    assert store.get(created.id).status == "queued"
    store.claim()
    store.fail_attempt(created.id, "permanent")
    assert store.get(created.id).status == "failed"
    with pytest.raises(ValueError):
        store.complete(created.id, tmp_path / "missing.mp4")


def test_recovery_and_completion(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.create("question")
    store.claim()
    assert store.recover_running() == 1
    assert store.get(job.id).status == "queued"
    store.claim()
    artifact = tmp_path / "video.mp4"
    artifact.write_bytes(b"video")
    store.complete(job.id, artifact)
    completed = store.get(job.id)
    assert completed.status == "completed"
    assert completed.artifact_path == str(artifact)
