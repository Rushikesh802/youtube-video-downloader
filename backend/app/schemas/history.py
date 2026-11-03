from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DownloadHistoryItem(BaseModel):
    id: str
    download_id: str
    downloaded_at: datetime
    ip_hash: Optional[str] = Field(None, description="Hashed client IP for privacy-conscious audit")

    # Joined metadata from Download and Media
    format: Optional[str] = None
    resolution: Optional[str] = None
    file_size: Optional[int] = None
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    source_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DownloadHistoryListResponse(BaseModel):
    items: List[DownloadHistoryItem]
    total: int
    skip: int
    limit: int
