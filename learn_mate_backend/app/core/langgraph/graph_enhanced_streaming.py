"""Enhanced streaming implementation for LangGraph with proper token-level streaming."""

from typing import AsyncGenerator, Optional
from app.core.logging import logger
from app.schemas import Message
from app.utils import dump_messages


async def get_stream_response_enhanced(
    self, messages: list[Message], session_id: str, user_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Enhanced stream response with proper token-level streaming.

    This implementation uses stream_mode="messages" which is specifically designed
    for streaming LLM tokens, unlike the original implementation that may have
    bundled the entire response.

    Args:
        self: The instance of the class.
        messages: The messages to send to the LLM.
        session_id: The session ID for the conversation.
        user_id: The user ID for the conversation.

    Yields:
        str: Individual tokens from the LLM response.
    """
    config = {
        "configurable": {"thread_id": session_id},
    }

    if self._graph is None:
        self._graph = await self.create_graph()

    token_count = 0
    accumulated_content = ""

    try:
        # Use stream_mode="messages" for token-level streaming
        async for msg, metadata in self._graph.astream(
            {"messages": dump_messages(messages), "session_id": session_id}, config, stream_mode="messages"
        ):
            # Filter to only process LLM outputs from the chat node
            if metadata.get("langgraph_node") == "chat":
                # msg should contain the token content
                if hasattr(msg, "content") and msg.content:
                    token_count += 1
                    token = msg.content
                    accumulated_content += token

                    logger.debug(
                        "streaming_token",
                        session_id=session_id,
                        token_number=token_count,
                        token_content=repr(token[:20]) if len(token) > 20 else repr(token),
                        metadata_tags=metadata.get("tags", []),
                        langgraph_node=metadata.get("langgraph_node"),
                    )

                    yield token

        logger.info(
            "streaming_completed",
            session_id=session_id,
            total_tokens=token_count,
            total_content_length=len(accumulated_content),
            content_preview=accumulated_content[:100] + "..."
            if len(accumulated_content) > 100
            else accumulated_content,
        )

    except Exception as e:
        logger.error(
            "stream_processing_error",
            error=str(e),
            session_id=session_id,
            tokens_before_error=token_count,
            exc_info=True,
        )
        raise e


async def get_multi_stream_response(
    self, messages: list[Message], session_id: str, user_id: Optional[str] = None
) -> AsyncGenerator[tuple[str, any], None]:
    """Stream multiple types of data simultaneously.

    This implementation demonstrates how to use multiple stream modes
    to get both token streaming and state updates.

    Yields:
        tuple: (stream_mode, data) where stream_mode indicates the type of data
    """
    config = {
        "configurable": {"thread_id": session_id},
    }

    if self._graph is None:
        self._graph = await self.create_graph()

    try:
        # Stream both messages (tokens) and updates (state changes)
        async for stream_mode, data in self._graph.astream(
            {"messages": dump_messages(messages), "session_id": session_id},
            config,
            stream_mode=["messages", "updates"],
        ):
            if stream_mode == "messages":
                # Handle token streaming
                msg, metadata = data
                if metadata.get("langgraph_node") == "chat" and hasattr(msg, "content") and msg.content:
                    yield ("token", msg.content)

            elif stream_mode == "updates":
                # Handle state updates
                logger.debug("state_update", session_id=session_id, update_data=str(data)[:200])
                yield ("update", data)

    except Exception as e:
        logger.error("multi_stream_error", error=str(e), session_id=session_id, exc_info=True)
        raise e
