"""Enhanced chat service that integrates with conversation management."""

from typing import Optional, AsyncGenerator, List
from uuid import UUID

from sqlmodel import Session

from app.models.chat_message import MessageRole
from app.services.conversation_service import ConversationService
from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.core.logging import logger


class EnhancedChatService:
    """Enhanced chat service that saves messages to conversations."""

    def __init__(self, session: Session):
        """Initialize service with database session.

        Args:
            session: SQLModel database session
        """
        self.session = session
        self.conversation_service = ConversationService(session)
        self.agent = LangGraphAgent()

    async def send_message(self, conversation_id: UUID, user_id: int, content: str) -> Message:
        """Send a message and get AI response.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user
            content: Message content

        Returns:
            AI response message
        """
        # Save user message
        user_message = await self.conversation_service.add_message(
            conversation_id=conversation_id, user_id=user_id, role=MessageRole.USER, content=content
        )

        if not user_message:
            raise ValueError("Unauthorized access to conversation")

        # Get conversation history
        conv_with_messages = await self.conversation_service.get_conversation_with_messages(conversation_id, user_id)

        # Convert to Message format for agent
        messages = []
        for msg in conv_with_messages["messages"]:
            messages.append(Message(role=msg["role"], content=msg["content"]))

        # Get AI response
        session_id = str(conversation_id)  # Use conversation ID as session ID
        response_messages = await self.agent.get_response(messages, session_id, str(user_id))

        # Extract the assistant's response
        assistant_response = None
        for msg in response_messages:
            if msg["role"] == "assistant":
                assistant_response = msg
                break

        if not assistant_response:
            raise ValueError("No assistant response generated")

        # Save assistant message with thinking if present
        thinking_content = None
        # Check if there's thinking content in the response
        # This would need to be extracted from the response format

        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=MessageRole.ASSISTANT,
            content=assistant_response["content"],
            thinking=thinking_content,
        )

        return Message(role=assistant_response["role"], content=assistant_response["content"])

    async def send_message_stream(
        self, conversation_id: UUID, user_id: int, content: str
    ) -> AsyncGenerator[str, None]:
        """Send a message and get streaming AI response.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user
            content: Message content

        Yields:
            Chunks of AI response
        """
        # Save user message
        user_message = await self.conversation_service.add_message(
            conversation_id=conversation_id, user_id=user_id, role=MessageRole.USER, content=content
        )

        if not user_message:
            raise ValueError("Unauthorized access to conversation")

        # Get conversation history
        conv_with_messages = await self.conversation_service.get_conversation_with_messages(conversation_id, user_id)

        # Convert to Message format for agent
        messages = []
        for msg in conv_with_messages["messages"]:
            messages.append(Message(role=msg["role"], content=msg["content"]))

        # Stream AI response
        session_id = str(conversation_id)  # Use conversation ID as session ID
        accumulated_content = ""
        thinking_content = ""

        async for chunk in self.agent.get_stream_response(messages, session_id, str(user_id)):
            accumulated_content += chunk

            # Parse for thinking tags
            if "<think>" in chunk and "</think>" in chunk:
                # Extract thinking content
                if "<think>" in accumulated_content and "</think>" in accumulated_content:
                    start = accumulated_content.find("<think>") + 7
                    end = accumulated_content.find("</think>")
                    thinking_content = accumulated_content[start:end]

            yield chunk

        # Save complete assistant message after streaming
        # Extract clean content without thinking tags
        clean_content = accumulated_content
        if thinking_content:
            clean_content = accumulated_content.replace(f"<think>{thinking_content}</think>", "").strip()

        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=MessageRole.ASSISTANT,
            content=clean_content,
            thinking=thinking_content if thinking_content else None,
        )

    async def create_temporary_conversation(self, user_id: int, first_message: str) -> UUID:
        """Create a temporary conversation for legacy endpoints.

        Args:
            user_id: ID of the user
            first_message: First message content

        Returns:
            ID of created conversation
        """
        conversation = await self.conversation_service.create_conversation(
            user_id=user_id, title="Temporary Chat", first_message=first_message
        )

        return conversation.id
