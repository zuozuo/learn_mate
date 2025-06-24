# Backup of original get_stream_response method
async def get_stream_response_original(
    self, messages: list[Message], session_id: str, user_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Original stream response implementation."""
    config = {
        "configurable": {"thread_id": session_id},
    }
    if self._graph is None:
        self._graph = await self.create_graph()

    try:
        async for msg, metadata in self._graph.astream(
            {"messages": dump_messages(messages), "session_id": session_id}, config, stream_mode="messages"
        ):
            try:
                # 只处理来自 chat 节点的消息（LLM 输出）
                if msg.content and metadata.get("langgraph_node") == "chat":
                    yield msg.content
            except Exception as token_error:
                logger.error("Error processing token", error=str(token_error), session_id=session_id)
                # Continue with next token even if current one fails
                continue
    except Exception as stream_error:
        logger.error("Error in stream processing", error=str(stream_error), session_id=session_id)
        raise stream_error
