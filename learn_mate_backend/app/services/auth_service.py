"""Authentication service for user management."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.jwt import JWTManager
from app.schemas.auth import UserRegister, UserLogin, LoginResponse, UserInfo


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the service.

        Args:
            db: Database session
        """
        self.db = db
        self.user_repo = UserRepository(db)

    async def register_user(self, user_data: UserRegister) -> Optional[User]:
        """Register a new user.

        Args:
            user_data: User registration data

        Returns:
            Created user or None if registration failed
        """
        # Check if user already exists
        existing_user = await self.user_repo.get_user_by_email(user_data.email)
        if existing_user:
            return None

        # Check if username is taken
        existing_username = await self.user_repo.get_user_by_username(user_data.username)
        if existing_username:
            return None

        # Hash password
        hashed_password = User.hash_password(user_data.password.get_secret_value())

        # Create user
        return await self.user_repo.create_user(
            email=user_data.email, username=user_data.username, hashed_password=hashed_password
        )

    async def login_user(
        self, login_data: UserLogin, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Optional[LoginResponse]:
        """Authenticate user and create tokens.

        Args:
            login_data: Login credentials
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Login response with tokens or None if authentication failed
        """
        # Get user by email
        user = await self.user_repo.get_user_by_email(login_data.email)
        if not user:
            return None

        # Verify password
        if not user.verify_password(login_data.password.get_secret_value()):
            # Record failed login attempt
            await self.user_repo.record_login_attempt(
                user_id=user.id, ip_address=ip_address, user_agent=user_agent, success=False
            )
            return None

        # Check if user is active
        if not user.is_active:
            return None

        # Update last login
        await self.user_repo.update_last_login(user.id)

        # Record successful login
        await self.user_repo.record_login_attempt(
            user_id=user.id, ip_address=ip_address, user_agent=user_agent, success=True
        )

        # Create tokens
        tokens = JWTManager.create_token_pair(user.id, user.email)

        # Calculate expiration time
        expires_in = JWTManager.access_token_expire_minutes * 60

        # Prepare response
        return LoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"] if login_data.remember_me else None,
            token_type=tokens["token_type"],
            expires_in=expires_in,
            user=UserInfo(id=user.id, email=user.email, username=user.username, created_at=user.created_at),
        )

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            New token pair or None if refresh failed
        """
        # Verify refresh token
        token_data = JWTManager.verify_token(refresh_token)
        if not token_data or token_data.token_type != "refresh":
            return None

        # Get user
        user = await self.user_repo.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            return None

        # Create new token pair
        tokens = JWTManager.create_token_pair(user.id, user.email)

        return {
            "access_token": tokens["access_token"],
            "token_type": tokens["token_type"],
            "expires_in": JWTManager.access_token_expire_minutes * 60,
        }

    async def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from token.

        Args:
            token: JWT access token

        Returns:
            User if token is valid, None otherwise
        """
        # Verify token
        token_data = JWTManager.verify_token(token)
        if not token_data or token_data.token_type != "access":
            return None

        # Get user
        user = await self.user_repo.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            return None

        return user
