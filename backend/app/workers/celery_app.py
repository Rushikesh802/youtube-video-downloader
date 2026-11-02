"""
Celery application factory and queue configuration.

Queue layout
────────────
  media-processing   Heavy work: stream retrieval, FFmpeg transcoding, S3 upload.
  metadata-fetch     Light work: external API calls for metadata refresh.
  housekeeping       Periodic work: expired-file deletion, temp-file cleanup.

Reliability settings
────────────────────
  task_acks_late                  Tasks acknowledged only after completion (not on pickup).
  task_reject_on_worker_lost      Un-acked tasks re-queued if worker dies mid-execution.
  task_acks_on_failure_or_timeout Prevents silent loss of failed tasks.

Retry / back-off defaults (overridable per task)
─────────────────────────────────────────────────
  max_retries     = 3
  default_retry_delay = 30 s   (exponential back-off applied per task)

Celery Beat — periodic tasks
─────────────────────────────
  expire-cleanup       Every 15 min: delete expired files from storage + DB.
  orphan-file-cleanup  Every 60 min: remove temporary scratch files from worker volumes.
"""

from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.config import settings

# ─── Named exchanges ──────────────────────────────────────────────────────────
_media_exchange = Exchange("media-processing", type="direct", durable=True)
_meta_exchange = Exchange("metadata-fetch", type="direct", durable=True)
_housekeeping_exchange = Exchange("housekeeping", type="direct", durable=True)

# ─── Named queues with explicit bindings ──────────────────────────────────────
CELERY_QUEUES: tuple[Queue, ...] = (
    Queue(
        "media-processing",
        exchange=_media_exchange,
        routing_key="media-processing",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "metadata-fetch",
        exchange=_meta_exchange,
        routing_key="metadata-fetch",
    ),
    Queue(
        "housekeeping",
        exchange=_housekeeping_exchange,
        routing_key="housekeeping",
    ),
)

# ─── Task → queue routing ─────────────────────────────────────────────────────
CELERY_TASK_ROUTES: dict[str, dict] = {
    "app.workers.download_worker.process_download_job": {
        "queue": "media-processing",
        "routing_key": "media-processing",
    },
    "app.workers.download_worker.refresh_metadata": {
        "queue": "metadata-fetch",
        "routing_key": "metadata-fetch",
    },
    "app.workers.cleanup_worker.expire_stale_downloads": {
        "queue": "housekeeping",
        "routing_key": "housekeeping",
    },
    "app.workers.cleanup_worker.purge_orphan_temp_files": {
        "queue": "housekeeping",
        "routing_key": "housekeeping",
    },
}

# ─── Celery Beat periodic schedule ───────────────────────────────────────────
CELERY_BEAT_SCHEDULE: dict[str, dict] = {
    "expire-stale-downloads": {
        "task": "app.workers.cleanup_worker.expire_stale_downloads",
        "schedule": timedelta(minutes=15),
        "options": {"queue": "housekeeping"},
    },
    "purge-orphan-temp-files": {
        "task": "app.workers.cleanup_worker.purge_orphan_temp_files",
        "schedule": timedelta(hours=1),
        "options": {"queue": "housekeeping"},
    },
}


def create_celery_app() -> Celery:
    """
    Construct and fully configure the Celery application.

    Centralising all configuration here (rather than using ``celery.conf.update``)
    makes it straightforward to unit-test the configuration in isolation.
    """
    app = Celery(
        "yt_downloader",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "app.workers.download_worker",
            "app.workers.cleanup_worker",
        ],
    )

    app.conf.update(
        # ── Serialisation ──────────────────────────────────────────────────
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # ── Timezone ───────────────────────────────────────────────────────
        timezone="UTC",
        enable_utc=True,
        # ── Reliability: late-ack + reject on worker loss ──────────────────
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_acks_on_failure_or_timeout=True,
        # ── Task result TTL (keep results for 24 h, then expire from Redis) ─
        result_expires=86400,
        # ── Per-worker concurrency defaults (overridden at startup via CLI) ─
        worker_concurrency=2,
        worker_prefetch_multiplier=1,   # fetch one task at a time per worker slot
        # ── Queue definitions ──────────────────────────────────────────────
        task_queues=CELERY_QUEUES,
        task_default_queue="media-processing",
        task_default_exchange="media-processing",
        task_default_routing_key="media-processing",
        task_routes=CELERY_TASK_ROUTES,
        # ── Global task soft/hard time limits ─────────────────────────────
        # Soft limit: task receives SoftTimeLimitExceeded for graceful cleanup
        # Hard limit: SIGKILL sent after this many seconds
        task_soft_time_limit=1800,   # 30 min
        task_time_limit=2100,        # 35 min (buffer beyond soft limit)
        # ── Celery Beat periodic tasks ─────────────────────────────────────
        beat_schedule=CELERY_BEAT_SCHEDULE,
        beat_scheduler="celery.beat:PersistentScheduler",
        # ── Dead-letter: max retries before task goes to dead-letter queue ──
        task_annotations={
            "app.workers.download_worker.process_download_job": {
                "max_retries": 3,
                "default_retry_delay": 30,
                "rate_limit": "20/m",
            },
            "app.workers.download_worker.refresh_metadata": {
                "max_retries": 5,
                "default_retry_delay": 10,
                "rate_limit": "60/m",
            },
            "app.workers.cleanup_worker.expire_stale_downloads": {
                "max_retries": 3,
                "default_retry_delay": 60,
            },
            "app.workers.cleanup_worker.purge_orphan_temp_files": {
                "max_retries": 2,
                "default_retry_delay": 120,
            },
        },
    )

    return app


# ─── Singleton Celery app instance ───────────────────────────────────────────
# Import this wherever you need to dispatch tasks:
#   from app.workers.celery_app import celery_app
#   celery_app.send_task("app.workers.download_worker.process_download_job", args=[job_id])
celery_app: Celery = create_celery_app()
