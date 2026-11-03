"""
Download history and audit trail API endpoints.

Handles:
  - GET /api/v1/history: Paginated list of current user's download events
  - GET /api/v1/history/{history_id}: Retrieve single history event details
  - DELETE /api/v1/history/{history_id}: Remove an entry from user's history log
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, get_history_repository
from app.core.exceptions import NotFoundException
from app.models.history import DownloadHistory
from app.models.user import User
from app.repositories.history_repository import HistoryRepository
from app.schemas.common import MessageResponse
from app.schemas.history import DownloadHistoryItem, DownloadHistoryListResponse

logger = logging.getLogger("yt_downloader.api.history")

router = APIRouter(prefix="/history", tags=["History"])


def _to_history_item(entry: DownloadHistory) -> DownloadHistoryItem:
    """Helper to convert DownloadHistory ORM model with joined relationships to response schema."""
    format_val = None
    resolution_val = None
    file_size_val = None
    title_val = None
    thumbnail_val = None
    source_val = None

    if entry.download:
        format_val = entry.download.format
        resolution_val = entry.download.resolution
        file_size_val = entry.download.file_size
        if entry.download.media:
            title_val = entry.download.media.title
            thumbnail_val = entry.download.media.thumbnail_url
            source_val = entry.download.media.source_url

    return DownloadHistoryItem(
        id=entry.id,
        download_id=entry.download_id,
        downloaded_at=entry.downloaded_at,
        ip_hash=entry.ip_hash,
        format=format_val,
        resolution=resolution_val,
        file_size=file_size_val,
        title=title_val,
        thumbnail_url=thumbnail_val,
        source_url=source_val,
    )


@router.get(
    "",
    response_model=DownloadHistoryListResponse,
    summary="List download access history for the authenticated user",
)
async def list_user_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    history_repo: HistoryRepository = Depends(get_history_repository),
) -> DownloadHistoryListResponse:
    """Retrieve paginated download history and audit logs for the current user."""
    items, total = await history_repo.list_for_user(current_user.id, skip=skip, limit=limit)
    return DownloadHistoryListResponse(
        items=[_to_history_item(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{history_id}",
    response_model=DownloadHistoryItem,
    summary="Retrieve details of a single download history event",
)
async def get_history_detail(
    history_id: str,
    current_user: User = Depends(get_current_active_user),
    history_repo: HistoryRepository = Depends(get_history_repository),
) -> DownloadHistoryItem:
    """Get audit details for a specific download history record."""
    entry = await history_repo.get_by_id_for_user(history_id, current_user.id)
    if not entry:
        raise NotFoundException("History record not found or access denied.")
    return _to_history_item(entry)


@router.delete(
    "/{history_id}",
    response_model=MessageResponse,
    summary="Delete an entry from the user's download history",
)
async def delete_history_entry(
    history_id: str,
    current_user: User = Depends(get_current_active_user),
    history_repo: HistoryRepository = Depends(get_history_repository),
) -> MessageResponse:
    """Delete a specific history entry."""
    entry = await history_repo.get_by_id_for_user(history_id, current_user.id)
    if not entry:
        raise NotFoundException("History record not found or access denied.")

    await history_repo.delete(entry)
    return MessageResponse(message="History record deleted successfully.")
