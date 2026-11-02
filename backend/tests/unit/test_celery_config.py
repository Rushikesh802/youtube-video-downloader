"""
Unit tests for the Celery application configuration.

These tests validate queue definitions, task routing, Beat schedule,
and reliability settings entirely in-process — no Redis connection needed.
"""
import pytest
from celery import Celery
from kombu import Queue

from app.workers.celery_app import (
    CELERY_BEAT_SCHEDULE,
    CELERY_QUEUES,
    CELERY_TASK_ROUTES,
    celery_app,
    create_celery_app,
)


# ─── Application instance ─────────────────────────────────────────────────────

def test_celery_app_is_celery_instance():
    assert isinstance(celery_app, Celery)


def test_celery_app_name():
    assert celery_app.main == "yt_downloader"


# ─── Queue definitions ────────────────────────────────────────────────────────

def test_three_queues_defined():
    assert len(CELERY_QUEUES) == 3


def test_queue_names():
    names = {q.name for q in CELERY_QUEUES}
    assert names == {"media-processing", "metadata-fetch", "housekeeping"}


def test_media_queue_has_priority():
    """media-processing queue must have x-max-priority argument for task ordering."""
    media_q = next(q for q in CELERY_QUEUES if q.name == "media-processing")
    assert media_q.queue_arguments.get("x-max-priority") == 10


# ─── Task routing ─────────────────────────────────────────────────────────────

def test_process_download_job_routed_to_media_queue():
    route = CELERY_TASK_ROUTES["app.workers.download_worker.process_download_job"]
    assert route["queue"] == "media-processing"


def test_refresh_metadata_routed_to_metadata_queue():
    route = CELERY_TASK_ROUTES["app.workers.download_worker.refresh_metadata"]
    assert route["queue"] == "metadata-fetch"


def test_expire_stale_downloads_routed_to_housekeeping():
    route = CELERY_TASK_ROUTES["app.workers.cleanup_worker.expire_stale_downloads"]
    assert route["queue"] == "housekeeping"


def test_purge_orphan_temp_files_routed_to_housekeeping():
    route = CELERY_TASK_ROUTES["app.workers.cleanup_worker.purge_orphan_temp_files"]
    assert route["queue"] == "housekeeping"


# ─── Beat schedule ────────────────────────────────────────────────────────────

def test_beat_schedule_has_two_entries():
    assert len(CELERY_BEAT_SCHEDULE) == 2


def test_expire_stale_downloads_in_beat_schedule():
    assert "expire-stale-downloads" in CELERY_BEAT_SCHEDULE
    entry = CELERY_BEAT_SCHEDULE["expire-stale-downloads"]
    assert entry["task"] == "app.workers.cleanup_worker.expire_stale_downloads"
    assert entry["options"]["queue"] == "housekeeping"


def test_purge_orphan_beat_schedule():
    assert "purge-orphan-temp-files" in CELERY_BEAT_SCHEDULE
    entry = CELERY_BEAT_SCHEDULE["purge-orphan-temp-files"]
    assert entry["task"] == "app.workers.cleanup_worker.purge_orphan_temp_files"


# ─── Reliability settings ─────────────────────────────────────────────────────

def test_task_acks_late_enabled():
    assert celery_app.conf.task_acks_late is True


def test_task_reject_on_worker_lost_enabled():
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_task_acks_on_failure_or_timeout_enabled():
    assert celery_app.conf.task_acks_on_failure_or_timeout is True


def test_worker_prefetch_multiplier_is_one():
    """Prefetch of 1 ensures a single slow job doesn't block other task slots."""
    assert celery_app.conf.worker_prefetch_multiplier == 1


# ─── Serialisation ────────────────────────────────────────────────────────────

def test_json_serialisation():
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content


# ─── Time limits ──────────────────────────────────────────────────────────────

def test_soft_time_limit():
    assert celery_app.conf.task_soft_time_limit == 1800  # 30 min


def test_hard_time_limit():
    assert celery_app.conf.task_time_limit == 2100  # 35 min


# ─── Task annotations ─────────────────────────────────────────────────────────

def test_download_task_annotation_max_retries():
    annotations = celery_app.conf.task_annotations
    task_ann = annotations.get("app.workers.download_worker.process_download_job", {})
    assert task_ann.get("max_retries") == 3


def test_download_task_annotation_rate_limit():
    annotations = celery_app.conf.task_annotations
    task_ann = annotations.get("app.workers.download_worker.process_download_job", {})
    assert task_ann.get("rate_limit") == "20/m"


# ─── Registered tasks ─────────────────────────────────────────────────────────
# celery_app.tasks is only populated after the worker modules are imported.
# Import them explicitly here to trigger @celery_app.task registration.
import app.workers.download_worker  # noqa: F401, E402
import app.workers.cleanup_worker   # noqa: F401, E402


def test_download_task_registered():
    assert "app.workers.download_worker.process_download_job" in celery_app.tasks


def test_refresh_metadata_task_registered():
    assert "app.workers.download_worker.refresh_metadata" in celery_app.tasks


def test_expire_stale_downloads_task_registered():
    assert "app.workers.cleanup_worker.expire_stale_downloads" in celery_app.tasks


def test_purge_orphan_temp_files_task_registered():
    assert "app.workers.cleanup_worker.purge_orphan_temp_files" in celery_app.tasks


# ─── create_celery_app factory ────────────────────────────────────────────────

def test_factory_returns_independent_instance():
    """create_celery_app() should always return a fresh Celery instance."""
    app1 = create_celery_app()
    app2 = create_celery_app()
    assert app1 is not app2
    assert isinstance(app1, Celery)
