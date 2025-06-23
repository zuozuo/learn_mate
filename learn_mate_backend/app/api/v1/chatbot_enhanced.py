"""Enhanced chatbot endpoints with improved streaming diagnostics."""

import json
import time
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.schemas.chat import ChatRequest, StreamResponse

router = APIRouter()
agent = LangGraphAgent()


@router.post("/chat/stream/enhanced")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])
async def chat_stream_enhanced(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """Enhanced streaming endpoint with detailed diagnostics."""
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate streaming events with diagnostics."""
        chunk_count = 0
        total_chars = 0
        start_time = time.time()
        
        try:
            logger.info(
                "enhanced_stream_start",
                session_id=session.id,
                message_count=len(chat_request.messages)
            )
            
            async for chunk in agent.get_stream_response(
                chat_request.messages, session.id, user_id=session.user_id
            ):
                chunk_count += 1
                total_chars += len(chunk)
                
                # Log every 10th chunk for monitoring
                if chunk_count % 10 == 0:
                    logger.debug(
                        "stream_progress",
                        session_id=session.id,
                        chunks_sent=chunk_count,
                        total_chars=total_chars,
                        elapsed=time.time() - start_time
                    )
                
                # Send the chunk
                response = StreamResponse(content=chunk, done=False)
                yield f"data: {json.dumps(response.model_dump())}\n\n"
            
            # Send completion event
            elapsed = time.time() - start_time
            logger.info(
                "enhanced_stream_complete",
                session_id=session.id,
                total_chunks=chunk_count,
                total_chars=total_chars,
                duration=elapsed,
                avg_chunk_size=total_chars/chunk_count if chunk_count > 0 else 0,
                chunks_per_second=chunk_count/elapsed if elapsed > 0 else 0
            )
            
            final_response = StreamResponse(content="", done=True)
            yield f"data: {json.dumps(final_response.model_dump())}\n\n"
            
        except Exception as e:
            logger.error(
                "enhanced_stream_error",
                session_id=session.id,
                error=str(e),
                chunks_before_error=chunk_count,
                exc_info=True
            )
            error_response = StreamResponse(content=str(e), done=True)
            yield f"data: {json.dumps(error_response.model_dump())}\n\n"
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )


@router.get("/streaming/test")
async def test_streaming():
    """Test endpoint to verify streaming is working."""
    
    async def generate():
        """Generate test stream."""
        for i in range(10):
            yield f"data: {json.dumps({'count': i, 'time': time.time()})}\n\n"
            await asyncio.sleep(0.1)  # Small delay between chunks
    
    import asyncio
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )