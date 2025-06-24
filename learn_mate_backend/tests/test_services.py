"""Tests for service layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from sqlmodel import Session

from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage, MessageRole
from app.services.conversation_service import ConversationService
from app.services.enhanced_chat_service import EnhancedChatService


class TestConversationService:
    """Test suite for ConversationService."""

    @pytest.mark.asyncio
    async def test_create_conversation_without_message(self, session: Session, test_user: User):
        """Test creating a conversation without initial message."""
        service = ConversationService(session)

        conversation = await service.create_conversation(user_id=test_user.id, title="Test Conversation")

        assert conversation.title == "Test Conversation"
        assert conversation.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_conversation_with_first_message(self, session: Session, test_user: User):
        """Test creating a conversation with initial message."""
        service = ConversationService(session)

        conversation = await service.create_conversation(
            user_id=test_user.id, title=None, first_message="Hello, world!"
        )

        # Should auto-generate title from message
        assert conversation.title == "Hello, world!"

        # Verify message was created
        messages = session.query(ChatMessage).filter(ChatMessage.conversation_id == conversation.id).all()

        assert len(messages) == 1
        assert messages[0].content == "Hello, world!"
        assert messages[0].role == MessageRole.USER

    @pytest.mark.asyncio
    async def test_auto_title_generation(self, session: Session, test_user: User):
        """Test automatic title generation from long message."""
        service = ConversationService(session)

        long_message = "This is a very long message that should be truncated for the title " * 5

        conversation = await service.create_conversation(user_id=test_user.id, first_message=long_message)

        # Title should be truncated
        assert len(conversation.title) <= 53  # 50 + "..."
        assert conversation.title.endswith("...")

    @pytest.mark.asyncio
    async def test_get_conversations_with_message_count(self, session: Session, test_user: User):
        """Test retrieving conversations with message counts."""
        service = ConversationService(session)

        # Create conversation
        conversation = await service.create_conversation(user_id=test_user.id, title="Test")

        # Add messages
        for i in range(3):
            await service.add_message(
                conversation_id=conversation.id, user_id=test_user.id, role=MessageRole.USER, content=f"Message {i}"
            )

        # Get conversations
        conversations, total = await service.get_conversations(user_id=test_user.id)

        assert total >= 1
        conv_dict = next(c for c in conversations if c["id"] == conversation.id)
        assert conv_dict["message_count"] == 3

    @pytest.mark.asyncio
    async def test_get_conversation_with_messages(
        self, session: Session, test_user: User, test_conversation: Conversation, test_messages: list[ChatMessage]
    ):
        """Test retrieving conversation with all messages."""
        service = ConversationService(session)

        result = await service.get_conversation_with_messages(
            conversation_id=test_conversation.id, user_id=test_user.id
        )

        assert result is not None
        assert result["id"] == test_conversation.id
        assert result["title"] == test_conversation.title
        assert len(result["messages"]) == len(test_messages)

        # Verify message order
        for i, msg in enumerate(result["messages"]):
            assert msg["content"] == test_messages[i].content

    @pytest.mark.asyncio
    async def test_add_message_with_authorization(
        self, session: Session, test_user: User, test_conversation: Conversation
    ):
        """Test adding message with proper authorization."""
        service = ConversationService(session)

        message = await service.add_message(
            conversation_id=test_conversation.id,
            user_id=test_user.id,
            role=MessageRole.USER,
            content="Authorized message",
        )

        assert message is not None
        assert message.content == "Authorized message"

    @pytest.mark.asyncio
    async def test_add_message_unauthorized(self, session: Session, test_user: User, test_conversation: Conversation):
        """Test that unauthorized users can't add messages."""
        service = ConversationService(session)

        # Create another user
        other_user = User(email="other@test.com", hashed_password="hash")
        session.add(other_user)
        session.commit()

        # Try to add message as other user
        message = await service.add_message(
            conversation_id=test_conversation.id, user_id=other_user.id, role=MessageRole.USER, content="Unauthorized"
        )

        assert message is None

    @pytest.mark.asyncio
    async def test_auto_update_title_on_first_message(self, session: Session, test_user: User):
        """Test that title auto-updates from first user message."""
        service = ConversationService(session)

        # Create conversation with default title
        conversation = await service.create_conversation(user_id=test_user.id, title="New Conversation")

        # Add first user message
        await service.add_message(
            conversation_id=conversation.id, user_id=test_user.id, role=MessageRole.USER, content="What is Python?"
        )

        # Refresh and check title
        session.refresh(conversation)
        assert conversation.title == "What is Python?"


