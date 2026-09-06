import logging
import os
import time
from pathlib import Path

from ..config import Settings
from ..generator import VideoGenerator
from ..jobs import JobStore

logger = logging.getLogger(__name__)


def run_once(store: JobStore, generator: VideoGenerator, artifact_root: Path) -> bool:
    job = store.claim()
    if not job:
        return False
    work_dir = artifact_root / job.id / "work"
    try:
        generated = generator.generate(job.question, work_dir)
        final = artifact_root / job.id / "video.mp4"
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(generated, final)
        store.complete(job.id, final.resolve())
        logger.info("completed video job %s", job.id)
    except Exception as exc:
        store.fail_attempt(job.id, f"{type(exc).__name__}: {exc}")
        logger.exception("video job %s attempt %s failed", job.id, job.attempts)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    store = JobStore(settings.database_path)
    recovered = store.recover_running()
    if recovered:
        logger.warning("recovered %s interrupted job(s)", recovered)
    generator = VideoGenerator(settings)
    while True:
        if not run_once(store, generator, settings.artifact_root):
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
