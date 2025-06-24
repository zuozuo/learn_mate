"""API endpoints for conversation management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlmodel import Session

from app.api.v1.auth import get_current_user
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.user import User
from app.services.database import database_service
from app.services.conversation_service import ConversationService
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    ConversationDetailResponse,
)

router = APIRouter()


@router.post("/", response_model=ConversationResponse)
@limiter.limit("30/minute")
async def create_conversation(
    request: Request,
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation.

    Args:
        request: FastAPI request object
        conversation_data: Conversation creation data
        current_user: Current authenticated user

    Returns:
        Created conversation
    """
    try:
        with Session(database_service.engine) as session:
            service = ConversationService(session)
            conversation = await service.create_conversation(
                user_id=current_user.id, title=conversation_data.title, first_message=conversation_data.first_message
            )

            logger.info("conversation_created_via_api", user_id=current_user.id, conversation_id=str(conversation.id))

            return ConversationResponse.model_validate(conversation)
    except Exception as e:
        logger.error("create_conversation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=ConversationListResponse)
@limiter.limit("60/minute")
async def get_conversations(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Get user's conversations with pagination.

    Args:
        request: FastAPI request object
        page: Page number (1-indexed)
        limit: Items per page
        search: Optional search query
        current_user: Current authenticated user

    Returns:
        Paginated list of conversations
    """
    try:
        with Session(database_service.engine) as session:
            service = ConversationService(session)
            conversations, total = await service.get_conversations(
                user_id=current_user.id, page=page, limit=limit, search=search
            )

            return ConversationListResponse(conversations=conversations, total=total, page=page, limit=limit)
    except Exception as e:
        logger.error("get_conversations_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
@limiter.limit("60/minute")
async def get_conversation(
    request: Request,
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Get a conversation with all messages.

    Args:
        request: FastAPI request object
        conversation_id: ID of the conversation
        current_user: Current authenticated user

    Returns:
        Conversation with messages
    """
    try:
        with Session(database_service.engine) as session:
            service = ConversationService(session)
            conversation = await service.get_conversation_with_messages(
                conversation_id=conversation_id, user_id=current_user.id
            )

            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            return ConversationDetailResponse(**conversation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{conversation_id}", response_model=ConversationResponse)
@limiter.limit("30/minute")
async def update_conversation(
    request: Request,
    conversation_id: UUID,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a conversation.

    Args:
        request: FastAPI request object
        conversation_id: ID of the conversation
        update_data: Update data
        current_user: Current authenticated user

    Returns:
        Updated conversation
    """
    try:
        with Session(database_service.engine) as session:
            service = ConversationService(session)
            conversation = await service.update_conversation_title(
                conversation_id=conversation_id, user_id=current_user.id, title=update_data.title
            )

            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            logger.info("conversation_updated", conversation_id=str(conversation_id), user_id=current_user.id)

            return ConversationResponse.model_validate(conversation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_conversation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
@limiter.limit("30/minute")
async def delete_conversation(
    request: Request,
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation (soft delete).

    Args:
        request: FastAPI request object
        conversation_id: ID of the conversation
        current_user: Current authenticated user

    Returns:
        Success message
    """
    try:
        with Session(database_service.engine) as session:
            service = ConversationService(session)
            deleted = await service.delete_conversation(conversation_id=conversation_id, user_id=current_user.id)

            if not deleted:
                raise HTTPException(status_code=404, detail="Conversation not found")

            logger.info("conversation_deleted", conversation_id=str(conversation_id), user_id=current_user.id)

            return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_conversation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
