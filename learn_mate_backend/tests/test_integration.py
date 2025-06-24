"""Integration tests for the entire conversation flow."""

import pytest
import json
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage


class TestConversationFlow:
    """Integration tests for complete conversation workflows."""
    
    @pytest.mark.integration
    def test_complete_conversation_flow(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_langgraph_agent,
        session: Session
    ):
        """Test a complete conversation lifecycle."""
        # 1. Create a new conversation
        create_response = client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={
                "title": "Integration Test Conversation",
                "first_message": "Hello, AI!"
            }
        )
        assert create_response.status_code == 200
        conversation = create_response.json()
        conversation_id = conversation["id"]
        
        # 2. Verify conversation appears in list
        list_response = client.get(
            "/api/v1/conversations",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        conversations = list_response.json()["conversations"]
        assert any(c["id"] == conversation_id for c in conversations)
        
        # 3. Send a message
        message_response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=auth_headers,
            json={
                "messages": [{"role": "user", "content": "What is Python?"}]
            }
        )
        assert message_response.status_code == 200
        assert message_response.json()["role"] == "assistant"
        
        # 4. Get conversation with messages
        detail_response = client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers=auth_headers
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert len(detail["messages"]) >= 3  # Initial + Q&A
        
        # 5. Update conversation title
        update_response = client.patch(
            f"/api/v1/conversations/{conversation_id}",
            headers=auth_headers,
            json={"title": "Python Discussion"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Python Discussion"
        
        # 6. Delete conversation
        delete_response = client.delete(
            f"/api/v1/conversations/{conversation_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        
        # 7. Verify it's gone from list
        final_list = client.get(
            "/api/v1/conversations",
            headers=auth_headers
        ).json()["conversations"]
        assert not any(c["id"] == conversation_id for c in final_list)
    
    @pytest.mark.integration
    def test_streaming_conversation_flow(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_langgraph_agent
    ):
        """Test streaming message flow."""
        # Create conversation
        create_response = client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "Streaming Test"}
        )
        conversation_id = create_response.json()["id"]
        
        # Send streaming message
        with client.stream(
            "POST",
            f"/api/v1/conversations/{conversation_id}/messages/stream",
            headers=auth_headers,
            json={
                "messages": [{"role": "user", "content": "Stream this response"}]
            }
        ) as response:
            assert response.status_code == 200
            
            # Collect all events
            events = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        events.append(json.loads(line[6:]))
                    except json.JSONDecodeError:
                        pass
            
            # Verify streaming worked
            assert len(events) > 1
            assert any(e.get("done") for e in events)
            
            # Verify content was streamed
            content_events = [e for e in events if "content" in e and not e.get("done")]
            assert len(content_events) > 0
    
    @pytest.mark.integration
    def test_multiple_users_isolation(
        self,
        client: TestClient,
        session: Session,
        mock_langgraph_agent
    ):
        """Test that multiple users' conversations are properly isolated."""
        # Create two users
        users = []
        for i in range(2):
            user = User(
                email=f"user{i}@test.com",
                hashed_password=User.hash_password(f"pass{i}")
            )
            session.add(user)
            users.append(user)
        session.commit()
        
        # Create auth headers for each user
        from app.utils.auth import create_access_token
        headers = []
        for user in users:
            token = create_access_token(str(user.id))
            headers.append({"Authorization": f"Bearer {token.access_token}"})
        
        # Each user creates a conversation
        conversation_ids = []
        for i, header in enumerate(headers):
            response = client.post(
                "/api/v1/conversations",
                headers=header,
                json={"title": f"User {i} Conversation"}
            )
            conversation_ids.append(response.json()["id"])
        
        # Verify each user only sees their own conversation
        for i, header in enumerate(headers):
            response = client.get("/api/v1/conversations", headers=header)
            conversations = response.json()["conversations"]
            
            assert len(conversations) == 1
            assert conversations[0]["title"] == f"User {i} Conversation"
            
            # Try to access other user's conversation
            other_id = conversation_ids[1 - i]
            response = client.get(
                f"/api/v1/conversations/{other_id}",
                headers=header
            )
            assert response.status_code == 404
    
    @pytest.mark.integration
    def test_thinking_content_persistence(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session,
        monkeypatch
    ):
        """Test that thinking content is properly saved and retrieved."""
        # Create a custom mock for the LangGraph agent that returns thinking content
        class MockLangGraphAgentWithThinking:
            def __init__(self):
                pass
            
            async def get_response(self, messages, session_id, user_id):
                return [{
                    "role": "assistant",
                    "content": "The answer is 42",
                    "thinking": "<think>Let me calculate... 6 * 7 = 42</think>"
                }]
        
        # Patch the agent in the chatbot module
        import app.api.v1.chatbot
        monkeypatch.setattr(app.api.v1.chatbot, "agent", MockLangGraphAgentWithThinking())
        
        # Create conversation and send message
        conv_response = client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "Thinking Test"}
        )
        conv_id = conv_response.json()["id"]
        
        # Send message
        msg_response = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=auth_headers,
            json={"messages": [{"role": "user", "content": "What's 6 times 7?"}]}
        )
        assert msg_response.status_code == 200
        
        # Retrieve and verify thinking was saved
        detail_response = client.get(
            f"/api/v1/conversations/{conv_id}",
            headers=auth_headers
        )
        messages = detail_response.json()["messages"]
        
        # Find assistant message
        assistant_msg = next(
            (m for m in messages if m["role"] == "assistant"),
            None
        )
        
        assert assistant_msg is not None
        # Thinking content is extracted without tags
        assert assistant_msg.get("thinking") == "Let me calculate... 6 * 7 = 42"
    
    @pytest.mark.integration
    def test_conversation_search_and_pagination(
        self,
        client: TestClient,
        auth_headers: dict,
        session: Session,
        test_user: User
    ):
        """Test search and pagination features together."""
        # Create many conversations with varied titles
        titles = [
            "Python Basics",
            "JavaScript Tutorial", 
            "Python Advanced",
            "Machine Learning with Python",
            "Web Development",
            "Data Science in Python",
            "React Guide",
            "Python for Beginners",
            "Django Tutorial",
            "FastAPI with Python"
        ]
        
        for title in titles:
            conv = Conversation(user_id=test_user.id, title=title)
            session.add(conv)
        session.commit()
        
        # Test search with pagination
        response = client.get(
            "/api/v1/conversations?search=Python&page=1&limit=3",
            headers=auth_headers
        )
        
        data = response.json()
        assert data["total"] == 6  # 6 conversations with "Python"
        assert len(data["conversations"]) == 3  # Limited to 3
        assert all("Python" in c["title"] for c in data["conversations"])
        
        # Get second page
        response = client.get(
            "/api/v1/conversations?search=Python&page=2&limit=3",
            headers=auth_headers
        )
        
        data = response.json()
        assert len(data["conversations"]) == 3  # Remaining 3
        assert data["page"] == 2