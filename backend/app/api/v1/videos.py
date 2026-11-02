from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.video import VideoMetadataRequest, VideoMetadataResponse, VideoRead
from app.services.metadata_service import fetch_video_metadata

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post(
    "/metadata",
    response_model=VideoMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a media URL and retrieve available metadata and formats",
)
async def get_video_metadata(
    request: VideoMetadataRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> VideoMetadataResponse:
    """
    Accepts an authorized media URL, validates it against the provider allowlist,
    applies SSRF protection, fetches metadata via the authorized provider,
    and returns the title, thumbnail, duration, and permitted format options.

    The backend independently validates the URL and provider. No download
    authorization is implied solely by URL format — provider authorization
    must be established separately.
    """
    return await fetch_video_metadata(url=request.url, session=session)
