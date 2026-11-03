"""Integration tests for the Download History audit API."""
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.download import Download
from app.models.history import DownloadHistory
from app.models.media import Media
from app.models.user import User


async def _get_auth_headers(client: AsyncClient, email: str = "history_user@example.com") -> dict:
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
async def test_history_unauthorized(client: AsyncClient):
    """GET /history without authorization token returns 401."""
    res = await client.get("/api/v1/history")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_history_crud_and_isolation(client: AsyncClient, db_session: AsyncSession):
    """Test history listing, details, deletion, and cross-user isolation."""
    headers_alice = await _get_auth_headers(client, "alice@example.com")
    headers_bob = await _get_auth_headers(client, "bob@example.com")

    # Get Alice & Bob user models
    res_a = await db_session.execute(select(User).where(User.email == "alice@example.com"))
    alice = res_a.scalars().first()

    res_b = await db_session.execute(select(User).where(User.email == "bob@example.com"))
    bob = res_b.scalars().first()

    # Create Media
    media = Media(
        source_url="https://youtube.com/watch?v=hist1",
        title="Audited Video Title",
        thumbnail_url="https://img.youtube.com/vi/hist1/default.jpg",
        duration=300,
        provider="youtube",
    )
    db_session.add(media)
    await db_session.flush()

    # Create Download for Alice
    download_alice = Download(
        user_id=alice.id,
        media_id=media.id,
        status="completed",
        format="mp4",
        resolution="1080p",
        progress=100,
        file_size=2097152,
    )
    db_session.add(download_alice)
    await db_session.flush()

    # Create Download History for Alice
    now = datetime.now(timezone.utc)
    hist_alice = DownloadHistory(
        user_id=alice.id,
        download_id=download_alice.id,
        downloaded_at=now,
        ip_hash="fake-sha256-hash",
    )
    db_session.add(hist_alice)
    await db_session.commit()

    # 1. Alice lists history
    res = await client.get("/api/v1/history", headers=headers_alice)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["id"] == hist_alice.id
    assert item["download_id"] == download_alice.id
    assert item["title"] == "Audited Video Title"
    assert item["format"] == "mp4"
    assert item["resolution"] == "1080p"
    assert item["file_size"] == 2097152
    assert item["ip_hash"] == "fake-sha256-hash"

    # 2. Bob lists history -> must be empty
    bob_res = await client.get("/api/v1/history", headers=headers_bob)
    assert bob_res.status_code == 200
    assert bob_res.json()["total"] == 0

    # 3. Bob attempts to access Alice's history item -> 404
    bob_get = await client.get(f"/api/v1/history/{hist_alice.id}", headers=headers_bob)
    assert bob_get.status_code == 404

    # 4. Alice gets single history detail
    alice_get = await client.get(f"/api/v1/history/{hist_alice.id}", headers=headers_alice)
    assert alice_get.status_code == 200
    assert alice_get.json()["id"] == hist_alice.id

    # 5. Alice deletes history entry
    del_res = await client.delete(f"/api/v1/history/{hist_alice.id}", headers=headers_alice)
    assert del_res.status_code == 200

    # 6. Verify item is deleted
    alice_check = await client.get(f"/api/v1/history/{hist_alice.id}", headers=headers_alice)
    assert alice_check.status_code == 404
