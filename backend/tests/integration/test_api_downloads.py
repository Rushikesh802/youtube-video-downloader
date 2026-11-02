"""Integration tests for the download jobs API."""
import pytest
from httpx import AsyncClient


async def _get_auth_headers(client: AsyncClient, email: str = "worker_user@example.com") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_download_job_unauthorized(client: AsyncClient):
    """POST /downloads without token must return 401."""
    res = await client.post(
        "/api/v1/downloads",
        json={"media_id": "dummy-id", "format": "mp4", "resolution": "720p"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_download_job_and_lifecycle(client: AsyncClient):
    """Complete lifecycle test: inspect URL -> create download job -> check status -> list -> delete."""
    headers = await _get_auth_headers(client, "lifecycle@example.com")

    # 1. Inspect metadata for test fixture
    meta_res = await client.post(
        "/api/v1/videos/metadata",
        json={"url": "https://www.youtube.com/watch?v=test_720p"},
        headers=headers,
    )
    assert meta_res.status_code == 200
    media_id = meta_res.json()["media_id"]

    # 2. Queue download job (should return 202 Accepted)
    job_payload = {
        "media_id": media_id,
        "format": "mp4",
        "resolution": "720p",
    }
    create_res = await client.post("/api/v1/downloads", json=job_payload, headers=headers)
    assert create_res.status_code == 202
    job_data = create_res.json()
    assert "job_id" in job_data
    assert job_data["status"] == "queued"
    job_id = job_data["job_id"]

    # 3. Check job status (GET /api/v1/downloads/{id})
    get_res = await client.get(f"/api/v1/downloads/{job_id}", headers=headers)
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["id"] == job_id
    assert details["media_id"] == media_id
    assert details["format"] == "mp4"
    assert details["resolution"] == "720p"
    assert details["status"] == "queued"

    # 4. List user downloads (GET /api/v1/downloads)
    list_res = await client.get("/api/v1/downloads", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == job_id for item in list_data["items"])

    # 5. Delete job (DELETE /api/v1/downloads/{id})
    del_res = await client.delete(f"/api/v1/downloads/{job_id}", headers=headers)
    assert del_res.status_code == 200

    # 6. Verify job is deleted -> returns 404
    check_del = await client.get(f"/api/v1/downloads/{job_id}", headers=headers)
    assert check_del.status_code == 404


@pytest.mark.asyncio
async def test_download_quota_limit(client: AsyncClient):
    """Attempting to exceed concurrent jobs limit must return 429."""
    headers = await _get_auth_headers(client, "quota@example.com")

    # Get media ID
    meta_res = await client.post(
        "/api/v1/videos/metadata",
        json={"url": "https://www.youtube.com/watch?v=test_720p"},
        headers=headers,
    )
    media_id = meta_res.json()["media_id"]

    # MAX_USER_CONCURRENT_JOBS defaults to 2
    # Create 1st job
    res1 = await client.post(
        "/api/v1/downloads",
        json={"media_id": media_id, "format": "mp4", "resolution": "720p"},
        headers=headers,
    )
    assert res1.status_code == 202

    # Create 2nd job
    res2 = await client.post(
        "/api/v1/downloads",
        json={"media_id": media_id, "format": "mp3", "resolution": "audio_only"},
        headers=headers,
    )
    assert res2.status_code == 202

    # Attempt 3rd job -> should be blocked by quota with 429
    res3 = await client.post(
        "/api/v1/downloads",
        json={"media_id": media_id, "format": "webm", "resolution": "720p"},
        headers=headers,
    )
    assert res3.status_code == 429
    assert "quota" in res3.json()["error"].lower() or "limit" in res3.json()["error"].lower()
