"""Download repository for database CRUD on Download records."""
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.download import Download
from app.repositories.base import BaseRepository


class DownloadRepository(BaseRepository[Download]):
    def __init__(self, session: AsyncSession):
        super().__init__(Download, session)

    async def list_for_user(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> Tuple[List[Download], int]:
        count_q = select(func.count(Download.id)).where(Download.user_id == user_id)
        count_res = await self.session.execute(count_q)
        total = count_res.scalar_one()

        result = await self.session.execute(
            select(Download)
            .where(Download.user_id == user_id)
            .order_by(Download.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_user_active_count(self, user_id: str) -> int:
        result = await self.session.execute(
            select(func.count(Download.id)).where(
                Download.user_id == user_id,
                Download.status.in_(["queued", "processing", "uploading"]),
            )
        )
        return result.scalar_one()

    async def get_by_id_for_user(self, download_id: str, user_id: str) -> Optional[Download]:
        result = await self.session.execute(
            select(Download).where(
                Download.id == download_id,
                Download.user_id == user_id,
            )
        )
        return result.scalars().first()
