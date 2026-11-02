from fastapi import APIRouter, Depends
from app.api.deps import get_current_active_user
from app.api.v1 import auth, downloads, videos
from app.models.user import User
from app.schemas.user import UserRead

api_v1_router = APIRouter()

# Auth routes: /api/v1/auth/...
api_v1_router.include_router(auth.router)

# Video / metadata routes: /api/v1/videos/...
api_v1_router.include_router(videos.router)

# Download / processing routes: /api/v1/downloads/...
api_v1_router.include_router(downloads.router)


# /api/v1/users/me  (Section 7 of the API design spec)
@api_v1_router.get(
    "/users/me",
    response_model=UserRead,
    tags=["Users"],
    summary="Get current user profile",
)
async def get_user_me(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Retrieve the profile of the currently logged-in user."""
    return current_user
