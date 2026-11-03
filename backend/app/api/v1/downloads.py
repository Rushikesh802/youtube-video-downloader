"""
Download jobs API endpoints.

Handles:
  - POST /api/v1/downloads: Queue a new download/transcode job (202 Accepted)
  - GET /api/v1/downloads/{id}: Check current status and progress
  - GET /api/v1/downloads: List current user's download jobs
  - GET /api/v1/downloads/{id}/file: Generate short-lived presigned download URL
  - GET /api/v1/downloads/{id}/events: Server-Sent Events (SSE) live progress stream
  - DELETE /api/v1/downloads/{id}: Cancel job and purge resources
  - GET /api/v1/downloads/files/{file_path:path}: Local storage fallback file serving
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import re
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from app.api.deps import (
    get_current_active_user,
    get_download_repository,
    get_history_repository,
    get_media_repository,
)
from app.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ExpiredException,
    NotFoundException,
    QuotaExceededException,
)
from app.models.download import Download
from app.models.user import User
from app.repositories.download_repository import DownloadRepository
from app.repositories.history_repository import HistoryRepository
from app.repositories.media_repository import MediaRepository
from app.schemas.common import MessageResponse
from app.schemas.download import (
    DownloadCreateRequest,
    DownloadFileResponse,
    DownloadJobCreated,
    DownloadListResponse,
    DownloadRead,
)
from app.services.format_service import verify_format_for_media
from app.services.storage_service import storage_service
from app.workers.celery_app import celery_app

logger = logging.getLogger("yt_downloader.api.downloads")

router = APIRouter(prefix="/downloads", tags=["Downloads"])


@router.post(
    "",
    response_model=DownloadJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create and enqueue an asynchronous media download/transcode job",
)
async def create_download_job(
    request: DownloadCreateRequest,
    current_user: User = Depends(get_current_active_user),
    download_repo: DownloadRepository = Depends(get_download_repository),
    media_repo: MediaRepository = Depends(get_media_repository),
) -> DownloadJobCreated:
    """
    Validates requested format against media source, checks user concurrency quotas,
    persists a 'queued' Download record, dispatches a background Celery task,
    and returns a 202 Accepted response with the job_id.
    """
    # 1. Verify media exists
    media = await media_repo.get_by_id(request.media_id)
    if not media:
        raise NotFoundException("Media record not found. Please inspect URL first.")

    # 2. Verify requested format and quality are permitted
    await verify_format_for_media(media, request.format, request.resolution)

    # 3. Check concurrent active job quota
    active_count = await download_repo.get_user_active_count(current_user.id)
    if active_count >= settings.MAX_USER_CONCURRENT_JOBS:
        raise QuotaExceededException(
            f"Download quota exceeded: you have reached the maximum limit of {settings.MAX_USER_CONCURRENT_JOBS} concurrent active jobs."
        )

    # 4. Create database job record
    download = Download(
        user_id=current_user.id,
        media_id=media.id,
        format=request.format,
        resolution=request.resolution,
        status="queued",
        progress=0,
    )
    download = await download_repo.create(download)

    # 5. Dispatch task to Celery worker queue
    try:
        task = celery_app.send_task(
            "app.workers.download_worker.process_download_job",
            args=[download.id],
            queue="media-processing",
            retry=False,
        )
        download.celery_task_id = task.id
        await download_repo.update(download)
    except Exception as exc:
        logger.warning(
            "Could not dispatch task to Celery broker (%s). Job recorded as queued in DB.",
            exc,
        )

    return DownloadJobCreated(
        job_id=download.id,
        status=download.status,
        message="Processing request accepted and queued for worker execution.",
    )


@router.get(
    "/{download_id}",
    response_model=DownloadRead,
    summary="Retrieve the status and progress of a download job",
)
async def get_download_job(
    download_id: str,
    current_user: User = Depends(get_current_active_user),
    download_repo: DownloadRepository = Depends(get_download_repository),
) -> DownloadRead:
    """Fetch status, progress percentage, and details of a specific download job."""
    download = await download_repo.get_by_id_for_user(download_id, current_user.id)
    if not download:
        raise NotFoundException("Download job not found or access denied.")
    return DownloadRead.model_validate(download)


@router.get(
    "",
    response_model=DownloadListResponse,
    summary="List download jobs for the authenticated user",
)
async def list_download_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    download_repo: DownloadRepository = Depends(get_download_repository),
) -> DownloadListResponse:
    """Retrieve a paginated history of jobs submitted by the current user."""
    items, total = await download_repo.list_for_user(current_user.id, skip=skip, limit=limit)
    return DownloadListResponse(
        items=[DownloadRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/{download_id}",
    response_model=MessageResponse,
    summary="Cancel an active download job or delete a completed record",
)
async def delete_download_job(
    download_id: str,
    current_user: User = Depends(get_current_active_user),
    download_repo: DownloadRepository = Depends(get_download_repository),
) -> MessageResponse:
    """Cancel and delete a user's download job."""
    download = await download_repo.get_by_id_for_user(download_id, current_user.id)
    if not download:
        raise NotFoundException("Download job not found or access denied.")

    # If celery task is still active, attempt revocation
    if download.celery_task_id and download.status in ("queued", "processing", "uploading"):
        try:
            celery_app.control.revoke(download.celery_task_id, terminate=True)
        except Exception as exc:
            logger.debug("Failed to revoke Celery task %s: %s", download.celery_task_id, exc)

    # If file was stored, delete from storage
    if download.file_key:
        storage_service.delete_file(download.file_key)

    await download_repo.delete(download)
    return MessageResponse(message="Download job and associated resources deleted successfully.")


