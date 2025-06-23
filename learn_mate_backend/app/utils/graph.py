"""This file contains the graph utilities for the application."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import trim_messages as _trim_messages

from app.core.config import settings
from app.schemas import Message


def dump_messages(messages: list[Message]) -> list[dict]:
    """Dump the messages to a list of dictionaries.

    Args:
        messages (list[Message]): The messages to dump.

    Returns:
        list[dict]: The dumped messages.
    """
    return [message.model_dump() for message in messages]


def prepare_messages(messages: list[Message], llm: BaseChatModel, system_prompt: str) -> list[Message]:
    """Prepare the messages for the LLM.

    Args:
        messages (list[Message]): The messages to prepare.
        llm (BaseChatModel): The LLM to use.
        system_prompt (str): The system prompt to use.

    Returns:
        list[Message]: The prepared messages.
    """
    # 对于 Ollama，使用简单的字符数限制避免 token 计数问题
    if "ollama" in settings.LLM_PROVIDER.lower():
        # 简单的消息裁剪，保留最近的几条消息
        max_messages = 10  # 最多保留10条历史消息
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        
        return [Message(role="system", content=system_prompt)] + messages
    else:
        # 对于其他提供商，使用原来的 token 计数方法
        try:
            trimmed_messages = _trim_messages(
                dump_messages(messages),
                strategy="last",
                token_counter=llm,
                max_tokens=settings.MAX_TOKENS,
                start_on="human",
                include_system=False,
                allow_partial=False,
            )
            return [Message(role="system", content=system_prompt)] + trimmed_messages
        except Exception as e:
            # 如果 token 计数失败，回退到简单方法
            max_messages = 5
            if len(messages) > max_messages:
                messages = messages[-max_messages:]
            return [Message(role="system", content=system_prompt)] + messages
