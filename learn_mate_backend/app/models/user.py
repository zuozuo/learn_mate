"""This file contains the user model for the application."""

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)
from datetime import datetime

import bcrypt
from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session
    from app.models.conversation import Conversation
    from app.models.login_history import LoginHistory


class User(BaseModel, table=True):
    """User model for storing user accounts.

    Attributes:
        id: The primary key
        email: User's email (unique)
        username: User's username (unique)
        hashed_password: Bcrypt hashed password
        is_active: Whether the user account is active
        is_verified: Whether the user email is verified
        last_login_at: Last login timestamp
        created_at: When the user was created
        sessions: Relationship to user's chat sessions
        conversations: Relationship to user's conversations
    """

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    last_login_at: Optional[datetime] = Field(default=None)
    sessions: List["Session"] = Relationship(back_populates="user")
    conversations: List["Conversation"] = Relationship(back_populates="user")
    login_history: List["LoginHistory"] = Relationship(back_populates="user")

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash."""
        return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# Avoid circular imports
from app.models.session import Session  # noqa: E402
