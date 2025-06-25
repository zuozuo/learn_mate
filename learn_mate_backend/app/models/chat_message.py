"""Chat message model for storing individual messages in conversations."""

from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional, List
from uuid import UUID, uuid4
from enum import Enum

from sqlmodel import Field, Relationship, JSON, Column
from sqlalchemy import text, UniqueConstraint

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.message_branch import MessageBranch


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
        branch_id: Foreign key to message branch
        version_number: Version number within the branch
        is_current_version: Whether this is the current version
        parent_version_id: Parent version for tracking edit history
        branch: Relationship to message branch
        parent_version: Relationship to parent version
        child_versions: Child versions of this message
    """

    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "message_index",
            "branch_id",
            "version_number",
            name="unique_conversation_message_branch_version",
        ),
    )

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

    # Branch-related fields
    branch_id: Optional[UUID] = Field(default=None, foreign_key="message_branches.id", index=True)
    version_number: int = Field(default=1, index=True)
    is_current_version: bool = Field(default=True, index=True)
    parent_version_id: Optional[UUID] = Field(default=None, foreign_key="chat_messages.id", index=True)

    # Relationships
    conversation: "Conversation" = Relationship(back_populates="messages")
    branch: Optional["MessageBranch"] = Relationship(
        back_populates="messages", sa_relationship_kwargs={"foreign_keys": "ChatMessage.branch_id"}
    )
    parent_version: Optional["ChatMessage"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ChatMessage.parent_version_id", "remote_side": "ChatMessage.id"}
    )
    child_versions: List["ChatMessage"] = Relationship(
        back_populates="parent_version", sa_relationship_kwargs={"foreign_keys": "ChatMessage.parent_version_id"}
    )
