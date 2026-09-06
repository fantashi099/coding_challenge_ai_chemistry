from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import Settings
from .jobs import Job, JobStore


class VideoRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


def create_app(settings: Settings | None = None, store: JobStore | None = None) -> FastAPI:
    settings = settings or Settings()
    jobs = store or JobStore(settings.database_path)
    app = FastAPI(title="AI Chemistry Video Service", version="0.1.0")

    def public(job: Job) -> dict:
        data = job.dict()
        data["artifact_url"] = f"/videos/{job.id}/artifact" if job.status == "completed" else None
        data.pop("artifact_path")
        return data

    @app.post("/videos", status_code=status.HTTP_202_ACCEPTED)
    async def create_video(request: VideoRequest) -> dict:
        return public(jobs.create(request.question.strip()))

    @app.get("/videos")
    async def list_videos() -> list[dict]:
        return [public(job) for job in jobs.list()]

    @app.get("/videos/{job_id}")
    async def get_video(job_id: str) -> dict:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "video job not found")
        return public(job)

    @app.get("/videos/{job_id}/artifact", response_class=StreamingResponse)
    async def get_artifact(job_id: str) -> StreamingResponse:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "video job not found")
        if job.status != "completed":
            raise HTTPException(409, "video is not complete")
        path = Path(job.artifact_path or "")
        if not path.is_file():
            raise HTTPException(404, "video artifact is missing")
        async def chunks():
            with path.open("rb") as artifact:
                while chunk := artifact.read(1024 * 1024):
                    yield chunk

        return StreamingResponse(
            chunks(),
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{job.id}.mp4"'},
        )

    return app


app = create_app()
