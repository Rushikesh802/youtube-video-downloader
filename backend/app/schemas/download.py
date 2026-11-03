from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

DownloadStatus = Literal[
    "queued", "processing", "uploading", "completed", "failed", "expired", "cancelled"
]
OutputFormat = Literal["mp4", "webm", "mp3"]
Resolution = Literal["360p", "480p", "720p", "1080p", "audio_only"]


class DownloadCreateRequest(BaseModel):
    media_id: str = Field(..., description="ID of the previously validated Media record")
    format: OutputFormat = Field(..., description="Desired output format")
    resolution: Resolution = Field(..., description="Desired output resolution")


class DownloadRead(BaseModel):
    id: str
    user_id: str
    media_id: str
    status: str
    format: str
    resolution: str
    progress: int = Field(ge=0, le=100)
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownloadListResponse(BaseModel):
    items: List[DownloadRead]
    total: int
    skip: int
    limit: int


class DownloadJobCreated(BaseModel):
    job_id: str
    status: str = "queued"
    message: str = "Processing request received. Your download has been queued."


class DownloadFileResponse(BaseModel):
    download_url: str = Field(..., description="Short-lived signed S3 URL or direct delivery URL")
    expires_in_seconds: int = Field(..., description="Validity period of the signed URL in seconds")
    filename: str = Field(..., description="Sanitized human-readable filename for Content-Disposition")
    file_size: Optional[int] = Field(None, description="Output file size in bytes")
    content_type: str = Field("application/octet-stream", description="MIME content type")
