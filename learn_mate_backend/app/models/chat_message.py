"""Chat message model for storing individual messages in conversations."""

from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4
from enum import Enum

from sqlmodel import Field, Relationship, JSON, Column
from sqlalchemy import text, UniqueConstraint

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageRole(str, Enum):
    """Enum for message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel, table=True):
    """Chat message model for storing messages in conversations.

    Attributes:
        id: The primary key (UUID)
        conversation_id: Foreign key to conversation
        role: Message role (user/assistant/system)
        content: Message content
        thinking: AI thinking process content
        message_index: Order of message in conversation
        created_at: When the message was created
        metadata: Additional metadata as JSONB
        conversation: Relationship to conversation
    """

    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("conversation_id", "message_index", name="unique_conversation_message_index"),)

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    conversation_id: UUID = Field(foreign_key="conversations.id", index=True)
    role: MessageRole = Field(max_length=50)
    content: str
    thinking: Optional[str] = Field(default=None)
    message_index: int = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Relationships
    conversation: "Conversation" = Relationship(back_populates="messages")
