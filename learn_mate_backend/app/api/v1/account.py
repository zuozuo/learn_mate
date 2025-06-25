"""Account authentication API endpoints."""

from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.database import DatabaseService
from app.services.auth_service import AuthService
from app.schemas.auth import UserRegister, UserLogin, LoginResponse, UserInfo, TokenRefreshRequest
from app.models.user import User
from app.core.jwt import JWTManager


router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
db_service = DatabaseService()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> User:
    """Get current authenticated user.

    Args:
        credentials: Bearer token credentials
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)) -> UserInfo:
    """Register a new user.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user information

    Raises:
        HTTPException: If registration fails
    """
    auth_service = AuthService(db)
    user = await auth_service.register_user(user_data)

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or username already registered")

    return UserInfo(id=user.id, email=user.email, username=user.username, created_at=user.created_at)


@router.post("/login", response_model=LoginResponse)
async def login(login_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    """Login user and get access token.

    Args:
        login_data: Login credentials
        request: HTTP request
        db: Database session

    Returns:
        Login response with tokens

    Raises:
        HTTPException: If login fails
    """
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    auth_service = AuthService(db)
    login_response = await auth_service.login_user(login_data, ip_address=ip_address, user_agent=user_agent)

    if not login_response:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return login_response


@router.post("/refresh")
async def refresh_token(refresh_data: TokenRefreshRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token request
        db: Database session

    Returns:
        New access token

    Raises:
        HTTPException: If refresh fails
    """
    auth_service = AuthService(db)
    token_response = await auth_service.refresh_token(refresh_data.refresh_token)

    if not token_response:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return token_response


@router.post("/logout")
async def logout(current_user: Annotated[User, Depends(get_current_user)]) -> dict:
    """Logout current user.

    Args:
        current_user: Current authenticated user

    Returns:
        Logout success message
    """
    # In a real implementation, you might want to:
    # 1. Add the token to a blacklist
    # 2. Clear server-side sessions
    # 3. Log the logout event

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserInfo:
    """Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at,
    )
