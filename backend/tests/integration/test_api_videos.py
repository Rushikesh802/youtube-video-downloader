"""Integration tests for the video metadata API endpoint."""
import pytest
from httpx import AsyncClient


async def _get_auth_headers(client: AsyncClient, email: str = "user@example.com") -> dict:
    """Register and return Authorization header for a test user."""
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
async def test_metadata_requires_auth(client: AsyncClient):
    """Unauthenticated request must be rejected with 401."""
    res = await client.post(
        "/api/v1/videos/metadata",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_metadata_rejected_for_disallowed_domain(client: AsyncClient):
    """Requests for non-allowlisted domains must return 400."""
    headers = await _get_auth_headers(client, "dom@example.com")
    res = await client.post(
        "/api/v1/videos/metadata",
        json={"url": "https://evil.com/video.mp4"},
        headers=headers,
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_metadata_returns_fixture_data(client: AsyncClient):
    """
    Valid YouTube URL with MockProvider active should return metadata
    including media_id, title, duration, and at least one format option.
    """
    headers = await _get_auth_headers(client, "meta@example.com")
    res = await client.post(
        "/api/v1/videos/metadata",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert "media_id" in data
    assert data["title"]
    assert data["provider"] == "youtube.com"
    assert isinstance(data["available_formats"], list)
    assert len(data["available_formats"]) >= 1

    # Verify format structure
    fmt = data["available_formats"][0]
    assert "format" in fmt
    assert "resolution" in fmt


@pytest.mark.asyncio
async def test_metadata_720p_fixture(client: AsyncClient):
    """test_720p fixture URL returns formats including 720p mp4."""
    headers = await _get_auth_headers(client, "hd@example.com")
    res = await client.post(
        "/api/v1/videos/metadata",
        json={"url": "https://www.youtube.com/watch?v=test_720p"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["duration"] == 300

    formats = {(f["format"], f["resolution"]) for f in data["available_formats"]}
    assert ("mp4", "720p") in formats
    assert ("mp3", "audio_only") in formats


@pytest.mark.asyncio
async def test_metadata_caching(client: AsyncClient):
    """Fetching the same URL twice should return the same media_id (cached)."""
    headers = await _get_auth_headers(client, "cache@example.com")
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    res1 = await client.post("/api/v1/videos/metadata", json={"url": url}, headers=headers)
    res2 = await client.post("/api/v1/videos/metadata", json={"url": url}, headers=headers)

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["media_id"] == res2.json()["media_id"]


@pytest.mark.asyncio
async def test_metadata_rejects_malformed_url(client: AsyncClient):
    """Malformed URL strings should return 400."""
    headers = await _get_auth_headers(client, "bad@example.com")
    res = await client.post(
        "/api/v1/videos/metadata",
        json={"url": "not-a-real-url"},
        headers=headers,
    )
    assert res.status_code == 400
