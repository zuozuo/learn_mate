"""Direct LLM streaming implementation bypassing LangGraph limitations."""

from typing import AsyncGenerator, Optional, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from app.core.logging import logger
from app.schemas import Message


async def get_direct_stream_response(
    self, messages: list[Message], session_id: str, user_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Direct streaming from LLM, bypassing LangGraph's message-level limitation.
    
    This implementation:
    1. Converts messages to LangChain format
    2. Streams directly from the LLM
    3. Manually saves to chat history afterward
    
    Args:
        messages: The messages to send to the LLM
        session_id: The session ID for the conversation
        user_id: The user ID for the conversation
        
    Yields:
        str: Individual tokens from the LLM response
    """
    from app.core.prompts import SYSTEM_PROMPT
    from app.utils import dump_messages
    
    try:
        # Convert messages to LangChain format
        langchain_messages: List[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT)
        ]
        
        for msg in messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
        
        token_count = 0
        accumulated_content = ""
        
        # Stream directly from LLM
        async for chunk in self.llm.astream(langchain_messages):
            if chunk.content:
                token_count += 1
                token = chunk.content
                accumulated_content += token
                
                logger.debug(
                    "direct_streaming_token",
                    session_id=session_id,
                    token_number=token_count,
                    token_length=len(token),
                    accumulated_length=len(accumulated_content)
                )
                
                yield token
        
        # After streaming completes, save to history via LangGraph
        if accumulated_content and self._graph:
            try:
                # Create a complete message for history
                complete_messages = messages + [
                    Message(role="assistant", content=accumulated_content)
                ]
                
                # Use non-streaming invoke to save history
                config = {"configurable": {"thread_id": session_id}}
                await self._graph.ainvoke(
                    {"messages": dump_messages(complete_messages), "session_id": session_id},
                    config
                )
                
                logger.info(
                    "streaming_history_saved",
                    session_id=session_id,
                    content_length=len(accumulated_content)
                )
            except Exception as e:
                logger.error(
                    "streaming_history_save_failed",
                    session_id=session_id,
                    error=str(e)
                )
                # Don't fail the streaming if history save fails
        
        logger.info(
            "direct_streaming_completed",
            session_id=session_id,
            total_tokens=token_count,
            total_content_length=len(accumulated_content)
        )
        
    except Exception as e:
        logger.error(
            "direct_streaming_error",
            error=str(e),
            session_id=session_id
        )
        raise e