from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import TimeStampedUUIDModel


class DownloadHistory(TimeStampedUUIDModel):
    """Audit record of every time a completed file is accessed by a user."""
    __tablename__ = "download_history"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    download_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("downloads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ip_hash: Mapped[str] = mapped_column(String(128), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")  # noqa: F821
    download: Mapped["Download"] = relationship("Download", back_populates="history_entries")  # noqa: F821

    def __repr__(self) -> str:
        return f"<DownloadHistory id={self.id} download_id={self.download_id}>"
