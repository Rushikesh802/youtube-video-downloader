"""
Cleanup worker — housekeeping tasks run by Celery Beat on a schedule.

Handles:
  - Periodic purging of expired download media assets from object storage (S3/MinIO) and DB state update
  - Purging orphaned temporary worker scratch directories
"""
import asyncio
from datetime import datetime, timezone
import logging
import os
import shutil
import time
from typing import List, Set

from celery import Task
from sqlalchemy import select

from app.config import settings
from app.db.session import async_session_factory
from app.models.download import Download
from app.services.storage_service import storage_service
from app.workers.celery_app import celery_app
from app.workers.download_worker import _publish_redis_progress

logger = logging.getLogger("yt_downloader.workers.cleanup")


async def _run_expire_stale_downloads() -> dict:
    """
    Asynchronous pipeline to identify and expire completed downloads that passed their expiration date:
      1. Query Download rows where expires_at <= now() and status == 'completed'.
      2. Delete underlying storage files from S3/MinIO and local fallback.
      3. Set status = 'expired' and clear file_key in database.
      4. Publish expiration event to Redis for any connected listeners.
    """
    now = datetime.now(timezone.utc)
    expired_count = 0
    purged_keys: List[str] = []

    async with async_session_factory() as session:
        # Fetch completed downloads where expiration time has elapsed
        result = await session.execute(
            select(Download).where(
                Download.status == "completed",
                Download.expires_at <= now,
            )
        )
        downloads = result.scalars().all()

        for download in downloads:
            file_key = download.file_key
            if file_key:
                try:
                    storage_service.delete_file(file_key)
                    purged_keys.append(file_key)
                    logger.info("Purged expired storage file: %s for job %s", file_key, download.id)
                except Exception as exc:
                    logger.warning("Could not delete storage file %s for job %s: %s", file_key, download.id, exc)

            download.status = "expired"
            download.file_key = None
            expired_count += 1

            _publish_redis_progress(
                download_id=download.id,
                progress=download.progress,
                status="expired",
                error=None,
            )

        if expired_count > 0:
            await session.commit()
            logger.info("Expired %d stale download records successfully", expired_count)

    return {
        "expired": expired_count,
        "purged_keys": purged_keys,
        "status": "completed",
    }


async def _get_active_job_ids() -> Set[str]:
    """Retrieve set of currently active download job IDs to protect in-flight scratch dirs."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Download.id).where(
                    Download.status.in_(["queued", "processing", "uploading"])
                )
            )
            return set(result.scalars().all())
    except Exception as exc:
        logger.warning("Could not fetch active job IDs for scratch purge: %s", exc)
        return set()


@celery_app.task(
    bind=True,
    name="app.workers.cleanup_worker.expire_stale_downloads",
    queue="housekeeping",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def expire_stale_downloads(self: Task) -> dict:
    """
    Periodic task (every 15 min via Celery Beat).
    Scans for expired media assets, purges them from S3/MinIO, and updates status in DB.
    """
    logger.info("expire_stale_downloads: starting housekeeping expiration pass")
    try:
        return asyncio.run(_run_expire_stale_downloads())
    except Exception as exc:
        logger.error("expire_stale_downloads task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.workers.cleanup_worker.purge_orphan_temp_files",
    queue="housekeeping",
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def purge_orphan_temp_files(self: Task, max_age_hours: int = 2) -> dict:
    """
    Periodic task (every 60 min via Celery Beat).
    Scans the WORKER_SCRATCH_DIR for job scratch folders older than max_age_hours
    that do not correspond to an active processing task, and removes them.
    """
    scratch_dir = settings.WORKER_SCRATCH_DIR
    if not os.path.isdir(scratch_dir):
        logger.debug("purge_orphan_temp_files: scratch dir %s does not exist, skipping", scratch_dir)
        return {"purged": 0, "status": "no_dir"}

    active_job_ids = asyncio.run(_get_active_job_ids())
    threshold = time.time() - (max_age_hours * 3600)
    purged = 0

    try:
        for entry in os.scandir(scratch_dir):
            if not entry.is_dir():
                continue

            # If folder name is an active job and not exceedingly old, skip
            is_active = entry.name in active_job_ids
            is_stale = entry.stat().st_mtime < threshold

            # Purge if scratch folder is older than max_age_hours and not an active job
            if is_stale and not is_active:
                try:
                    shutil.rmtree(entry.path, ignore_errors=True)
                    purged += 1
                    logger.info("purge_orphan_temp_files: removed scratch dir %s", entry.path)
                except OSError as exc:
                    logger.warning("Could not remove %s: %s", entry.path, exc)
    except Exception as exc:
        logger.error("Error during scratch folder scanning: %s", exc)

    logger.info("purge_orphan_temp_files: purged %d orphan directories", purged)
    return {"purged": purged, "status": "completed"}
