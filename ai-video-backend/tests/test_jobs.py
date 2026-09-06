from concurrent.futures import ThreadPoolExecutor

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
