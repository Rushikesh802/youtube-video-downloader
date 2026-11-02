from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import TimeStampedUUIDModel


class Download(TimeStampedUUIDModel):
    """Represents a media processing job — from queued to completed/expired."""
    __tablename__ = "downloads"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="queued", index=True
    )
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")  # noqa: F821
    media: Mapped["Media"] = relationship("Media", back_populates="downloads")  # noqa: F821
    history_entries: Mapped[list["DownloadHistory"]] = relationship(  # noqa: F821
        "DownloadHistory", back_populates="download", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Download id={self.id} status={self.status} format={self.format}>"
