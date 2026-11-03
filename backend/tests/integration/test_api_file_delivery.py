"""Integration tests for secure file delivery and presigned download URL generation."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.download import Download
from app.models.history import DownloadHistory
from app.models.media import Media
from app.models.user import User
from app.services.storage_service import storage_service


async def _get_auth_headers(client: AsyncClient, email: str = "file_user@example.com") -> dict:
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
async def test_file_delivery_unauthorized(client: AsyncClient):
    """Accessing /file endpoint without auth must return 401."""
    res = await client.get("/api/v1/downloads/dummy-id/file")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_file_delivery_lifecycle(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    """
    Test complete file delivery flow:
      1. Create job & simulate completed state.
      2. Verify presigned URL returned with sanitized filename.
      3. Verify audit record created in DownloadHistory.
      4. Verify ?redirect=true triggers 307.
    """
    # Mock storage service generate_presigned_url
    fake_signed_url = "https://minio.local/media-downloads/sample_asset.mp4?signature=test-sig-123"
    monkeypatch.setattr(
        storage_service,
        "generate_presigned_url",
        MagicMock(return_value=fake_signed_url),
    )

    headers = await _get_auth_headers(client, "delivery_owner@example.com")

    # 1. Fetch user from DB
    res_user = await db_session.execute(select(User).where(User.email == "delivery_owner@example.com"))
    user = res_user.scalars().first()

    # 2. Create media and completed download
    media = Media(
        source_url="https://youtube.com/watch?v=sample1",
        title='Sample "Awesome" Video / Clip: 2026',
        duration=180,
        provider="youtube",
    )
    db_session.add(media)
    await db_session.flush()

    download = Download(
        user_id=user.id,
        media_id=media.id,
        status="completed",
        format="mp4",
        resolution="720p",
        progress=100,
        file_key=f"downloads/{user.id}/2026/11/job123.mp4",
        file_size=1048576,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(download)
    await db_session.commit()

    # 3. GET /downloads/{id}/file
    file_res = await client.get(
        f"/api/v1/downloads/{download.id}/file",
        headers=headers,
    )
    assert file_res.status_code == 200
    data = file_res.json()
    assert data["download_url"] == fake_signed_url
    assert data["expires_in_seconds"] == 900
    assert data["file_size"] == 1048576
    assert data["content_type"] == "video/mp4"
    # Filename should have forbidden characters removed
    assert data["filename"] == "Sample Awesome Video  Clip 2026.mp4"

    # 4. Verify audit entry in DownloadHistory
    hist_res = await db_session.execute(
        select(DownloadHistory).where(
            DownloadHistory.user_id == user.id,
            DownloadHistory.download_id == download.id,
        )
    )
    history_entry = hist_res.scalars().first()
    assert history_entry is not None
    assert history_entry.ip_hash is not None

    # 5. Test redirect mode: ?redirect=true
    redir_res = await client.get(
        f"/api/v1/downloads/{download.id}/file?redirect=true",
        headers=headers,
        follow_redirects=False,
    )
    assert redir_res.status_code == 307
    assert redir_res.headers["location"] == fake_signed_url


@pytest.mark.asyncio
async def test_file_delivery_not_ready_conflict(client: AsyncClient, db_session: AsyncSession):
    """Requesting file for a queued or processing download must return 409 Conflict."""
    headers = await _get_auth_headers(client, "pending_user@example.com")
    res_user = await db_session.execute(select(User).where(User.email == "pending_user@example.com"))
    user = res_user.scalars().first()

    media = Media(source_url="https://youtube.com/watch?v=sample2", title="Test", provider="youtube")
    db_session.add(media)
    await db_session.flush()

    pending_download = Download(
        user_id=user.id,
        media_id=media.id,
        status="processing",
        format="mp4",
        resolution="720p",
        progress=45,
    )
    db_session.add(pending_download)
    await db_session.commit()

    res = await client.get(f"/api/v1/downloads/{pending_download.id}/file", headers=headers)
    assert res.status_code == 409
    err_msg = res.json().get("error") or res.json().get("detail", "")
    assert "not ready" in err_msg.lower()


@pytest.mark.asyncio
async def test_file_delivery_expired(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    """Requesting an expired file must return 410 Gone and mark DB record as expired."""
    mock_del = MagicMock(return_value=True)
    monkeypatch.setattr(storage_service, "delete_file", mock_del)

    headers = await _get_auth_headers(client, "expired_user@example.com")
    res_user = await db_session.execute(select(User).where(User.email == "expired_user@example.com"))
    user = res_user.scalars().first()

    media = Media(source_url="https://youtube.com/watch?v=sample3", title="Test Expired", provider="youtube")
    db_session.add(media)
    await db_session.flush()

    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    expired_download = Download(
        user_id=user.id,
        media_id=media.id,
        status="completed",
        format="mp4",
        resolution="720p",
        progress=100,
        file_key="downloads/u/2026/11/old.mp4",
        expires_at=past_time,
    )
    db_session.add(expired_download)
    await db_session.commit()

    res = await client.get(f"/api/v1/downloads/{expired_download.id}/file", headers=headers)
    assert res.status_code == 410
    err_msg = res.json().get("error") or res.json().get("detail", "")
    assert "expired" in err_msg.lower()

    # Verify updated in DB
    await db_session.refresh(expired_download)
    assert expired_download.status == "expired"
    assert expired_download.file_key is None
    mock_del.assert_called_once_with("downloads/u/2026/11/old.mp4")


@pytest.mark.asyncio
async def test_file_delivery_cross_user_isolation(client: AsyncClient, db_session: AsyncSession):
    """User B cannot access User A's download file."""
    headers_a = await _get_auth_headers(client, "user_a@example.com")
    headers_b = await _get_auth_headers(client, "user_b@example.com")

    res_user_a = await db_session.execute(select(User).where(User.email == "user_a@example.com"))
    user_a = res_user_a.scalars().first()

    media = Media(source_url="https://youtube.com/watch?v=sample4", title="Isolation Media", provider="youtube")
    db_session.add(media)
    await db_session.flush()

    download_a = Download(
        user_id=user_a.id,
        media_id=media.id,
        status="completed",
        format="mp4",
        resolution="720p",
        progress=100,
        file_key="downloads/user_a/test.mp4",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=10),
    )
    db_session.add(download_a)
    await db_session.commit()

    # User B attempts to access User A's file
    res = await client.get(f"/api/v1/downloads/{download_a.id}/file", headers=headers_b)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_serve_local_fallback_file(client: AsyncClient):
    """Local fallback endpoint serves existing file and 404s on missing or traversal."""
    import os

    # 1. Non-existent file
    res_404 = await client.get("/api/v1/downloads/files/non_existent.mp4")
    assert res_404.status_code == 404

    # 2. Path traversal attack
    res_traversal = await client.get("/api/v1/downloads/files/../../etc/passwd")
    assert res_traversal.status_code == 404

    # 3. Create a dummy file in local fallback store
    dummy_rel_path = "test_serve/video.mp4"
    dummy_abs_path = os.path.join(storage_service.local_storage_dir, dummy_rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(dummy_abs_path), exist_ok=True)
    with open(dummy_abs_path, "wb") as f:
        f.write(b"local fallback content test")

    try:
        res_ok = await client.get(f"/api/v1/downloads/files/{dummy_rel_path}")
        assert res_ok.status_code == 200
        assert res_ok.content == b"local fallback content test"
    finally:
        if os.path.exists(dummy_abs_path):
            os.remove(dummy_abs_path)

