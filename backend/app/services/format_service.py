"""
Format service.

Independently verifies that a requested (format, resolution) combination
is currently permitted for a given Media record. The backend must never
trust the frontend's format selection — this service performs a server-side
re-verification step before a download job is created.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.models.media import Media
from app.schemas.video import FormatOption
from app.services.providers.base import ProviderError
from app.services.providers.mock_provider import MockProvider

# Simple synchronous allowlist for quick validation
_ALLOWED_FORMATS: set[str] = {"mp4", "webm", "mp3"}
_ALLOWED_RESOLUTIONS: set[str] = {"360p", "480p", "720p", "1080p", "audio_only"}


def assert_format_allowed(format: str, resolution: str) -> None:
    """
    Raise BadRequestException if format/resolution combination is not on the allowlist.
    This is a fast, allowlist-only pre-check — provider verification follows.
    """
    if format not in _ALLOWED_FORMATS:
        raise BadRequestException(
            f"Format '{format}' is not supported. Allowed: {sorted(_ALLOWED_FORMATS)}"
        )
    if resolution not in _ALLOWED_RESOLUTIONS:
        raise BadRequestException(
            f"Resolution '{resolution}' is not supported. Allowed: {sorted(_ALLOWED_RESOLUTIONS)}"
        )
    if format == "mp3" and resolution != "audio_only":
        raise BadRequestException(
            "Format 'mp3' requires resolution 'audio_only'."
        )
    if format != "mp3" and resolution == "audio_only":
        raise BadRequestException(
            "Resolution 'audio_only' is only valid with format 'mp3'."
        )


async def verify_format_for_media(
    media: Media,
    format: str,
    resolution: str,
) -> FormatOption:
    """
    Re-verify that the requested format/resolution is available for this specific media.

    Fetches the current permitted format list from the provider and returns
    the matching FormatOption if found.

    Raises:
        BadRequestException: If the combination is not currently offered.
    """
    assert_format_allowed(format, resolution)

    # Re-query the provider for the current permitted format set
    # In production this would dispatch to the correct registered provider.
    provider = MockProvider()  # TODO: wire through provider registry based on media.provider
    try:
        meta = await provider.fetch_metadata(media.source_url)
    except ProviderError as e:
        raise BadRequestException(f"Could not verify available formats: {e}") from e

    for f in meta.formats:
        if f.format == format and f.resolution == resolution:
            return FormatOption(
                format=f.format,
                resolution=f.resolution,
                filesize_approx=f.filesize_approx,
                note=f.note,
            )

    raise BadRequestException(
        f"Format '{format}' at '{resolution}' is not currently available for this media. "
        "Please re-fetch metadata to see current options."
    )
