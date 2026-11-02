from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# ─── Format schemas ───────────────────────────────────────────────────────────

class FormatOption(BaseModel):
    format: str = Field(..., examples=["mp4", "webm", "mp3"])
    resolution: str = Field(..., examples=["720p", "1080p", "audio_only"])
    filesize_approx: Optional[int] = Field(None, description="Approximate file size in bytes")
    note: Optional[str] = None


# ─── Video / Media schemas ────────────────────────────────────────────────────

class VideoMetadataRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2048, description="Authorized media URL")


class VideoMetadataResponse(BaseModel):
    media_id: str
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = Field(None, description="Duration in seconds")
    provider: str
    uploader: Optional[str] = None
    description: Optional[str] = None
    available_formats: List[FormatOption] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VideoRead(BaseModel):
    id: str
    source_url: str
    title: str
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    provider: str
    uploader: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
