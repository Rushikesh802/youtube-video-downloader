from datetime import timedelta
from fastapi import APIRouter, Depends, status
from app.api.deps import get_current_active_user, get_user_repository
from app.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import Token, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    user_in: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository),
) -> Token:
    """Create a new user account and immediately return an access token."""
    existing_user = await user_repo.get_by_email(user_in.email)
    if existing_user:
        raise ConflictException("An account with this email address already exists.")

    hashed_pw = hash_password(user_in.password)
    user = await user_repo.create_user(
        email=user_in.email,
        password_hash=hashed_pw,
        role="user",
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
        extra_claims={"email": user.email, "role": user.role},
    )

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and obtain access token",
)
async def login(
    credentials: UserLogin,
    user_repo: UserRepository = Depends(get_user_repository),
) -> Token:
    """Authenticate with email and password to receive a bearer JWT token."""
    user = await user_repo.get_by_email(credentials.email)
    if not user:
        raise UnauthorizedException("Incorrect email or password.")

    if not verify_password(credentials.password, user.password_hash):
        raise UnauthorizedException("Incorrect email or password.")

    if not user.is_active:
        raise UnauthorizedException("Account is inactive.")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
        extra_claims={"email": user.email, "role": user.role},
    )

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Retrieve current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Return the profile information of the currently authenticated user."""
    return current_user
