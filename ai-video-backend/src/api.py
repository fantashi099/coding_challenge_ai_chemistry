from pathlib import Path

from typing import Literal

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import Settings
from .jobs import Job, JobStore


class VideoRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(
        min_length=3,
        max_length=500,
        examples=["How does the pH scale work?"],
    )


class JobResponse(BaseModel):
    id: str
    question: str
    status: Literal["queued", "running", "completed", "failed"]
    attempts: int
    created_at: str
    updated_at: str
    error: str | None
    artifact_url: str | None


class CreateVideoResponse(JobResponse):
    reused: bool


def create_app(settings: Settings | None = None, store: JobStore | None = None) -> FastAPI:
    settings = settings or Settings()
    jobs = store or JobStore(settings.database_path)
    app = FastAPI(
        title="AI Chemistry Video Service",
        description="Queue narrated, animated chemistry explanation videos and retrieve completed MP4 artifacts.",
        version="0.2.0",
        openapi_tags=[{"name": "videos", "description": "Video generation jobs and artifacts."}],
    )

    def public(job: Job) -> dict:
        data = job.as_dict()
        data["artifact_url"] = f"/videos/{job.id}/artifact" if job.status == "completed" else None
        data.pop("artifact_path")
        return data

    @app.post(
        "/videos",
        response_model=CreateVideoResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["videos"],
        summary="Create or reuse a video job",
        responses={
            200: {"model": CreateVideoResponse, "description": "Existing terminal job reused"},
            202: {"model": CreateVideoResponse, "description": "Job accepted or still in progress"},
        },
    )
    async def create_video(request: VideoRequest, response: Response) -> dict:
        job, created = jobs.get_or_create(request.question)
        reused = not created
        response.status_code = 200 if reused and job.status in {"completed", "failed"} else 202
        return {**public(job), "reused": reused}

    @app.get("/videos", response_model=list[JobResponse], tags=["videos"], summary="List video jobs")
    async def list_videos() -> list[dict]:
        return [public(job) for job in jobs.list()]

    @app.get(
        "/videos/{job_id}",
        response_model=JobResponse,
        tags=["videos"],
        summary="Get a video job",
        responses={404: {"description": "Job not found"}},
    )
    async def get_video(job_id: str) -> dict:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "video job not found")
        return public(job)

    @app.get(
        "/videos/{job_id}/artifact",
        response_class=StreamingResponse,
        tags=["videos"],
        summary="Download a completed video",
        responses={
            200: {"description": "Completed MP4", "content": {"video/mp4": {}}},
            404: {"description": "Job or artifact not found"},
            409: {"description": "Video is unfinished"},
        },
    )
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
