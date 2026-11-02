"""Media repository for database CRUD on Media records."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.media import Media
from app.repositories.base import BaseRepository


class MediaRepository(BaseRepository[Media]):
    def __init__(self, session: AsyncSession):
        super().__init__(Media, session)

    async def get_by_url(self, url: str) -> Optional[Media]:
        result = await self.session.execute(
            select(Media).where(Media.source_url == url)
        )
        return result.scalars().first()
