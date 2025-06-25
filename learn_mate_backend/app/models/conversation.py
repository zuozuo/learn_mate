"""Conversation model for storing chat conversations."""

from datetime import datetime, UTC
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, JSON, Column
from sqlalchemy import text

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.chat_message import ChatMessage
    from app.models.message_branch import MessageBranch


class Conversation(BaseModel, table=True):
    """Conversation model for storing chat conversations.

    Attributes:
        id: The primary key (UUID)
        user_id: Foreign key to user
        title: Conversation title
        summary: Optional conversation summary
        created_at: When the conversation was created
        updated_at: When the conversation was last updated
        is_deleted: Soft delete flag
        metadata: Additional metadata as JSONB
        user: Relationship to user
        messages: Relationship to chat messages
    """

    __tablename__ = "conversations"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=255)
    summary: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)}
    )
    is_deleted: bool = Field(default=False, index=True)
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Relationships
    user: "User" = Relationship(back_populates="conversations")
    messages: List["ChatMessage"] = Relationship(back_populates="conversation", cascade_delete=True)
    branches: List["MessageBranch"] = Relationship(back_populates="conversation", cascade_delete=True)
