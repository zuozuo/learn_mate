"""Pytest configuration and fixtures for all tests."""

import asyncio
import os
import sys
import pytest
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, UTC
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

# Mock PostgreSQL dependencies before importing app
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg_c'] = MagicMock()
sys.modules['langgraph.checkpoint.postgres.aio'] = MagicMock()

# Mock langchain and ollama dependencies to avoid import issues
sys.modules['langchain_ollama'] = MagicMock()
sys.modules['ollama'] = MagicMock()
sys.modules['langchain_openai'] = MagicMock()
sys.modules['langgraph.graph'] = MagicMock()
sys.modules['langgraph.graph.state'] = MagicMock()
sys.modules['langgraph.graph.message'] = MagicMock()
sys.modules['langgraph.types'] = MagicMock()

# Mock add_messages function
def mock_add_messages(existing, new):
    return existing + new

sys.modules['langgraph.graph.message'].add_messages = mock_add_messages

# Mock the ChatOllama class
class MockChatOllama:
    def __init__(self, *args, **kwargs):
        pass
    
    def bind_tools(self, tools):
        return self
    
    async def ainvoke(self, *args, **kwargs):
        return MagicMock(content="Test response")
    
    def invoke(self, *args, **kwargs):
        return MagicMock(content="Test response")

sys.modules['langchain_ollama'].ChatOllama = MockChatOllama
sys.modules['langchain_openai'].ChatOpenAI = MockChatOllama  # Use same mock for ChatOpenAI

# Create a mock AsyncPostgresSaver
class MockAsyncPostgresSaver:
    def __init__(self, *args, **kwargs):
        pass
    
    async def setup(self):
        pass

# Replace the import
sys.modules['langgraph.checkpoint.postgres.aio'].AsyncPostgresSaver = MockAsyncPostgresSaver

# Mock psycopg_pool
sys.modules['psycopg_pool'] = MagicMock()
class MockAsyncConnectionPool:
    def __init__(self, *args, **kwargs):
        pass
    
    async def connection(self):
        return MagicMock()
    
    async def close(self):
        pass
    
    async def open(self):
        pass

sys.modules['psycopg_pool'].AsyncConnectionPool = MockAsyncConnectionPool

from app.main import app
from app.services.database import database_service
from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage, MessageRole
from app.utils.auth import create_access_token


# Create in-memory SQLite database for testing
@pytest.fixture(name="engine", scope="function")
def engine_fixture():
    """Create a test database engine for each test."""
    engine = create_engine(
        "sqlite:///:memory:",  # In-memory database
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    # Use autocommit mode to avoid transaction isolation issues in tests
    with Session(engine, autocommit=False, autoflush=False) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session, monkeypatch) -> Generator[TestClient, None, None]:
    """Create a test client with overridden dependencies."""
    # Mock database service methods
    monkeypatch.setattr(database_service, "engine", session.bind)
    
    # Disable triggers for test database
    monkeypatch.setattr(database_service, "_create_triggers", lambda: None)
    
    def get_session_override():
        return session

    # Override the database session
    old_get_session_maker = database_service.get_session_maker
    database_service.get_session_maker = get_session_override
    
    # Mock the LangGraph agent initialization
    import app.core.langgraph.graph
    
    # Create a mock LangGraphAgent class
    class MockLangGraphAgent:
        def __init__(self):
            self.llm = MockChatOllama()
            self.llm_with_tools = MockChatOllama()
            self.tools_by_name = {}
            self._connection_pool = None
            self._graph = None
        
        async def _get_connection_pool(self):
            return MockAsyncConnectionPool()
        
        async def create_graph(self):
            return MagicMock()
        
        async def get_response(self, messages, session_id, user_id):
            return [{"role": "assistant", "content": "Test response"}]
        
        async def get_stream_response(self, messages, session_id, user_id):
            chunks = ["This ", "is ", "a ", "test ", "response"]
            for chunk in chunks:
                yield chunk
    
    # Replace the LangGraphAgent class
    monkeypatch.setattr(app.core.langgraph.graph, "LangGraphAgent", MockLangGraphAgent)
    
    from app.main import app as fastapi_app
    client = TestClient(fastapi_app)
    yield client
    
    # Restore
    database_service.get_session_maker = old_get_session_maker
    # Clear any overrides if the app instance has them
    if hasattr(fastapi_app, 'dependency_overrides'):
        fastapi_app.dependency_overrides.clear()


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