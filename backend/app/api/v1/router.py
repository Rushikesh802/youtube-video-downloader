from fastapi import APIRouter, Depends
from app.api.deps import get_current_active_user
from app.api.v1 import auth
from app.models.user import User
from app.schemas.user import UserRead

api_v1_router = APIRouter()

# Include Auth endpoints under /api/v1/auth
api_v1_router.include_router(auth.router)


# Also support /api/v1/users/me directly as specified in API design Section 7
@api_v1_router.get(
    "/users/me",
    response_model=UserRead,
    tags=["Users"],
    summary="Get current user profile",
)
async def get_user_me(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Retrieve profile of the currently logged-in user."""
    return current_user
