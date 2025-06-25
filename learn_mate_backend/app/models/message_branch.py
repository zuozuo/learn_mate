"""Message branch model for supporting message versioning and branching."""

from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional, List
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship
from sqlalchemy import text, UniqueConstraint

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.chat_message import ChatMessage


class MessageBranch(BaseModel, table=True):
    """Message branch model for organizing message versions.

    Attributes:
        id: The primary key (UUID)
        conversation_id: Foreign key to conversation
        parent_message_id: Message where this branch starts
        sequence_number: Order of branch creation
        branch_name: Human-readable branch name
        created_at: When the branch was created
        updated_at: When the branch was last updated
        conversation: Relationship to conversation
        parent_message: Relationship to parent message
        messages: Messages in this branch
    """

    __tablename__ = "message_branches"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "parent_message_id", "sequence_number", name="unique_conversation_parent_sequence"
        ),
    )

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    conversation_id: UUID = Field(foreign_key="conversations.id", index=True)
    parent_message_id: Optional[UUID] = Field(default=None, foreign_key="chat_messages.id", index=True)
    sequence_number: int = Field()
    branch_name: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)}
    )

    # Relationships
    conversation: "Conversation" = Relationship(back_populates="branches")
    parent_message: Optional["ChatMessage"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "MessageBranch.parent_message_id", "remote_side": "ChatMessage.id"}
    )
    messages: List["ChatMessage"] = Relationship(
        back_populates="branch", sa_relationship_kwargs={"foreign_keys": "ChatMessage.branch_id"}
    )
