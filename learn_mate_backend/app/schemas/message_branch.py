"""Message branch schemas for API validation."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class MessageBranchBase(BaseModel):
    """Base message branch schema."""

    branch_name: Optional[str] = Field(None, max_length=100)


class MessageBranchCreate(MessageBranchBase):
    """Schema for creating a message branch."""

    parent_message_id: Optional[UUID] = None


class MessageBranchUpdate(BaseModel):
    """Schema for updating a message branch."""

    branch_name: Optional[str] = Field(None, max_length=100)


class MessageBranch(MessageBranchBase):
    """Message branch response schema."""

    id: UUID
    conversation_id: UUID
    parent_message_id: Optional[UUID]
    sequence_number: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class MessageVersion(BaseModel):
    """Message version schema."""

    id: UUID
    content: str
    version_number: int
    branch_id: UUID
    branch_name: Optional[str]
    created_at: datetime
    is_current_version: bool

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class MessageEditRequest(BaseModel):
    """Request schema for editing a message."""

    content: str = Field(..., min_length=1)
    create_branch: bool = Field(True, description="Whether to create a new branch")


class MessageEditResponse(BaseModel):
    """Response schema for editing a message."""

    message: MessageVersion
    branch: Optional[MessageBranch]
    new_assistant_message: Optional[MessageVersion]


class BranchTreeNode(BaseModel):
    """Branch tree node for visualization."""

    id: UUID
    name: Optional[str]
    parent_message_id: Optional[UUID]
    message_count: int
    children: List["BranchTreeNode"] = []

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Update forward references
BranchTreeNode.model_rebuild()
