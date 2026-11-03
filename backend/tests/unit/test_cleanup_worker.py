"""Unit tests for cleanup worker and periodic expiration housekeeping."""
from datetime import datetime, timedelta, timezone
import os
import time
from unittest.mock import MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.download import Download
from app.models.media import Media
from app.models.user import User
from app.workers.cleanup_worker import (
    _run_expire_stale_downloads,
    expire_stale_downloads,
    purge_orphan_temp_files,
)
from tests.conftest import test_session_factory as _session_factory


@pytest.mark.asyncio
async def test_expire_stale_downloads(monkeypatch, db_session: AsyncSession):
    """Test that expired downloads are purged from storage and marked expired in DB."""
    # Monkeypatch async_session_factory in cleanup_worker to use test DB
    monkeypatch.setattr(
        "app.workers.cleanup_worker.async_session_factory",
        _session_factory,
    )

    mock_delete = MagicMock(return_value=True)
    monkeypatch.setattr("app.workers.cleanup_worker.storage_service.delete_file", mock_delete)
    monkeypatch.setattr("app.workers.cleanup_worker._publish_redis_progress", MagicMock())

    now = datetime.now(timezone.utc)

    # 1. Seed user & media
    user = User(email="cleanup_test@example.com", password_hash="dummy")
    db_session.add(user)
    await db_session.flush()

    media = Media(
        source_url="https://youtube.com/watch?v=cleanup1",
        title="Cleanup Media",
        duration=120,
        provider="youtube",
    )
    db_session.add(media)
    await db_session.flush()

    # 2. Add an expired completed download
    expired_job = Download(
        user_id=user.id,
        media_id=media.id,
        status="completed",
        format="mp4",
        resolution="720p",
        progress=100,
        file_key="downloads/u1/2026/11/expired_job.mp4",
        expires_at=now - timedelta(hours=2),
    )
    db_session.add(expired_job)

    # 3. Add an active completed download (not expired)
    active_job = Download(
        user_id=user.id,
        media_id=media.id,
        status="completed",
        format="mp4",
        resolution="720p",
        progress=100,
        file_key="downloads/u1/2026/11/active_job.mp4",
        expires_at=now + timedelta(hours=22),
    )
    db_session.add(active_job)

    # 4. Add a processing download
    processing_job = Download(
        user_id=user.id,
        media_id=media.id,
        status="processing",
        format="mp4",
        resolution="720p",
        progress=50,
        file_key=None,
        expires_at=None,
    )
    db_session.add(processing_job)

    await db_session.commit()

    # Run expiration pipeline
    res = await _run_expire_stale_downloads()

    assert res["status"] == "completed"
    assert res["expired"] == 1
    assert "downloads/u1/2026/11/expired_job.mp4" in res["purged_keys"]
    mock_delete.assert_called_once_with("downloads/u1/2026/11/expired_job.mp4")

    # Refresh objects from DB to verify states
    await db_session.refresh(expired_job)
    await db_session.refresh(active_job)
    await db_session.refresh(processing_job)

    assert expired_job.status == "expired"
    assert expired_job.file_key is None

    assert active_job.status == "completed"
    assert active_job.file_key == "downloads/u1/2026/11/active_job.mp4"

    assert processing_job.status == "processing"


def test_purge_orphan_temp_files(tmp_path, monkeypatch):
    """Test scanning and purging of stale scratch folders older than max age."""
    monkeypatch.setattr(settings, "WORKER_SCRATCH_DIR", str(tmp_path))
    async def mock_active_ids():
        return set()

    monkeypatch.setattr("app.workers.cleanup_worker._get_active_job_ids", mock_active_ids)

    # Create a fresh directory (should not be purged if age < 2 hrs)
    fresh_dir = tmp_path / "job_fresh"
    fresh_dir.mkdir()

    # Create a stale directory (> 2 hours old)
    stale_dir = tmp_path / "job_stale"
    stale_dir.mkdir()
    old_time = time.time() - (4 * 3600)
    os.utime(str(stale_dir), (old_time, old_time))

    res = purge_orphan_temp_files.apply(kwargs={"max_age_hours": 2}).result

    assert res["status"] == "completed"
    assert not stale_dir.exists()
    assert fresh_dir.exists()
