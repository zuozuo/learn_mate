"""Schemas for conversation-related API endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""
    title: Optional[str] = Field(None, description="Conversation title")
    first_message: Optional[str] = Field(None, description="Optional first message")


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    title: str = Field(..., description="New conversation title")


class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    id: UUID
    title: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Schema for message in conversation."""
    id: UUID
    role: str
    content: str
    thinking: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """Schema for detailed conversation with messages."""
    id: UUID
    title: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]
    
    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Schema for paginated conversation list."""
    conversations: List[ConversationResponse]
    total: int
    page: int
    limit: int