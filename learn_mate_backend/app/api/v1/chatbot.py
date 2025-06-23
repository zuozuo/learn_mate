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
from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)

router = APIRouter()
agent = LangGraphAgent()



@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """Process a chat request using LangGraph.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

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

       

        result = await agent.get_response(
            chat_request.messages, session.id, user_id=session.user_id
        )

        logger.info("chat_request_processed", session_id=session.id)

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
):
    """Process a chat request using LangGraph with streaming response.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

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
                full_response = ""
                thinking_content = ""
                response_content = ""
                in_thinking = False
                thinking_sent = False
                
                # Get model name based on LLM provider
                model_name = getattr(agent.llm, 'model_name', None) or getattr(agent.llm, 'model', 'unknown')
                with llm_stream_duration_seconds.labels(model=model_name).time():
                    async for chunk in agent.get_stream_response(
                        chat_request.messages, session.id, user_id=session.user_id
                     ):
                        full_response += chunk
                        
                        # 解析 thinking 标签
                        if "<think>" in chunk and not in_thinking:
                            in_thinking = True
                            # 发送 thinking 开始前的内容（如果有）
                            if "<think>" not in chunk.split("<think>")[0]:
                                content_before = chunk.split("<think>")[0]
                                if content_before.strip():
                                    response = StreamResponse(content=content_before, done=False, type="response")
                                    yield f"data: {json.dumps(response.model_dump())}\n\n"
                            # 开始发送 thinking 内容
                            thinking_part = chunk.split("<think>", 1)[-1]
                            if thinking_part:
                                thinking_content += thinking_part
                                response = StreamResponse(content=thinking_part, done=False, type="thinking")
                                yield f"data: {json.dumps(response.model_dump())}\n\n"
                        elif "</think>" in chunk and in_thinking:
                            # thinking 结束
                            parts = chunk.split("</think>", 1)
                            thinking_part = parts[0]
                            thinking_content += thinking_part
                            if thinking_part:
                                response = StreamResponse(content=thinking_part, done=False, type="thinking")
                                yield f"data: {json.dumps(response.model_dump())}\n\n"
                            
                            thinking_sent = True
                            in_thinking = False
                            
                            # 发送 thinking 后的内容
                            if len(parts) > 1:
                                response_part = parts[1]
                                if response_part.strip():
                                    response_content += response_part
                                    response = StreamResponse(content=response_part, done=False, type="response")
                                    yield f"data: {json.dumps(response.model_dump())}\n\n"
                        elif in_thinking:
                            # 在 thinking 中
                            thinking_content += chunk
                            response = StreamResponse(content=chunk, done=False, type="thinking")
                            yield f"data: {json.dumps(response.model_dump())}\n\n"
                        else:
                            # 普通回复内容
                            response_content += chunk
                            response = StreamResponse(content=chunk, done=False, type="response")
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
