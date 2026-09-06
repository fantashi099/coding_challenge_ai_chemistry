import json
import logging
import os
import time
from pathlib import Path

import httpx

from ..config import Settings
from ..fallbacks import FallbackPlanner, LearnedFallbackStore
from ..generator import VideoGenerator
from ..jobs import JobStore
from ..models import VideoPlan
from ..planner import OpenRouterPlanner

logger = logging.getLogger(__name__)


def _record_planner_attempts(store: JobStore, job_id: str, job_attempt: int, attempts) -> None:
    for attempt in attempts:
        data = dict(attempt.as_dict() if hasattr(attempt, "as_dict") else attempt)
        if data.get("detail"):
            data["detail"] = data["detail"][:500]
        outcome = data.get("outcome")
        event = "planner_attempt_succeeded" if outcome == "succeeded" else "planner_attempt_failed"
        store.record_event(job_id, event, job_attempt, json.dumps(data, separators=(",", ":")))


def _record_fallback(
    generator: VideoGenerator, fallbacks: LearnedFallbackStore, question: str, work_dir: Path
) -> str:
    metadata_path = work_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    source = getattr(getattr(generator, "planner", None), "last_source", "none")
    metadata["fallback_source"] = source
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    if source == "none":
        plan = VideoPlan.model_validate_json((work_dir / "plan.json").read_text())
        fallbacks.save(question, plan, metadata["model"])
    return source


def run_once(
    store: JobStore,
    generator: VideoGenerator,
    artifact_root: Path,
    fallbacks: LearnedFallbackStore | None = None,
) -> bool:
    job = store.claim()
    if not job:
        return False
    work_dir = artifact_root / job.id / "work"
    try:
        store.record_event(job.id, "generation_started", job.attempts)
        generated = generator.generate(job.question, work_dir)
        metadata_path = work_dir / "metadata.json"
        if metadata_path.is_file():
            _record_planner_attempts(
                store, job.id, job.attempts, json.loads(metadata_path.read_text()).get("planner_attempts", [])
            )
        store.record_event(job.id, "generation_finished", job.attempts)
        final = artifact_root / job.id / "video.mp4"
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(generated, final)
        store.record_event(job.id, "artifact_published", job.attempts)
        if fallbacks:
            try:
                if _record_fallback(generator, fallbacks, job.question, work_dir) == "none":
                    store.record_event(job.id, "fallback_promoted", job.attempts)
            except Exception as exc:
                store.record_event(
                    job.id,
                    "fallback_promotion_failed",
                    job.attempts,
                    f"{type(exc).__name__}: {exc}",
                )
                logger.exception("could not record fallback metadata for job %s", job.id)
        store.complete(job.id, final.resolve())
        logger.info("completed video job %s", job.id)
    except Exception as exc:
        attempts = getattr(exc, "attempts", ())
        metadata_path = work_dir / "metadata.json"
        if not attempts and metadata_path.is_file():
            attempts = json.loads(metadata_path.read_text()).get("planner_attempts", [])
        _record_planner_attempts(store, job.id, job.attempts, attempts)
        store.fail_attempt(job.id, f"{type(exc).__name__}: {exc}")
        logger.exception("video job %s attempt %s failed", job.id, job.attempts)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    store = JobStore(settings.database_path)
    fallbacks = LearnedFallbackStore(settings.database_path)
    recovered = store.recover_running()
    if recovered:
        logger.warning("recovered %s interrupted job(s)", recovered)
    planner = FallbackPlanner(
        OpenRouterPlanner(
            settings.openrouter_api_key,
            settings.openrouter_model,
            client=httpx.Client(timeout=settings.planner_timeout_seconds),
        ),
        fallbacks,
    )
    generator = VideoGenerator(settings, planner=planner)
    while True:
        if not run_once(store, generator, settings.artifact_root, fallbacks):
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
