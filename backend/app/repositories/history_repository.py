"""History repository for database CRUD and audit logging on DownloadHistory records."""
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.download import Download
from app.models.history import DownloadHistory
from app.repositories.base import BaseRepository


class HistoryRepository(BaseRepository[DownloadHistory]):
    def __init__(self, session: AsyncSession):
        super().__init__(DownloadHistory, session)

    async def create_entry(
        self,
        user_id: str,
        download_id: str,
        ip_hash: Optional[str] = None,
        downloaded_at: Optional[datetime] = None,
    ) -> DownloadHistory:
        """Create a new download audit entry."""
        entry = DownloadHistory(
            user_id=user_id,
            download_id=download_id,
            ip_hash=ip_hash,
            downloaded_at=downloaded_at or datetime.now(timezone.utc),
        )
        return await self.create(entry)

    async def list_for_user(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> Tuple[List[DownloadHistory], int]:
        """List download history entries for a specific user with related download and media loaded."""
        count_q = select(func.count(DownloadHistory.id)).where(DownloadHistory.user_id == user_id)
        count_res = await self.session.execute(count_q)
        total = count_res.scalar_one()

        result = await self.session.execute(
            select(DownloadHistory)
            .options(
                selectinload(DownloadHistory.download).selectinload(Download.media)
            )
            .where(DownloadHistory.user_id == user_id)
            .order_by(DownloadHistory.downloaded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_by_id_for_user(
        self, history_id: str, user_id: str
    ) -> Optional[DownloadHistory]:
        """Fetch a specific history entry owned by the user."""
        result = await self.session.execute(
            select(DownloadHistory)
            .options(
                selectinload(DownloadHistory.download).selectinload(Download.media)
            )
            .where(
                DownloadHistory.id == history_id,
                DownloadHistory.user_id == user_id,
            )
        )
        return result.scalars().first()
