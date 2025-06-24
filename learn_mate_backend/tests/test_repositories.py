"""Tests for repository layer."""

import pytest
from uuid import uuid4
from datetime import datetime, UTC
from sqlmodel import Session

from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage, MessageRole
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.chat_message_repository import ChatMessageRepository


class TestConversationRepository:
    """Test suite for ConversationRepository."""
    
    def test_create_conversation(self, session: Session, test_user: User):
        """Test creating a conversation."""
        repo = ConversationRepository(session)
        
        conversation = repo.create_conversation(
            user_id=test_user.id,
            title="Test Conversation"
        )
        
        assert conversation.id is not None
        assert conversation.user_id == test_user.id
        assert conversation.title == "Test Conversation"
        assert conversation.created_at is not None
        assert conversation.updated_at is not None
        assert conversation.is_deleted is False
    
    def test_get_conversations_by_user(
        self, 
        session: Session, 
        test_user: User
    ):
        """Test retrieving user's conversations."""
        repo = ConversationRepository(session)
        
        # Create multiple conversations
        for i in range(5):
            repo.create_conversation(
                user_id=test_user.id,
                title=f"Conversation {i}"
            )
        
        # Test basic retrieval
        conversations, total = repo.get_conversations_by_user(
            user_id=test_user.id,
            page=1,
            limit=10
        )
        
        assert total == 5
        assert len(conversations) == 5
        
        # Test pagination
        conversations, total = repo.get_conversations_by_user(
            user_id=test_user.id,
            page=1,
            limit=2
        )
        
        assert total == 5
        assert len(conversations) == 2
    
    def test_get_conversations_with_search(
        self,
        session: Session,
        test_user: User
    ):
        """Test searching conversations."""
        repo = ConversationRepository(session)
        
        # Create conversations with different titles
        repo.create_conversation(test_user.id, "Python Tutorial")
        repo.create_conversation(test_user.id, "JavaScript Guide")
        repo.create_conversation(test_user.id, "Python Advanced Topics")
        
        # Search for Python
        conversations, total = repo.get_conversations_by_user(
            user_id=test_user.id,
            search="Python"
        )
        
        assert total == 2
        assert all("Python" in c.title for c in conversations)
    
    def test_get_conversation_by_id(
        self,
        session: Session,
        test_user: User
    ):
        """Test retrieving conversation by ID."""
        repo = ConversationRepository(session)
        
        # Create conversation
        created = repo.create_conversation(test_user.id, "Test")
        
        # Retrieve it
        retrieved = repo.get_conversation_by_id(
            conversation_id=created.id,
            user_id=test_user.id
        )
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test"
    
    def test_get_conversation_wrong_user(
        self,
        session: Session,
        test_user: User
    ):
        """Test that users can't access other users' conversations."""
        repo = ConversationRepository(session)
        
        # Create another user
        other_user = User(
            email="other@test.com",
            hashed_password="hash"
        )
        session.add(other_user)
        session.commit()
        
        # Create conversation for other user
        conversation = repo.create_conversation(other_user.id, "Private")
        
        # Try to access with test user
        retrieved = repo.get_conversation_by_id(
            conversation_id=conversation.id,
            user_id=test_user.id
        )
        
        assert retrieved is None
    
    def test_update_conversation(
        self,
        session: Session,
        test_user: User
    ):
        """Test updating a conversation."""
        repo = ConversationRepository(session)
        
        # Create conversation
        conversation = repo.create_conversation(test_user.id, "Original Title")
        original_updated_at = conversation.updated_at
        
        # Update it
        updated = repo.update_conversation(
            conversation_id=conversation.id,
            user_id=test_user.id,
            title="New Title",
            summary="New summary",
            metadata_json={"key": "value"}
        )
        
        assert updated is not None
        assert updated.title == "New Title"
        assert updated.summary == "New summary"
        assert updated.metadata_json == {"key": "value"}
        assert updated.updated_at > original_updated_at
    
    def test_soft_delete_conversation(
        self,
        session: Session,
        test_user: User
    ):
        """Test soft deleting a conversation."""
        repo = ConversationRepository(session)
        
        # Create conversation
        conversation = repo.create_conversation(test_user.id, "To Delete")
        
        # Delete it
        result = repo.soft_delete_conversation(
            conversation_id=conversation.id,
            user_id=test_user.id
        )
        
        assert result is True
        
        # Verify it's soft deleted
        session.refresh(conversation)
        assert conversation.is_deleted is True
        
        # Verify it's not returned in queries
        retrieved = repo.get_conversation_by_id(
            conversation_id=conversation.id,
            user_id=test_user.id
        )
        assert retrieved is None
    
    def test_get_message_count(
        self,
        session: Session,
        test_user: User
    ):
        """Test getting message count for a conversation."""
        # Create a fresh conversation for this test
        conversation = Conversation(
            user_id=test_user.id,
            title="Message Count Test",
            summary="Testing message count"
        )
        session.add(conversation)
        session.commit()
        
        repo = ConversationRepository(session)
        msg_repo = ChatMessageRepository(session)
        
        # Add messages
        for i in range(3):
            msg_repo.create_message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=f"Message {i}"
            )
        
        count = repo.get_message_count(conversation.id)
        assert count == 3


