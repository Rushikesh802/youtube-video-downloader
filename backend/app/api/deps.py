from typing import Callable, Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

# Re-export get_db so API routers can import it from deps
__all__ = ["get_db", "get_current_user", "get_current_active_user", "require_role"]

# HTTPBearer authorization header scheme
security_scheme = HTTPBearer(auto_error=False)


async def get_user_repository(
    session: AsyncSession = Depends(get_db),
) -> UserRepository:
    """Dependency injecting UserRepository with current async session."""
    return UserRepository(session)


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Validate bearer token and resolve the current authenticated user."""
    if not auth or not auth.credentials:
        raise UnauthorizedException("Authentication credentials are required.")

    token = auth.credentials
    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired access token.")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Malformed token claims.")

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedException("User associated with this token does not exist.")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure authenticated user is active."""
    if not current_user.is_active:
        raise ForbiddenException("User account has been deactivated.")
    return current_user


def require_role(required_role: str) -> Callable:
    """Dependency factory checking user has sufficient role permissions."""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role and current_user.role != "admin":
            raise ForbiddenException(f"Action requires '{required_role}' privileges.")
        return current_user
    return role_checker
