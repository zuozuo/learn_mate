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
sys.modules["psycopg"] = MagicMock()
sys.modules["psycopg_c"] = MagicMock()
sys.modules["langgraph.checkpoint.postgres.aio"] = MagicMock()

# Mock langchain and ollama dependencies to avoid import issues
sys.modules["langchain_ollama"] = MagicMock()
sys.modules["ollama"] = MagicMock()
sys.modules["langchain_openai"] = MagicMock()
sys.modules["langgraph.graph"] = MagicMock()
sys.modules["langgraph.graph.state"] = MagicMock()
sys.modules["langgraph.graph.message"] = MagicMock()
sys.modules["langgraph.types"] = MagicMock()


# Mock add_messages function
def mock_add_messages(existing, new):
    """Mock add_messages function."""
    return existing + new


sys.modules["langgraph.graph.message"].add_messages = mock_add_messages


# Mock the ChatOllama class
class MockChatOllama:
    """Mock ChatOllama class for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize mock ChatOllama."""
        pass

    def bind_tools(self, tools):
        """Mock bind_tools method."""
        return self

    async def ainvoke(self, *args, **kwargs):
        """Mock async invoke method."""
        return MagicMock(content="Test response")

    def invoke(self, *args, **kwargs):
        """Mock invoke method."""
        return MagicMock(content="Test response")

    async def astream(self, *args, **kwargs):
        """Mock async stream method."""
        # Mock streaming responses
        chunks = [
            MagicMock(content="This "),
            MagicMock(content="is "),
            MagicMock(content="a "),
            MagicMock(content="test "),
            MagicMock(content="response"),
        ]
        for chunk in chunks:
            yield chunk


sys.modules["langchain_ollama"].ChatOllama = MockChatOllama
sys.modules["langchain_openai"].ChatOpenAI = MockChatOllama  # Use same mock for ChatOpenAI


# Create a mock AsyncPostgresSaver
class MockAsyncPostgresSaver:
    """Mock AsyncPostgresSaver for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize mock AsyncPostgresSaver."""
        pass

    async def setup(self):
        """Mock setup method."""
        pass


# Replace the import
sys.modules["langgraph.checkpoint.postgres.aio"].AsyncPostgresSaver = MockAsyncPostgresSaver

# Mock psycopg_pool
sys.modules["psycopg_pool"] = MagicMock()


class MockAsyncConnectionPool:
    """Mock AsyncConnectionPool for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize mock AsyncConnectionPool."""
        pass

    async def connection(self):
        """Mock connection method."""
        return MagicMock()

    async def close(self):
        """Mock close method."""
        pass

    async def open(self):
        """Mock open method."""
        pass


sys.modules["psycopg_pool"].AsyncConnectionPool = MockAsyncConnectionPool

# Import app modules after mocks are set up
from app.main import app  # noqa: E402
from app.services.database import database_service  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.chat_message import ChatMessage, MessageRole  # noqa: E402
from app.models.login_history import LoginHistory  # noqa: E402
from app.utils.auth import create_access_token  # noqa: E402


# Create in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="function")
def session() -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def client(session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with the test database session."""

    def get_session_override():
        return session

    database_service.engine = engine
    app.dependency_overrides[database_service.get_session] = get_session_override

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(session: Session) -> User:
    """Create a test user."""
    # Create user with properly hashed password
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=User.hash_password("testpassword123"),
        is_active=True,
        is_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers for the test user."""
    token_obj = create_access_token(thread_id=str(test_user.id))
    token = token_obj.access_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_conversation(session: Session, test_user: User) -> Conversation:
    """Create a test conversation."""
    conversation = Conversation(
        user_id=test_user.id, title="Test Conversation", summary="Test summary", metadata_json={"test": "data"}
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@pytest.fixture
def test_messages(session: Session, test_conversation: Conversation) -> list[ChatMessage]:
    """Create test messages."""
    messages = []
    for i, (role, content) in enumerate(
        [
            (MessageRole.USER, "Hello, how are you?"),
            (MessageRole.ASSISTANT, "I'm doing well, thank you! How can I help you today?"),
            (MessageRole.USER, "What's the weather like?"),
            (MessageRole.ASSISTANT, "I'm sorry, I don't have access to weather information."),
        ]
    ):
        message = ChatMessage(
            conversation_id=test_conversation.id,
            role=role,
            content=content,
            message_index=i,
            created_at=datetime.now(UTC),
        )
        session.add(message)
        messages.append(message)

    session.commit()
    return messages


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock LangGraph service
@pytest.fixture
def mock_langgraph_service():
    """Mock the LangGraph service."""
    with patch("app.api.routes.chat.langgraph_service") as mock:
        # Mock the get_stream_response method to return an async generator
        async def mock_stream():
            responses = ["This ", "is ", "a ", "test ", "response."]
            for response in responses:
                yield response

        mock.get_stream_response.return_value = mock_stream()
        mock.process_conversation.return_value = AsyncMock(return_value="Test response")
        yield mock


# Mock database service methods
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    with patch("app.services.database.database_service.get_session") as mock:
        session_mock = MagicMock()
        session_mock.__enter__ = MagicMock(return_value=session_mock)
        session_mock.__exit__ = MagicMock(return_value=None)
        mock.return_value = session_mock
        yield session_mock


# Test data fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {"username": "newuser", "email": "newuser@example.com", "password": "StrongPassword123!"}


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {"title": "New Conversation", "metadata": {"source": "test"}}


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {"role": "user", "content": "Hello, this is a test message"}


# Mock external services
@pytest.fixture
def mock_ollama():
    """Mock Ollama service."""
    with patch("app.core.langgraph.graph.ollama") as mock:
        mock.generate.return_value = {"response": "Test response from Ollama"}
        yield mock


@pytest.fixture
def mock_openai():
    """Mock OpenAI service."""
    with patch("app.core.langgraph.graph.ChatOpenAI") as mock:
        instance = MagicMock()
        instance.ainvoke.return_value = MagicMock(content="Test response from OpenAI")
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_langgraph_agent():
    """Mock the LangGraph Agent."""
    with patch("app.services.enhanced_chat_service.LangGraphAgent") as mock_agent_class:
        # Create mock instance
        mock_instance = MagicMock()

        # Mock the stream response method
        async def mock_stream():
            responses = ["This ", "is ", "a ", "test ", "response."]
            for response in responses:
                yield response

        mock_instance.get_stream_response.return_value = mock_stream()

        # Mock the get_response method for non-streaming calls
        async def mock_get_response(*args, **kwargs):
            return [{"role": "assistant", "content": "This is a test response"}]

        mock_instance.get_response = AsyncMock(
            return_value=[{"role": "assistant", "content": "This is a test response"}]
        )

        # Make the class return our mock instance
        mock_agent_class.return_value = mock_instance

        yield mock_instance
