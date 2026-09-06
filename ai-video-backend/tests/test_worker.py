from pathlib import Path
import json
from types import SimpleNamespace

from src.curated import CURATED_PLANS
from src.fallbacks import LearnedFallbackStore
from src.jobs import JobStore
from src.workers.video_worker import run_once


class SuccessfulGenerator:
    def generate(self, question: str, output: Path) -> Path:
        output.mkdir(parents=True)
        video = output / "video.mp4"
        video.write_bytes(question.encode())
        return video


class FailingGenerator:
    def generate(self, question: str, output: Path) -> Path:
        raise RuntimeError("provider unavailable")


class CacheableGenerator:
    planner = SimpleNamespace(last_source="none")

    def generate(self, question: str, output: Path) -> Path:
        output.mkdir(parents=True)
        (output / "plan.json").write_text(next(iter(CURATED_PLANS.values())).model_dump_json())
        (output / "metadata.json").write_text(json.dumps({"model": "test-model"}))
        video = output / "video.mp4"
        video.write_bytes(b"video")
        return video


def test_worker_publishes_only_completed_video(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.create("chemistry question")
    root = tmp_path / "artifacts"

    assert run_once(store, SuccessfulGenerator(), root) is True
    completed = store.get(job.id)
    assert completed.status == "completed"
    assert Path(completed.artifact_path).read_bytes() == b"chemistry question"
    assert not (root / job.id / "work" / "video.mp4").exists()
    assert run_once(store, SuccessfulGenerator(), root) is False


def test_worker_retries_once_then_fails(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.create("chemistry question")

    run_once(store, FailingGenerator(), tmp_path / "artifacts")
    assert store.get(job.id).status == "queued"
    run_once(store, FailingGenerator(), tmp_path / "artifacts")
    failed = store.get(job.id)
    assert failed.status == "failed"
    assert failed.attempts == 2
    assert "provider unavailable" in failed.error


def test_worker_promotes_plan_only_after_successful_render(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    fallbacks = LearnedFallbackStore(store.path)
    job = store.create("new topic")
    root = tmp_path / "artifacts"

    run_once(store, CacheableGenerator(), root, fallbacks)
    learned = fallbacks.use("NEW TOPIC")
    assert learned is not None
    assert learned.source_model == "test-model"
    metadata = json.loads((root / job.id / "work" / "metadata.json").read_text())
    assert metadata["fallback_source"] == "none"