@router.get(
    "/{download_id}/file",
    summary="Generate a short-lived presigned download URL for a completed media asset",
    responses={
        200: {"model": DownloadFileResponse},
        307: {"description": "Redirect directly to signed URL"},
        400: {"description": "Job failed or invalid state"},
        404: {"description": "Download job not found"},
        409: {"description": "Media file is still processing"},
        410: {"description": "Download file has expired"},
    },
)
async def get_download_file(
    download_id: str,
    request: Request,
    redirect: bool = Query(False, description="Redirect browser directly to presigned URL"),
    current_user: User = Depends(get_current_active_user),
    download_repo: DownloadRepository = Depends(get_download_repository),
    media_repo: MediaRepository = Depends(get_media_repository),
    history_repo: HistoryRepository = Depends(get_history_repository),
):
    """
    Validates job completion and expiration, generates a 15-minute presigned GET URL
    with Content-Disposition attachment header, records a DownloadHistory audit event,
    and returns the signed URL or redirects directly.
    """
    # 1. Fetch download owned by current user
    download = await download_repo.get_by_id_for_user(download_id, current_user.id)
    if not download:
        raise NotFoundException("Download job not found or access denied.")

    # 2. Check status state
    if download.status == "expired":
        raise ExpiredException("This download link has expired and is no longer available.")
    if download.status in ("queued", "processing", "uploading"):
        raise ConflictException(f"Media file is not ready yet. Current status: {download.status}")
    if download.status in ("failed", "cancelled"):
        raise BadRequestException(f"Download job {download.status}: {download.error_message or 'No output file available.'}")
    if download.status != "completed":
        raise BadRequestException(f"Download job is in unexpected state: {download.status}")

    # 3. Check expiration timestamp
    now = datetime.now(timezone.utc)
    if download.expires_at:
        # Standardize timezone for comparison
        expires_at_utc = download.expires_at if download.expires_at.tzinfo else download.expires_at.replace(tzinfo=timezone.utc)
        if expires_at_utc <= now:
            # Mark expired in DB and delete file
            download.status = "expired"
            if download.file_key:
                storage_service.delete_file(download.file_key)
                download.file_key = None
            await download_repo.update(download)
            raise ExpiredException("This download link has expired and is no longer available.")

    # 4. Verify storage key presence
    if not download.file_key:
        raise NotFoundException("Media storage key is missing for this download.")

    # 5. Build human-readable sanitized filename
    media = await media_repo.get_by_id(download.media_id)
    title_raw = media.title if (media and media.title) else "media_download"
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title_raw).strip() or "media_download"
    filename = f"{safe_title}.{download.format}"

    content_types = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mp3": "audio/mpeg",
    }
    content_type = content_types.get(download.format, "application/octet-stream")

    # 6. Generate presigned URL
    download_url = storage_service.generate_presigned_url(
        object_key=download.file_key,
        expiration=settings.S3_PRESIGNED_EXPIRATION_SECONDS,
        filename=filename,
        content_type=content_type,
    )

    # 7. Record privacy-conscious audit entry in DownloadHistory
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client and request.client.host:
        client_ip = request.client.host
    else:
        client_ip = "127.0.0.1"

    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()

    await history_repo.create_entry(
        user_id=current_user.id,
        download_id=download.id,
        ip_hash=ip_hash,
        downloaded_at=now,
    )

    if redirect:
        return RedirectResponse(url=download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    return DownloadFileResponse(
        download_url=download_url,
        expires_in_seconds=settings.S3_PRESIGNED_EXPIRATION_SECONDS,
        filename=filename,
        file_size=download.file_size,
        content_type=content_type,
    )


@router.get(
    "/files/{file_path:path}",
    summary="Local fallback media file server for development and offline testing",
)
async def serve_local_fallback_file(file_path: str):
    """Serves file from local storage fallback when S3 is running in offline mode."""
    local_path = storage_service.get_local_file_path(file_path)
    if not local_path:
        raise NotFoundException("Requested file not found in local store.")
    return FileResponse(
        path=local_path,
        filename=os.path.basename(local_path),
    )


@router.get(
    "/{download_id}/events",
    summary="Server-Sent Events (SSE) live progress stream for a download job",
)
async def stream_download_events(
    download_id: str,
    current_user: User = Depends(get_current_active_user),
    download_repo: DownloadRepository = Depends(get_download_repository),
) -> StreamingResponse:
    """Stream Server-Sent Events with progress updates until completion or termination."""
    download = await download_repo.get_by_id_for_user(download_id, current_user.id)
    if not download:
        raise NotFoundException("Download job not found or access denied.")

    async def event_generator() -> AsyncGenerator[str, None]:
        last_progress = -1
        last_status = ""

        # Poll database state and yield SSE messages
        for _ in range(120):  # Stream for up to ~2 minutes
            current = await download_repo.get_by_id_for_user(download_id, current_user.id)
            if not current:
                yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            if current.progress != last_progress or current.status != last_status:
                last_progress = current.progress
                last_status = current.status

                payload = json.dumps({
                    "job_id": current.id,
                    "status": current.status,
                    "progress": current.progress,
                    "file_size": current.file_size,
                    "error": current.error_message,
                })
                yield f"event: progress\ndata: {payload}\n\n"

            if current.status in ("completed", "failed", "cancelled", "expired"):
                break

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
