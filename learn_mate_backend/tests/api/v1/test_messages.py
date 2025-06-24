"""Tests for message management API endpoints."""

import pytest
import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage, MessageRole


class TestMessagesAPI:
    """Test suite for message management endpoints."""
    
    def test_send_message_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation,
        mock_langgraph_agent,
        session: Session
    ):
        """Test sending a message to a conversation."""
        message_data = {
            "messages": [{"role": "user", "content": "Hello, AI!"}]
        }
        
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/messages",
            headers=auth_headers,
            json=message_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"
        assert data["content"] == "This is a test response"
        
        # Verify messages were saved
        messages = session.query(ChatMessage).filter(
            ChatMessage.conversation_id == test_conversation.id
        ).order_by(ChatMessage.message_index).all()
        
        # Should have user message and assistant response
        assert len(messages) >= 2
        assert messages[-2].content == "Hello, AI!"
        assert messages[-2].role == MessageRole.USER
        assert messages[-1].role == MessageRole.ASSISTANT
    
    def test_send_message_no_user_content(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """Test sending message without user content."""
        message_data = {
            "messages": [{"role": "assistant", "content": "No user message"}]
        }
        
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/messages",
            headers=auth_headers,
            json=message_data
        )
        
        assert response.status_code == 400
        assert response.json()["detail"] == "No user message found"
    
    def test_send_message_unauthorized_conversation(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session
    ):
        """Test sending message to another user's conversation."""
        # Create another user's conversation
        other_user = User(
            email="other@example.com",
            hashed_password=User.hash_password("password")
        )
        session.add(other_user)
        session.commit()
        
        other_conversation = Conversation(
            user_id=other_user.id,
            title="Other's Conversation"
        )
        session.add(other_conversation)
        session.commit()
        
        message_data = {
            "messages": [{"role": "user", "content": "Unauthorized access"}]
        }
        
        response = client.post(
            f"/api/v1/conversations/{other_conversation.id}/messages",
            headers=auth_headers,
            json=message_data
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.json()["detail"]
    
    def test_send_message_conversation_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test sending message to non-existent conversation."""
        fake_id = uuid4()
        message_data = {
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = client.post(
            f"/api/v1/conversations/{fake_id}/messages",
            headers=auth_headers,
            json=message_data
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_send_message_stream_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation,
        mock_langgraph_agent
    ):
        """Test streaming message response."""
        message_data = {
            "messages": [{"role": "user", "content": "Stream this!"}]
        }
        
        with client.stream(
            "POST",
            f"/api/v1/conversations/{test_conversation.id}/messages/stream",
            headers=auth_headers,
            json=message_data
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            # Collect all chunks
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        chunks.append(data)
                    except json.JSONDecodeError:
                        pass
            
            # Verify we got chunks and completion
            assert len(chunks) > 0
            assert any(chunk.get("done") is True for chunk in chunks)
            
            # Verify content
            content_chunks = [chunk["content"] for chunk in chunks if "content" in chunk]
            assert len(content_chunks) > 0
    
    def test_send_message_stream_thinking_content(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation,
        monkeypatch
    ):
        """Test streaming with thinking content."""
        # Mock agent to return thinking content
        mock_agent = MagicMock()
        
        async def mock_stream_with_thinking(conversation_id, content, on_chunk, on_thinking):
            chunks = [
                "<think>",
                "I need to process this request",
                "</think>",
                "Here is my response"
            ]
            for chunk in chunks:
                on_chunk(chunk)
                await asyncio.sleep(0)  # Yield control
            
            # Call thinking callback
            if on_thinking:
                on_thinking("I need to process this request")
        
        from app.services import conversation_service as conv_service_module
        mock_service = MagicMock()
        mock_service.sendMessageStream = AsyncMock(side_effect=mock_stream_with_thinking)
        
        monkeypatch.setattr(conv_service_module, "conversationService", mock_service)
        
        message_data = {
            "messages": [{"role": "user", "content": "Think about this"}]
        }
        
        with client.stream(
            "POST",
            f"/api/v1/conversations/{test_conversation.id}/messages/stream",
            headers=auth_headers,
            json=message_data
        ) as response:
            assert response.status_code == 200
            
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        chunks.append(data)
                    except json.JSONDecodeError:
                        pass
            
            # Verify we got both thinking and response content
            content = "".join(chunk.get("content", "") for chunk in chunks)
            assert "<think>" in content
            assert "</think>" in content
            assert "Here is my response" in content
    
    def test_send_message_stream_error_handling(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation,
        monkeypatch
    ):
        """Test streaming error handling."""
        # Mock service to raise error
        async def mock_error_stream(*args, **kwargs):
            raise ValueError("Stream error")
        
        mock_service = MagicMock()
        mock_service.sendMessageStream = AsyncMock(side_effect=mock_error_stream)
        
        # Patch the service
        import app.services.enhanced_chat_service
        monkeypatch.setattr(
            app.services.enhanced_chat_service,
            "EnhancedChatService",
            lambda session: mock_service
        )
        
        message_data = {
            "messages": [{"role": "user", "content": "Cause an error"}]
        }
        
        with client.stream(
            "POST",
            f"/api/v1/conversations/{test_conversation.id}/messages/stream",
            headers=auth_headers,
            json=message_data
        ) as response:
            assert response.status_code == 200  # SSE always returns 200
            
            # Check error in stream
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        chunks.append(data)
                    except json.JSONDecodeError:
                        pass
            
            # Should have error chunk
            assert any(chunk.get("done") is True for chunk in chunks)
            error_chunks = [c for c in chunks if "Stream error" in c.get("content", "")]
            assert len(error_chunks) > 0
    
    def test_message_ordering(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation,
        mock_langgraph_agent,
        session: Session
    ):
        """Test that messages maintain correct order."""
        # Send multiple messages
        for i in range(3):
            message_data = {
                "messages": [{"role": "user", "content": f"Message {i}"}]
            }
            
            response = client.post(
                f"/api/v1/conversations/{test_conversation.id}/messages",
                headers=auth_headers,
                json=message_data
            )
            assert response.status_code == 200
        
        # Check message order
        messages = session.query(ChatMessage).filter(
            ChatMessage.conversation_id == test_conversation.id
        ).order_by(ChatMessage.message_index).all()
        
        # Verify indexes are sequential
        for i, msg in enumerate(messages):
            assert msg.message_index == i
        
        # Verify content order
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        for i, msg in enumerate(user_messages):
            assert f"Message {i}" in msg.content


# Import asyncio for async tests
import asyncio