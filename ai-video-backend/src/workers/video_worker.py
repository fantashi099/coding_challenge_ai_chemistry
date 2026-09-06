import os
import time
from pathlib import Path

from ..config import Settings
from ..generator import VideoGenerator
from ..jobs import JobStore


def run_once(store: JobStore, generator: VideoGenerator, artifact_root: Path) -> bool:
    job = store.claim()
    if not job:
        return False
    job_dir = artifact_root / job.id
    work_dir = job_dir / "work"
    try:
        generated = generator.generate(job.question, work_dir)
        final = job_dir / "video.mp4"
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(generated, final)
        store.complete(job.id, final.resolve())
    except Exception as exc:
        store.fail_attempt(job.id, f"{type(exc).__name__}: {exc}")
    return True


def main() -> None:
    settings = Settings()
    store = JobStore(settings.database_path)
    recovered = store.recover_running()
    if recovered:
        print(f"Recovered {recovered} interrupted job(s)", flush=True)
    generator = VideoGenerator(settings)
    while True:
        if not run_once(store, generator, settings.artifact_root):
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
