"""
YouTube provider stub.

In production this should call the YouTube Data API v3 using an authorized
API key to retrieve video metadata. It never fetches the video stream itself —
stream retrieval is the responsibility of authorized Celery worker tasks.

For now this is a stub that raises ProviderError to signal the feature
needs a configured API key. Wire in your YouTube Data API client here.
"""
from app.services.providers.base import BaseMediaProvider, ProviderError, ProviderMetadata


class YouTubeProvider(BaseMediaProvider):
    """
    YouTube Data API v3 metadata provider.

    Requires: YOUTUBE_DATA_API_KEY environment variable to be set.
    See: https://developers.google.com/youtube/v3/getting-started
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    @property
    def provider_domain(self) -> str:
        return "youtube.com"

    async def fetch_metadata(self, url: str) -> ProviderMetadata:
        """
        Fetch video metadata from the YouTube Data API v3.

        Note: YouTube Data API access does NOT grant permission to download
        the underlying video stream. Only use this for metadata retrieval.
        Download authorization must be established separately through
        an authorized creator workflow (e.g., YouTube Studio, Google Takeout).
        """
        if not self._api_key:
            raise ProviderError(
                "YouTube Data API key is not configured. "
                "Set YOUTUBE_DATA_API_KEY in your environment."
            )

        # TODO: Implement YouTube Data API v3 call here.
        # Example using httpx:
        #   import httpx
        #   video_id = extract_video_id(url)
        #   async with httpx.AsyncClient() as client:
        #       resp = await client.get(
        #           "https://www.googleapis.com/youtube/v3/videos",
        #           params={"part": "snippet,contentDetails", "id": video_id, "key": self._api_key}
        #       )
        #       resp.raise_for_status()
        #       items = resp.json().get("items", [])
        #       if not items:
        #           raise ProviderError("Video not found or not accessible via Data API.")
        #       # Parse snippet, contentDetails, etc. into ProviderMetadata
        raise ProviderError("YouTubeProvider: YouTube Data API integration not yet implemented.")
