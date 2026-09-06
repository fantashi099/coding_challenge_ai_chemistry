import asyncio

import httpx

from src.api import create_app
from src.jobs import JobStore


def test_video_job_api_lifecycle(tmp_path):
    async def exercise():
        store = JobStore(tmp_path / "jobs.sqlite3")
        transport = httpx.ASGITransport(app=create_app(store=store))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/videos", json={"question": "How does the pH scale work?"})
            assert response.status_code == 202
            job_id = response.json()["id"]
            assert response.json()["status"] == "queued"
            assert (await client.get(f"/videos/{job_id}/artifact")).status_code == 409
            assert (await client.get("/videos/missing")).status_code == 404
            assert (await client.get("/videos/missing/artifact")).status_code == 404
            assert (await client.get("/videos")).json()[0]["id"] == job_id

            store.claim()
            artifact = tmp_path / "video.mp4"
            artifact.write_bytes(b"video data")
            store.complete(job_id, artifact)
            detail = (await client.get(f"/videos/{job_id}")).json()
            assert detail["status"] == "completed"
            assert detail["artifact_url"] == f"/videos/{job_id}/artifact"
            assert (await client.get(detail["artifact_url"])).content == b"video data"

    asyncio.run(exercise())


def test_api_exposes_final_failure(tmp_path):
    async def exercise():
        store = JobStore(tmp_path / "jobs.sqlite3")
        transport = httpx.ASGITransport(app=create_app(store=store))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            job_id = (await client.post("/videos", json={"question": "A valid question"})).json()["id"]
            store.claim()
            store.fail_attempt(job_id, "first")
            store.claim()
            store.fail_attempt(job_id, "second")
            detail = (await client.get(f"/videos/{job_id}")).json()
            assert detail["status"] == "failed"
            assert detail["error"] == "second"

    asyncio.run(exercise())
