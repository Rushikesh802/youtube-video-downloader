from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import TimeStampedUUIDModel


class Media(TimeStampedUUIDModel):
    """Represents a validated authorized media source and its cached metadata."""
    __tablename__ = "media"

    source_url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(Text, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=True)  # seconds
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    uploader: Mapped[str] = mapped_column(String(256), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationship back to downloads
    downloads: Mapped[list["Download"]] = relationship(  # noqa: F821
        "Download", back_populates="media", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Media id={self.id} provider={self.provider} title={self.title!r}>"
