"""Login history model for tracking user login attempts."""

from typing import TYPE_CHECKING, Optional
from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class LoginHistory(BaseModel, table=True):
    """Model for tracking user login history.

    Attributes:
        id: Primary key (UUID)
        user_id: Foreign key to user
        ip_address: IP address of login attempt
        user_agent: User agent string
        login_at: Timestamp of login attempt
        success: Whether login was successful
        user: Relationship to User model
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    ip_address: Optional[str] = Field(max_length=45)  # IPv6 max length
    user_agent: Optional[str] = Field(default=None)
    login_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = Field(default=True)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="login_history")


# Update User model to include login_history relationship
from app.models.user import User  # noqa: E402
