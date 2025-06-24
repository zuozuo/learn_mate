"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

import json
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse
from app.core.metrics import llm_stream_duration_seconds
from app.api.v1.auth import get_current_session, get_current_user
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)
from app.services.database import database_service
from app.services.enhanced_chat_service import EnhancedChatService
from sqlmodel import Session as DBSession

router = APIRouter()
agent = LangGraphAgent()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
    current_user: User = Depends(get_current_user),
):
    """Process a chat request using LangGraph (backward compatibility).

    This endpoint creates a temporary conversation for each request.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.
        current_user: The current authenticated user.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        # Extract the last user message
        user_message = None
        for msg in reversed(chat_request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # Create temporary conversation and process
        with DBSession(database_service.engine) as db_session:
            service = EnhancedChatService(db_session)

            # Create temporary conversation
            conversation_id = await service.create_temporary_conversation(
                user_id=current_user.id, first_message=user_message
            )

            # Get response (message already saved)
            result = await agent.get_response(chat_request.messages, session.id, user_id=session.user_id)

            logger.info("chat_request_processed", session_id=session.id, conversation_id=str(conversation_id))

            return ChatResponse(messages=result)
    except Exception as e:
        logger.error("chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
    current_user: User = Depends(get_current_user),
):
    """Process a chat request using LangGraph with streaming response (backward compatibility).

    This endpoint creates a temporary conversation for each request.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.
        current_user: The current authenticated user.

    Returns:
        StreamingResponse: A streaming response of the chat completion.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "stream_chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        async def event_generator():
            """Generate streaming events.

            Yields:
                str: Server-sent events in JSON format.

            Raises:
                Exception: If there's an error during streaming.
            """
            try:
                # Get model name based on LLM provider
                model_name = getattr(agent.llm, "model_name", None) or getattr(agent.llm, "model", "unknown")
                chunk_count = 0
                total_content = ""

                with llm_stream_duration_seconds.labels(model=model_name).time():
                    async for chunk in agent.get_stream_response(
                        chat_request.messages, session.id, user_id=session.user_id
                    ):
                        chunk_count += 1
                        total_content += chunk

                        logger.debug(
                            "streaming_chunk_details",
                            chunk_number=chunk_count,
                            chunk_content=repr(chunk[:50]) + "..." if len(chunk) > 50 else repr(chunk),
                            chunk_length=len(chunk),
                            total_length_so_far=len(total_content),
                            session_id=session.id,
                        )

                        # 直接转发原始chunk内容，不做任何解析处理
                        if chunk:
                            response = StreamResponse(content=chunk, done=False)
                            yield f"data: {json.dumps(response.model_dump())}\n\n"

                # Send final message indicating completion
                final_response = StreamResponse(content="", done=True)
                yield f"data: {json.dumps(final_response.model_dump())}\n\n"

            except Exception as e:
                logger.error(
                    "stream_chat_request_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True,
                )
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(
            "stream_chat_request_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_messages(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages.
    """
    try:
        messages = await agent.get_chat_history(session.id)
        return ChatResponse(messages=messages)
    except Exception as e:
        logger.error("get_messages_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def clear_chat_history(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Clear all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        dict: A message indicating the chat history was cleared.
    """
    try:
        await agent.clear_chat_history(session.id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error("clear_chat_history_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
