"""API endpoints for message management within conversations."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.api.v1.auth import get_current_user
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.user import User
from app.services.database import database_service
from app.services.enhanced_chat_service import EnhancedChatService
from app.schemas.chat import ChatRequest, Message, StreamResponse

router = APIRouter()


@router.post("/conversations/{conversation_id}/messages", response_model=Message)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    conversation_id: UUID,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Send a message to a conversation and get AI response.

    Args:
        request: FastAPI request object
        conversation_id: ID of the conversation
        chat_request: Chat request with message content
        current_user: Current authenticated user

    Returns:
        AI response message
    """
    try:
        # Extract the last user message
        user_message = None
        for msg in reversed(chat_request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        with Session(database_service.engine) as session:
            service = EnhancedChatService(session)
            response = await service.send_message(
                conversation_id=conversation_id, user_id=current_user.id, content=user_message
            )

            logger.info("message_sent", conversation_id=str(conversation_id), user_id=current_user.id)

            return response
    except HTTPException:
        # Re-raise HTTPExceptions without modification
        raise
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("send_message_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/messages/stream")
@limiter.limit("30/minute")
async def send_message_stream(
    request: Request,
    conversation_id: UUID,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Send a message and get streaming AI response.

    Args:
        request: FastAPI request object
        conversation_id: ID of the conversation
        chat_request: Chat request with message content
        current_user: Current authenticated user

    Returns:
        Streaming response
    """
    try:
        # Extract the last user message
        user_message = None
        for msg in reversed(chat_request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        async def event_generator():
            """Generate streaming events."""
            try:
                with Session(database_service.engine) as session:
                    service = EnhancedChatService(session)

                    async for chunk in service.send_message_stream(
                        conversation_id=conversation_id, user_id=current_user.id, content=user_message
                    ):
                        if chunk:
                            response = StreamResponse(content=chunk, done=False)
                            yield f"data: {json.dumps(response.model_dump())}\n\n"

                    # Send completion message
                    final_response = StreamResponse(content="", done=True)
                    yield f"data: {json.dumps(final_response.model_dump())}\n\n"

                    logger.info("message_streamed", conversation_id=str(conversation_id), user_id=current_user.id)

            except ValueError as e:
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"
            except Exception as e:
                logger.error("stream_message_failed", error=str(e))
                error_response = StreamResponse(content="Internal error", done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("stream_message_setup_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
