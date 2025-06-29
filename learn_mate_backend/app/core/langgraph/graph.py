"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Literal,
    Optional,
)

from asgiref.sync import sync_to_async
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import (
    END,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from openai import OpenAIError
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.tools import tools
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.prompts import SYSTEM_PROMPT
from app.schemas import (
    GraphState,
    Message,
)
from app.utils import (
    dump_messages,
    prepare_messages,
)


class LangGraphAgent:
    """Manages the LangGraph Agent/workflow and interactions with the LLM.

    This class handles the creation and management of the LangGraph workflow,
    including LLM interactions, database connections, and response processing.
    """

    def __init__(self):
        """Initialize the LangGraph Agent with necessary components."""
        # Use environment-specific LLM model with provider support
        # NOTE: 不在初始化时绑定工具，避免流式响应问题
        # 参考: https://github.com/langchain-ai/langchain/issues/26971
        self.llm = self._create_llm()
        self.llm_with_tools = self._create_llm().bind_tools(tools)
        self.tools_by_name = {tool.name: tool for tool in tools}
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None

        logger.info(
            "llm_initialized",
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            environment=settings.ENVIRONMENT.value,
        )

    def _create_llm(self):
        """Create LLM instance based on the configured provider.

        Returns:
            Configured LLM instance (ChatOpenAI, ChatOllama, etc.)
        """
        provider = settings.LLM_PROVIDER.lower()
        model_kwargs = self._get_model_kwargs()

        if provider == "openai":
            return ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.LLM_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
                streaming=True,  # 启用流式传输
                **model_kwargs,
            )

        elif provider == "openrouter":
            return ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.OPENROUTER_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                base_url=settings.OPENROUTER_BASE_URL,
                streaming=True,  # 启用流式传输
                default_headers={"HTTP-Referer": "https://learn-mate.ai", "X-Title": "Learn Mate"},
                **model_kwargs,
            )

        elif provider == "ollama":
            # Ollama doesn't use API keys and has different parameter structure
            ollama_kwargs = {
                "model": settings.LLM_MODEL,
                "temperature": settings.DEFAULT_LLM_TEMPERATURE,
                "base_url": settings.OLLAMA_BASE_URL,
            }
            # Note: Ollama may not support all OpenAI parameters
            if "max_tokens" in model_kwargs:
                ollama_kwargs["num_predict"] = settings.MAX_TOKENS

            return ChatOllama(**ollama_kwargs)

        else:
            logger.warning(f"Unknown LLM provider: {provider}, falling back to OpenAI")
            return ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.LLM_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                streaming=True,  # 启用流式传输
                **model_kwargs,
            )

    def _get_model_kwargs(self) -> Dict[str, Any]:
        """Get environment-specific model kwargs.

        Returns:
            Dict[str, Any]: Additional model arguments based on environment
        """
        model_kwargs = {}

        # Development - we can use lower speeds for cost savings
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            model_kwargs["top_p"] = 0.8

        # Production - use higher quality settings
        elif settings.ENVIRONMENT == Environment.PRODUCTION:
            model_kwargs["top_p"] = 0.95
            model_kwargs["presence_penalty"] = 0.1
            model_kwargs["frequency_penalty"] = 0.1

        return model_kwargs

    def _get_model_name(self) -> str:
        """Get model name from LLM instance, compatible with different providers.

        Returns:
            str: The model name for metrics and logging
        """
        # Try different attribute names based on LLM provider
        if hasattr(self.llm, "model_name"):
            return self.llm.model_name
        elif hasattr(self.llm, "model"):
            return self.llm.model
        else:
            # Fallback to configured model name
            return settings.LLM_MODEL

    async def _get_connection_pool(self) -> AsyncConnectionPool:
        """Get a PostgreSQL connection pool using environment-specific settings.

        Returns:
            AsyncConnectionPool: A connection pool for PostgreSQL database.
        """
        if self._connection_pool is None:
            try:
                # Configure pool size based on environment
                max_size = settings.POSTGRES_POOL_SIZE

                self._connection_pool = AsyncConnectionPool(
                    settings.POSTGRES_URL,
                    open=False,
                    max_size=max_size,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                        "prepare_threshold": None,
                    },
                )
                await self._connection_pool.open()
                logger.info("connection_pool_created", max_size=max_size, environment=settings.ENVIRONMENT.value)
            except Exception as e:
                logger.error("connection_pool_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we might want to degrade gracefully
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_connection_pool", environment=settings.ENVIRONMENT.value)
                    return None
                raise e
        return self._connection_pool

    async def _chat(self, state: GraphState) -> dict:
        """Process the chat state and generate a response.

        Args:
            state (GraphState): The current state of the conversation.

        Returns:
            dict: Updated state with new messages.
        """
        messages = prepare_messages(state.messages, self.llm, SYSTEM_PROMPT)

        llm_calls_num = 0

        # Configure retry attempts based on environment
        max_retries = settings.MAX_LLM_CALL_RETRIES

        for attempt in range(max_retries):
            try:
                with llm_inference_duration_seconds.labels(model=self._get_model_name()).time():
                    # 使用带工具的 LLM 进行推理
                    generated_state = {"messages": [await self.llm_with_tools.ainvoke(dump_messages(messages))]}
                logger.info(
                    "llm_response_generated",
                    session_id=state.session_id,
                    llm_calls_num=llm_calls_num + 1,
                    model=settings.LLM_MODEL,
                    environment=settings.ENVIRONMENT.value,
                )
                return generated_state
            except OpenAIError as e:
                logger.error(
                    "llm_call_failed",
                    llm_calls_num=llm_calls_num,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    environment=settings.ENVIRONMENT.value,
                )
                llm_calls_num += 1

                # In production, we might want to fall back to a more reliable model
                if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
                    fallback_model = "gpt-4o"
                    logger.warning(
                        "using_fallback_model", model=fallback_model, environment=settings.ENVIRONMENT.value
                    )
                    # Update model name based on LLM provider
                    if hasattr(self.llm, "model_name"):
                        self.llm.model_name = fallback_model
                    elif hasattr(self.llm, "model"):
                        self.llm.model = fallback_model

                continue

        raise Exception(f"Failed to get a response from the LLM after {max_retries} attempts")

    # Define our tool node
    async def _tool_call(self, state: GraphState) -> GraphState:
        """Process tool calls from the last message.

        Args:
            state: The current agent state containing messages and tool calls.

        Returns:
            Dict with updated messages containing tool responses.
        """
        outputs = []
        for tool_call in state.messages[-1].tool_calls:
            tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

    def _should_continue(self, state: GraphState) -> Literal["end", "continue"]:
        """Determine if the agent should continue or end based on the last message.

        Args:
            state: The current agent state containing messages.

        Returns:
            Literal["end", "continue"]: "end" if there are no tool calls, "continue" otherwise.
        """
        messages = state.messages
        last_message = messages[-1]
        # If there is no function call, then we finish
        if not last_message.tool_calls:
            return "end"
        # Otherwise if there is, we continue
        else:
            return "continue"

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """Create and configure the LangGraph workflow.

        Returns:
            Optional[CompiledStateGraph]: The configured LangGraph instance or None if init fails
        """
        if self._graph is None:
            try:
                graph_builder = StateGraph(GraphState)
                graph_builder.add_node("chat", self._chat)
                graph_builder.add_node("tool_call", self._tool_call)
                graph_builder.add_conditional_edges(
                    "chat",
                    self._should_continue,
                    {"continue": "tool_call", "end": END},
                )
                graph_builder.add_edge("tool_call", "chat")
                graph_builder.set_entry_point("chat")
                graph_builder.set_finish_point("chat")

                # Get connection pool (may be None in production if DB unavailable)
                connection_pool = await self._get_connection_pool()
                if connection_pool:
                    checkpointer = AsyncPostgresSaver(connection_pool)
                    await checkpointer.setup()
                else:
                    # In production, proceed without checkpointer if needed
                    checkpointer = None
                    if settings.ENVIRONMENT != Environment.PRODUCTION:
                        raise Exception("Connection pool initialization failed")

                self._graph = graph_builder.compile(
                    checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent ({settings.ENVIRONMENT.value})"
                )

                logger.info(
                    "graph_created",
                    graph_name=f"{settings.PROJECT_NAME} Agent",
                    environment=settings.ENVIRONMENT.value,
                    has_checkpointer=checkpointer is not None,
                )
            except Exception as e:
                logger.error("graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we don't want to crash the app
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_graph")
                    return None
                raise e

        return self._graph

    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get a response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for Langfuse tracking.
            user_id (Optional[str]): The user ID for Langfuse tracking.

        Returns:
            list[dict]: The response from the LLM.
        """
        if self._graph is None:
            self._graph = await self.create_graph()
        config = {
            "configurable": {"thread_id": session_id},
        }
        try:
            response = await self._graph.ainvoke(
                {"messages": dump_messages(messages), "session_id": session_id}, config
            )
            return self.__process_messages(response["messages"])
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            raise e

    async def get_stream_response(
        self, messages: list[Message], session_id: str, user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Get a stream response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for the conversation.
            user_id (Optional[str]): The user ID for the conversation.

        Yields:
            str: Tokens of the LLM response.
        """
        # 直接使用不带工具的 LLM 进行流式响应，避免 bind_tools 导致的流式失效
        # 参考: https://github.com/langchain-ai/langchain/issues/26971
        from app.core.prompts import SYSTEM_PROMPT
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        try:
            # 转换消息格式
            langchain_messages = [SystemMessage(content=SYSTEM_PROMPT)]
            for msg in messages:
                if msg.role == "user":
                    langchain_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    langchain_messages.append(AIMessage(content=msg.content))

            token_count = 0
            accumulated_content = ""

            # 使用不带工具的 LLM 直接流式
            async for chunk in self.llm.astream(langchain_messages):
                if chunk.content:
                    token_count += 1
                    content = chunk.content
                    accumulated_content += content

                    logger.debug(
                        "streaming_token",
                        session_id=session_id,
                        token_number=token_count,
                        token_length=len(content),
                        accumulated_length=len(accumulated_content),
                    )

                    yield content

            # 流式完成后，保存到历史记录
            if accumulated_content and self._graph:
                try:
                    # 将完整的对话保存到 LangGraph 历史
                    complete_messages = messages + [Message(role="assistant", content=accumulated_content)]
                    config = {"configurable": {"thread_id": session_id}}

                    # 使用 invoke（非流式）来保存历史，这会通过 _chat 方法
                    await self._graph.ainvoke(
                        {"messages": dump_messages(complete_messages), "session_id": session_id}, config
                    )

                    logger.info(
                        "streaming_history_saved", session_id=session_id, content_length=len(accumulated_content)
                    )
                except Exception as e:
                    logger.error("streaming_history_save_failed", session_id=session_id, error=str(e))
                    # 历史保存失败不影响流式响应

            logger.info(
                "streaming_completed",
                session_id=session_id,
                total_tokens=token_count,
                total_content_length=len(accumulated_content),
            )

        except Exception as stream_error:
            logger.error("Error in stream processing", error=str(stream_error), session_id=session_id)
            raise stream_error

    async def get_chat_history(self, session_id: str) -> list[Message]:
        """Get the chat history for a given thread ID.

        Args:
            session_id (str): The session ID for the conversation.

        Returns:
            list[Message]: The chat history.
        """
        if self._graph is None:
            self._graph = await self.create_graph()

        state: StateSnapshot = await sync_to_async(self._graph.get_state)(
            config={"configurable": {"thread_id": session_id}}
        )
        return self.__process_messages(state.values["messages"]) if state.values else []

    def __process_messages(self, messages: list[BaseMessage]) -> list[Message]:
        openai_style_messages = convert_to_openai_messages(messages)
        # keep just assistant and user messages
        return [
            Message(**message)
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]

    async def clear_chat_history(self, session_id: str) -> None:
        """Clear all chat history for a given thread ID.

        Args:
            session_id: The ID of the session to clear history for.

        Raises:
            Exception: If there's an error clearing the chat history.
        """
        try:
            # Make sure the pool is initialized in the current event loop
            conn_pool = await self._get_connection_pool()

            # Use a new connection for this specific operation
            async with conn_pool.connection() as conn:
                for table in settings.CHECKPOINT_TABLES:
                    try:
                        await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (session_id,))
                        logger.info(f"Cleared {table} for session {session_id}")
                    except Exception as e:
                        logger.error(f"Error clearing {table}", error=str(e))
                        raise

        except Exception as e:
            logger.error("Failed to clear chat history", error=str(e))
            raise
