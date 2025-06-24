"""Tests for conversation management API endpoints."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage, MessageRole


class TestConversationsAPI:
    """Test suite for conversation management endpoints."""
    
    def test_create_conversation_success(
        self, 
        client: TestClient, 
        auth_headers: dict,
        test_user: User
    ):
        """Test successful conversation creation."""
        response = client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "Test Conversation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Conversation"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_conversation_with_first_message(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session
    ):
        """Test creating conversation with initial message."""
        response = client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={
                "title": "Chat with first message",
                "first_message": "Hello, world!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify message was created
        conversation_id = data["id"]
        from uuid import UUID
        messages = session.query(ChatMessage).filter(
            ChatMessage.conversation_id == UUID(conversation_id)
        ).all()
        
        assert len(messages) == 1
        assert messages[0].content == "Hello, world!"
        assert messages[0].role == MessageRole.USER
    
    def test_create_conversation_unauthorized(self, client: TestClient):
        """Test conversation creation without authentication."""
        response = client.post(
            "/api/v1/conversations",
            json={"title": "Unauthorized"}
        )
        
        assert response.status_code == 403
    
    def test_get_conversations_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """Test retrieving user's conversations."""
        response = client.get(
            "/api/v1/conversations",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        
        assert len(data["conversations"]) >= 1
        assert any(c["id"] == str(test_conversation.id) for c in data["conversations"])
    
    def test_get_conversations_with_pagination(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session,
        test_user: User
    ):
        """Test conversation list pagination."""
        # Create multiple conversations
        for i in range(5):
            conv = Conversation(
                user_id=test_user.id,
                title=f"Conversation {i}"
            )
            session.add(conv)
        session.commit()
        
        # Test first page
        response = client.get(
            "/api/v1/conversations?page=1&limit=3",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) <= 3
        assert data["page"] == 1
        assert data["limit"] == 3
        assert data["total"] >= 5
    
    def test_get_conversations_with_search(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session,
        test_user: User
    ):
        """Test conversation search functionality."""
        # Create conversations with different titles
        conversations = [
            Conversation(user_id=test_user.id, title="Python Tutorial"),
            Conversation(user_id=test_user.id, title="JavaScript Guide"),
            Conversation(user_id=test_user.id, title="Python Advanced"),
        ]
        for conv in conversations:
            session.add(conv)
        session.commit()
        
        # Search for Python
        response = client.get(
            "/api/v1/conversations?search=Python",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 2
        assert all("Python" in c["title"] for c in data["conversations"])
    
    def test_get_conversation_detail_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation,
        test_messages: list[ChatMessage]
    ):
        """Test retrieving conversation with messages."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_conversation.id)
        assert data["title"] == test_conversation.title
        assert "messages" in data
        assert len(data["messages"]) == len(test_messages)
        
        # Verify message order
        for i, msg in enumerate(data["messages"]):
            assert msg["content"] == test_messages[i].content
            assert msg["role"] == test_messages[i].role.value
    
    def test_get_conversation_detail_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test retrieving non-existent conversation."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/conversations/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found"
    
    def test_get_conversation_detail_unauthorized(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session,
        test_user: User
    ):
        """Test accessing another user's conversation."""
        # Create another user and their conversation
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
        
        # Try to access with test user's token
        response = client.get(
            f"/api/v1/conversations/{other_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_update_conversation_title(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """Test updating conversation title."""
        new_title = "Updated Title"
        response = client.patch(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers,
            json={"title": new_title}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == new_title
        assert data["id"] == str(test_conversation.id)
    
    def test_update_conversation_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test updating non-existent conversation."""
        fake_id = uuid4()
        response = client.patch(
            f"/api/v1/conversations/{fake_id}",
            headers=auth_headers,
            json={"title": "New Title"}
        )
        
        assert response.status_code == 404
    
    def test_delete_conversation_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation: Conversation,
        session: Session
    ):
        """Test soft deleting a conversation."""
        response = client.delete(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Conversation deleted successfully"
        
        # Verify soft delete
        session.refresh(test_conversation)
        assert test_conversation.is_deleted is True
    
    def test_delete_conversation_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test deleting non-existent conversation."""
        fake_id = uuid4()
        response = client.delete(
            f"/api/v1/conversations/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_conversation_isolation(
        self,
        client: TestClient,
        session: Session
    ):
        """Test that users can only see their own conversations."""
        # Create two users with conversations
        user1 = User(email="user1@test.com", hashed_password=User.hash_password("pass1"))
        user2 = User(email="user2@test.com", hashed_password=User.hash_password("pass2"))
        session.add(user1)
        session.add(user2)
        session.commit()
        
        conv1 = Conversation(user_id=user1.id, title="User 1 Conversation")
        conv2 = Conversation(user_id=user2.id, title="User 2 Conversation")
        session.add(conv1)
        session.add(conv2)
        session.commit()
        
        # Get auth token for user1
        from app.utils.auth import create_access_token
        token1 = create_access_token(str(user1.id))
        headers1 = {"Authorization": f"Bearer {token1.access_token}"}
        
        # User1 should only see their conversation
        response = client.get("/api/v1/conversations", headers=headers1)
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["title"] == "User 1 Conversation"