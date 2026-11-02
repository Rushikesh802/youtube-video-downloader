"""
Metadata service.

Orchestrates URL validation, provider dispatch, and Media record persistence.
Results are cached: if a Media row already exists for the same normalized URL,
the cached record is returned and the provider is not called again.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestException
from app.models.media import Media
from app.schemas.video import FormatOption, VideoMetadataResponse
from app.services.providers.base import BaseMediaProvider, ProviderError, ProviderMetadata
from app.services.providers.mock_provider import MockProvider
from app.services.providers.youtube_provider import YouTubeProvider
from app.services.url_validator import validate_url

logger = logging.getLogger("yt_downloader.metadata")

# ─── Provider registry ────────────────────────────────────────────────────────
# In development/test, MockProvider is active. In production, swap in YouTubeProvider.
_PROVIDER_REGISTRY: list[BaseMediaProvider] = [
    MockProvider(),
]

# Uncomment when YOUTUBE_DATA_API_KEY is configured:
# _PROVIDER_REGISTRY.append(YouTubeProvider(api_key=os.getenv("YOUTUBE_DATA_API_KEY")))


def _get_provider(provider_domain: str) -> BaseMediaProvider:
    for p in _PROVIDER_REGISTRY:
        if p.supports(provider_domain):
            return p
    raise BadRequestException(
        f"No authorized provider is registered for domain '{provider_domain}'."
    )


async def _find_cached_media(session: AsyncSession, url: str) -> Optional[Media]:
    result = await session.execute(select(Media).where(Media.source_url == url))
    return result.scalars().first()


async def _persist_media(session: AsyncSession, meta: ProviderMetadata) -> Media:
    media = Media(
        source_url=meta.source_url,
        title=meta.title,
        thumbnail_url=meta.thumbnail_url,
        duration=meta.duration,
        provider=meta.provider,
        uploader=meta.uploader,
        description=meta.description,
    )
    session.add(media)
    await session.flush()
    await session.refresh(media)
    return media


def _build_response(media: Media, formats: list[FormatOption]) -> VideoMetadataResponse:
    return VideoMetadataResponse(
        media_id=media.id,
        title=media.title,
        thumbnail=media.thumbnail_url,
        duration=media.duration,
        provider=media.provider,
        uploader=media.uploader,
        description=media.description,
        available_formats=formats,
    )


async def fetch_video_metadata(
    url: str,
    session: AsyncSession,
) -> VideoMetadataResponse:
    """
    Validate *url*, fetch provider metadata, persist or retrieve Media record,
    and return a metadata response including permitted format options.
    """
    # 1. SSRF-safe URL validation + provider identification
    try:
        provider_domain = validate_url(url)
    except Exception as exc:
        raise exc  # Re-raise SSRFException or similar

    # 2. Check if we already have a cached Media entry
    cached = await _find_cached_media(session, url)
    if cached:
        logger.debug("Returning cached media record id=%s for url=%s", cached.id, url)
        # Fetch formats again from provider to ensure they reflect current availability
        provider = _get_provider(provider_domain)
        try:
            meta = await provider.fetch_metadata(url)
        except ProviderError as e:
            logger.warning("Provider refresh failed, serving cached metadata: %s", e)
            formats: list[FormatOption] = []
            return _build_response(cached, formats)

        formats = [
            FormatOption(
                format=f.format,
                resolution=f.resolution,
                filesize_approx=f.filesize_approx,
                note=f.note,
            )
            for f in meta.formats
        ]
        return _build_response(cached, formats)

    # 3. Dispatch to the appropriate provider
    provider = _get_provider(provider_domain)
    try:
        meta = await provider.fetch_metadata(url)
    except ProviderError as e:
        raise BadRequestException(f"Could not retrieve media metadata: {e}") from e

    # 4. Persist the new Media record
    media = await _persist_media(session, meta)

    formats = [
        FormatOption(
            format=f.format,
            resolution=f.resolution,
            filesize_approx=f.filesize_approx,
            note=f.note,
        )
        for f in meta.formats
    ]

    logger.info("New media record created id=%s provider=%s", media.id, media.provider)
    return _build_response(media, formats)
