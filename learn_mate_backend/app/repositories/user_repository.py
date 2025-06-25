"""User repository for database operations."""

from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.login_history import LoginHistory


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the repository.

        Args:
            db: Database session
        """
        self.db = db

    async def create_user(self, email: str, username: str, hashed_password: str) -> Optional[User]:
        """Create a new user.

        Args:
            email: User email
            username: Username
            hashed_password: Hashed password

        Returns:
            Created user or None if user already exists
        """
        try:
            user = User(email=email, username=username, hashed_password=hashed_password)
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError:
            await self.db.rollback()
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp.

        Args:
            user_id: User ID
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.last_login_at = datetime.utcnow()
            await self.db.commit()

    async def record_login_attempt(
        self, user_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None, success: bool = True
    ) -> LoginHistory:
        """Record a login attempt.

        Args:
            user_id: User ID
            ip_address: IP address
            user_agent: User agent string
            success: Whether login was successful

        Returns:
            Login history record
        """
        login_record = LoginHistory(user_id=user_id, ip_address=ip_address, user_agent=user_agent, success=success)
        self.db.add(login_record)
        await self.db.commit()
        await self.db.refresh(login_record)
        return login_record

    async def check_user_active(self, user_id: int) -> bool:
        """Check if user is active.

        Args:
            user_id: User ID

        Returns:
            True if user is active, False otherwise
        """
        result = await self.db.execute(select(User.is_active).where(User.id == user_id))
        is_active = result.scalar_one_or_none()
        return is_active if is_active is not None else False
