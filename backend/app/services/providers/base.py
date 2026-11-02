"""
Abstract base class for authorized media providers.

All concrete providers must implement this interface, enabling
the metadata service to remain provider-agnostic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProviderFormat:
    """A single downloadable format variant offered by a provider."""
    format: str            # e.g. "mp4", "webm", "mp3"
    resolution: str        # e.g. "720p", "1080p", "audio_only"
    filesize_approx: Optional[int] = None   # bytes, if known
    note: Optional[str] = None


@dataclass
class ProviderMetadata:
    """Normalized metadata returned by any provider."""
    title: str
    provider: str          # provider domain identifier, e.g. "youtube.com"
    source_url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None      # seconds
    uploader: Optional[str] = None
    description: Optional[str] = None
    formats: List[ProviderFormat] = field(default_factory=list)


class BaseMediaProvider(ABC):
    """Contract all media providers must satisfy."""

    @property
    @abstractmethod
    def provider_domain(self) -> str:
        """Return the domain this provider handles, e.g. 'youtube.com'."""

    @abstractmethod
    async def fetch_metadata(self, url: str) -> ProviderMetadata:
        """
        Retrieve title, duration, thumbnail, and permitted format list for *url*.

        Raises:
            ProviderError: If the URL cannot be fetched or is unauthorized.
        """

    def supports(self, provider_domain: str) -> bool:
        """Return True if this provider handles the given domain."""
        return provider_domain == self.provider_domain


class ProviderError(Exception):
    """Raised when a provider cannot fulfill a metadata or download request."""
