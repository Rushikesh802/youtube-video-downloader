"""
Mock media provider for automated tests and local development.

Returns deterministic, controlled fixture data without any outbound
network calls. This provider does NOT fetch real media.
"""
from app.services.providers.base import BaseMediaProvider, ProviderError, ProviderFormat, ProviderMetadata

# Stable fixture catalogue keyed by URL substring for test predictability
_MOCK_CATALOGUE: dict[str, ProviderMetadata] = {
    "test_720p": ProviderMetadata(
        title="Sample Test Video 720p",
        provider="youtube.com",
        source_url="https://www.youtube.com/watch?v=test_720p",
        thumbnail_url="https://img.youtube.com/vi/test_720p/maxresdefault.jpg",
        duration=300,
        uploader="Test Channel",
        description="A controlled test fixture video.",
        formats=[
            ProviderFormat(format="mp4", resolution="720p", filesize_approx=150_000_000),
            ProviderFormat(format="mp4", resolution="480p", filesize_approx=80_000_000),
            ProviderFormat(format="webm", resolution="720p", filesize_approx=120_000_000),
            ProviderFormat(format="mp3", resolution="audio_only", filesize_approx=8_000_000),
        ],
    ),
    "test_1080p": ProviderMetadata(
        title="Sample Test Video 1080p",
        provider="youtube.com",
        source_url="https://www.youtube.com/watch?v=test_1080p",
        thumbnail_url="https://img.youtube.com/vi/test_1080p/maxresdefault.jpg",
        duration=600,
        uploader="Test Channel HD",
        description="A controlled 1080p test fixture.",
        formats=[
            ProviderFormat(format="mp4", resolution="1080p", filesize_approx=500_000_000),
            ProviderFormat(format="mp4", resolution="720p", filesize_approx=200_000_000),
            ProviderFormat(format="webm", resolution="1080p", filesize_approx=400_000_000),
            ProviderFormat(format="mp3", resolution="audio_only", filesize_approx=15_000_000),
        ],
    ),
}

_DEFAULT_FIXTURE = ProviderMetadata(
    title="Mock Authorized Video",
    provider="youtube.com",
    source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    duration=212,
    uploader="RickAstleyVEVO",
    description="Never gonna give you up.",
    formats=[
        ProviderFormat(format="mp4", resolution="720p", filesize_approx=100_000_000),
        ProviderFormat(format="mp4", resolution="360p", filesize_approx=40_000_000),
        ProviderFormat(format="webm", resolution="720p", filesize_approx=85_000_000),
        ProviderFormat(format="mp3", resolution="audio_only", filesize_approx=5_000_000),
    ],
)


class MockProvider(BaseMediaProvider):
    """Deterministic mock provider for tests and offline development."""

    @property
    def provider_domain(self) -> str:
        return "youtube.com"

    async def fetch_metadata(self, url: str) -> ProviderMetadata:
        if "error" in url.lower() or "fail" in url.lower():
            raise ProviderError("Mock: simulated provider failure for URL: " + url)

        for key, fixture in _MOCK_CATALOGUE.items():
            if key in url:
                return fixture

        return _DEFAULT_FIXTURE
