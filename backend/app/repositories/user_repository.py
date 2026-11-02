from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository handling database operations for User accounts."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalars().first()

    async def create_user(self, email: str, password_hash: str, role: str = "user") -> User:
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        return await self.create(user)