class TestEnhancedChatService:
    """Test suite for EnhancedChatService."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, session: Session, test_user: User, mock_langgraph_agent):
        """Test sending message to a conversation."""
        service = EnhancedChatService(session)

        # Create a real conversation
        conv_service = ConversationService(session)
        conversation = await conv_service.create_conversation(user_id=test_user.id, title="Test Chat")

        # Mock the agent response
        service.agent = mock_langgraph_agent

        # Send message
        response = await service.send_message(
            conversation_id=conversation.id, user_id=test_user.id, content="Test message"
        )

        assert response.role == "assistant"
        assert response.content == "This is a test response"

        # Verify messages were saved
        messages = session.query(ChatMessage).filter(ChatMessage.conversation_id == conversation.id).all()
        assert len(messages) == 2  # User + Assistant
        assert messages[0].content == "Test message"
        assert messages[1].content == "This is a test response"

    @pytest.mark.asyncio
    async def test_send_message_stream_with_thinking(
        self, session: Session, test_user: User, test_conversation: Conversation
    ):
        """Test streaming response with thinking content."""
        service = EnhancedChatService(session)

        # Mock agent to return thinking content
        mock_agent = MagicMock()

        async def mock_stream(*args):
            yield "<think>"
            yield "I'm thinking about this"
            yield "</think>"
            yield "Here's my response"

        mock_agent.get_stream_response = mock_stream
        service.agent = mock_agent

        chunks = []
        async for chunk in service.send_message_stream(
            conversation_id=test_conversation.id, user_id=test_user.id, content="Test"
        ):
            chunks.append(chunk)

        # Verify we got all chunks
        full_content = "".join(chunks)
        assert "<think>" in full_content
        assert "I'm thinking about this" in full_content
        assert "</think>" in full_content
        assert "Here's my response" in full_content

        # Verify messages were saved with thinking
        messages = (
            session.query(ChatMessage)
            .filter(ChatMessage.conversation_id == test_conversation.id)
            .order_by(ChatMessage.message_index)
            .all()
        )

        # Find the last assistant message
        assistant_msg = messages[-1]
        assert assistant_msg.role == MessageRole.ASSISTANT
        assert assistant_msg.content == "Here's my response"
        assert assistant_msg.thinking == "I'm thinking about this"

    @pytest.mark.asyncio
    async def test_create_temporary_conversation(self, session: Session, test_user: User):
        """Test creating temporary conversation for legacy endpoints."""
        service = EnhancedChatService(session)

        conv_id = await service.create_temporary_conversation(user_id=test_user.id, first_message="Legacy message")

        assert conv_id is not None

        # Verify conversation was created
        conversation = session.query(Conversation).filter(Conversation.id == conv_id).first()

        assert conversation is not None
        assert conversation.title == "Temporary Chat"

        # Verify message was created
        messages = session.query(ChatMessage).filter(ChatMessage.conversation_id == conv_id).all()

        assert len(messages) == 1
        assert messages[0].content == "Legacy message"

    @pytest.mark.asyncio
    async def test_thinking_extraction_from_stream(
        self, session: Session, test_user: User, test_conversation: Conversation
    ):
        """Test extraction of thinking content from stream."""
        service = EnhancedChatService(session)

        # Mock complex thinking pattern
        mock_agent = MagicMock()

        async def mock_complex_stream(*args):
            yield "Let me think"
            yield "<think>First thought"
            yield " and second thought"
            yield "</think>"
            yield "The answer is 42"

        mock_agent.get_stream_response = mock_complex_stream
        service.agent = mock_agent

        chunks = []
        async for chunk in service.send_message_stream(
            conversation_id=test_conversation.id, user_id=test_user.id, content="What's the answer?"
        ):
            chunks.append(chunk)

        # Get saved messages
        messages = (
            session.query(ChatMessage)
            .filter(ChatMessage.conversation_id == test_conversation.id)
            .order_by(ChatMessage.message_index)
            .all()
        )

        # Check final assistant message
        assistant_msg = messages[-1]
        assert assistant_msg.content == "Let me thinkThe answer is 42"
        assert assistant_msg.thinking == "First thought and second thought"