class TestChatMessageRepository:
    """Test suite for ChatMessageRepository."""
    
    def test_create_message(
        self,
        session: Session,
        test_conversation: Conversation
    ):
        """Test creating a message."""
        repo = ChatMessageRepository(session)
        
        message = repo.create_message(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Test message",
            thinking="Test thinking",
            metadata_json={"test": "data"}
        )
        
        assert message.id is not None
        assert message.conversation_id == test_conversation.id
        assert message.role == MessageRole.USER
        assert message.content == "Test message"
        assert message.thinking == "Test thinking"
        assert message.metadata_json == {"test": "data"}
        assert message.message_index == 0
    
    def test_message_index_auto_increment(
        self,
        session: Session,
        test_user: User
    ):
        """Test that message indexes auto-increment."""
        # Create a fresh conversation for this test
        conversation = Conversation(
            user_id=test_user.id,
            title="Auto Increment Test",
            summary="Testing message index auto increment"
        )
        session.add(conversation)
        session.commit()
        
        repo = ChatMessageRepository(session)
        
        # Create multiple messages
        messages = []
        for i in range(5):
            msg = repo.create_message(
                conversation_id=conversation.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}"
            )
            messages.append(msg)
        
        # Verify indexes
        for i, msg in enumerate(messages):
            assert msg.message_index == i
    
    def test_get_messages_by_conversation(
        self,
        session: Session,
        test_user: User
    ):
        """Test retrieving messages for a conversation."""
        # Create a fresh conversation for this test
        conversation = Conversation(
            user_id=test_user.id,
            title="Get Messages Test",
            summary="Testing message retrieval"
        )
        session.add(conversation)
        session.commit()
        
        repo = ChatMessageRepository(session)
        
        # Create messages
        for i in range(5):
            repo.create_message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=f"Message {i}"
            )
        
        # Retrieve all
        messages = repo.get_messages_by_conversation(conversation.id)
        assert len(messages) == 5
        
        # Test with limit
        messages = repo.get_messages_by_conversation(
            conversation.id,
            limit=3
        )
        assert len(messages) == 3
        
        # Test with offset
        messages = repo.get_messages_by_conversation(
            conversation.id,
            offset=2
        )
        assert len(messages) == 3
        assert messages[0].content == "Message 2"
    
    def test_bulk_create_messages(
        self,
        session: Session,
        test_user: User
    ):
        """Test bulk creating messages."""
        # Create a fresh conversation for this test
        conversation = Conversation(
            user_id=test_user.id,
            title="Bulk Create Test",
            summary="Testing bulk message creation"
        )
        session.add(conversation)
        session.commit()
        
        repo = ChatMessageRepository(session)
        
        messages_data = [
            {
                "conversation_id": conversation.id,
                "role": MessageRole.USER,
                "content": "Bulk message 1"
            },
            {
                "conversation_id": conversation.id,
                "role": MessageRole.ASSISTANT,
                "content": "Bulk response",
                "thinking": "Bulk thinking"
            },
            {
                "conversation_id": conversation.id,
                "role": MessageRole.USER,
                "content": "Bulk message 2"
            }
        ]
        
        messages = repo.bulk_create_messages(messages_data)
        
        assert len(messages) == 3
        
        # Verify indexes are sequential
        for i, msg in enumerate(messages):
            assert msg.message_index == i
        
        # Verify content
        assert messages[0].content == "Bulk message 1"
        assert messages[1].thinking == "Bulk thinking"
    
    def test_message_ordering(
        self,
        session: Session,
        test_conversation: Conversation
    ):
        """Test that messages are returned in correct order."""
        repo = ChatMessageRepository(session)
        
        # Create messages out of order
        msg2 = ChatMessage(
            conversation_id=test_conversation.id,
            role=MessageRole.ASSISTANT,
            content="Second",
            message_index=1
        )
        msg1 = ChatMessage(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="First",
            message_index=0
        )
        msg3 = ChatMessage(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Third",
            message_index=2
        )
        
        session.add(msg2)
        session.add(msg1)
        session.add(msg3)
        session.commit()
        
        # Retrieve and verify order
        messages = repo.get_messages_by_conversation(test_conversation.id)
        
        assert len(messages) == 3
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"