"""Pytest configuration and fixtures for all tests."""

import asyncio
import os
import pytest
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, UTC
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

from app.main import app
from app.services.database import database_service
from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage, MessageRole
from app.utils.auth import create_access_token


# Create in-memory SQLite database for testing
@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden dependencies."""
    def get_session_override():
        return session

    # Override the database session
    app.dependency_overrides[database_service.get_session_maker] = get_session_override
    
    client = TestClient(app)
    yield client
    
    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=User.hash_password("testpassword123")
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user: User) -> dict:
    """Create authentication headers for test user."""
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token.access_token}"}


@pytest.fixture(name="test_conversation")
def test_conversation_fixture(session: Session, test_user: User) -> Conversation:
    """Create a test conversation."""
    conversation = Conversation(
        user_id=test_user.id,
        title="Test Conversation",
        summary="A test conversation for unit tests"
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@pytest.fixture(name="test_messages")
def test_messages_fixture(
    session: Session, 
    test_conversation: Conversation
) -> list[ChatMessage]:
    """Create test messages in a conversation."""
    messages = [
        ChatMessage(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Hello, how are you?",
            message_index=0
        ),
        ChatMessage(
            conversation_id=test_conversation.id,
            role=MessageRole.ASSISTANT,
            content="I'm doing well, thank you! How can I help you today?",
            thinking="<think>The user is greeting me. I should respond politely.</think>",
            message_index=1
        ),
        ChatMessage(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Can you explain Python decorators?",
            message_index=2
        ),
    ]
    
    for message in messages:
        session.add(message)
    
    session.commit()
    
    for message in messages:
        session.refresh(message)
    
    return messages


@pytest.fixture(name="mock_langgraph_agent")
def mock_langgraph_agent_fixture(monkeypatch):
    """Mock the LangGraph agent for testing."""
    mock_agent = MagicMock()
    
    # Mock get_response method
    async def mock_get_response(messages, session_id, user_id):
        return [
            {"role": "assistant", "content": "This is a test response"}
        ]
    
    # Mock get_stream_response method
    async def mock_get_stream_response(messages, session_id, user_id):
        chunks = ["This ", "is ", "a ", "streaming ", "test ", "response"]
        for chunk in chunks:
            yield chunk
    
    mock_agent.get_response = AsyncMock(side_effect=mock_get_response)
    mock_agent.get_stream_response = mock_get_stream_response
    
    # Patch the agent in the modules that use it
    monkeypatch.setattr("app.api.v1.chatbot.agent", mock_agent)
    monkeypatch.setattr("app.services.enhanced_chat_service.LangGraphAgent", lambda: mock_agent)
    
    return mock_agent


@pytest.fixture(name="mock_conversation_service")
def mock_conversation_service_fixture(monkeypatch):
    """Mock the conversation service for isolated testing."""
    mock_service = MagicMock()
    
    # Mock methods as needed
    mock_service.create_conversation = AsyncMock(
        return_value=Conversation(
            id=uuid4(),
            user_id=1,
            title="New Conversation",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
    )
    
    return mock_service


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test data fixtures
@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "title": "Sample Conversation",
        "first_message": "Hello, this is a test message"
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "messages": [
            {"role": "user", "content": "What is Python?"}
        ]
    }