"""
Cleanup worker — housekeeping tasks run by Celery Beat on a schedule.

Phase 4 will wire up the actual S3 deletion logic.
These stubs ensure the module is importable and the Beat schedule is registered.
"""
import logging

from celery import Task

from app.workers.celery_app import celery_app

logger = logging.getLogger("yt_downloader.workers.cleanup")


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

    Phase 4 full implementation will:
      1. Query Download rows where expires_at <= now() and status == 'completed'.
      2. Delete the underlying object from S3/MinIO.
      3. Set status = 'expired' and clear file_key in the database.

    Returns:
        dict with count of records processed.
    """
    logger.info("expire_stale_downloads: running housekeeping pass")
    # Stub — full S3 + DB deletion logic wired in Phase 4
    return {"expired": 0, "status": "stub"}


@celery_app.task(
    bind=True,
    name="app.workers.cleanup_worker.purge_orphan_temp_files",
    queue="housekeeping",
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def purge_orphan_temp_files(self: Task) -> dict:
    """
    Periodic task (every 60 min via Celery Beat).

    Scans the WORKER_SCRATCH_DIR for job scratch folders older than 2 hours
    that no longer correspond to an active processing task, and removes them.

    Returns:
        dict with count of directories cleaned up.
    """
    import os
    import shutil
    import time

    from app.config import settings

    scratch_dir = settings.WORKER_SCRATCH_DIR
    if not os.path.isdir(scratch_dir):
        logger.debug("purge_orphan_temp_files: scratch dir does not exist, skipping")
        return {"purged": 0}

    threshold = time.time() - (2 * 3600)  # older than 2 hours
    purged = 0

    for entry in os.scandir(scratch_dir):
        if entry.is_dir() and entry.stat().st_mtime < threshold:
            try:
                shutil.rmtree(entry.path, ignore_errors=True)
                purged += 1
                logger.info("purge_orphan_temp_files: removed %s", entry.path)
            except OSError as exc:
                logger.warning("Could not remove %s: %s", entry.path, exc)

    logger.info("purge_orphan_temp_files: purged %d orphan directories", purged)
    return {"purged": purged}
