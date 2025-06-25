"""API tests for message branching endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from uuid import uuid4

from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage, MessageRole
from app.models.message_branch import MessageBranch


def test_edit_message_endpoint(client: TestClient, session: Session, auth_headers):
    """Test editing a message via API."""
    # Create conversation and messages
    user_id = 1  # Assuming test user ID
    conversation = Conversation(user_id=user_id, title="Test Conversation")
    session.add(conversation)
    session.flush()

    # Create main branch
    main_branch = MessageBranch(conversation_id=conversation.id, sequence_number=1, branch_name="Main")
    session.add(main_branch)
    session.flush()

    # Create user message
    user_message = ChatMessage(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content="Original question",
        message_index=0,
        branch_id=main_branch.id,
    )
    session.add(user_message)
    session.commit()

    # Edit the message
    response = client.post(
        f"/api/v1/conversations/{conversation.id}/messages/{user_message.id}/edit",
        json={"content": "Edited question", "create_branch": True},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"]["content"] == "Edited question"
    assert data["message"]["version_number"] == 2
    assert data["branch"] is not None


def test_get_message_versions_endpoint(client: TestClient, session: Session, auth_headers):
    """Test getting message versions via API."""
    # Setup similar to above
    user_id = 1
    conversation = Conversation(user_id=user_id, title="Test Conversation")
    session.add(conversation)
    session.flush()

    branch = MessageBranch(conversation_id=conversation.id, sequence_number=1, branch_name="Main")
    session.add(branch)
    session.flush()

    # Create original and edited messages
    original = ChatMessage(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content="Version 1",
        message_index=0,
        branch_id=branch.id,
        version_number=1,
    )
    session.add(original)
    session.flush()

    edited = ChatMessage(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content="Version 2",
        message_index=0,
        branch_id=branch.id,
        version_number=2,
        parent_version_id=original.id,
    )
    session.add(edited)
    session.commit()

    # Get versions
    response = client.get(
        f"/api/v1/conversations/{conversation.id}/messages/{original.id}/versions", headers=auth_headers
    )

    assert response.status_code == 200
    versions = response.json()
    assert len(versions) == 2
    assert versions[0]["content"] == "Version 1"
    assert versions[1]["content"] == "Version 2"


def test_get_branches_endpoint(client: TestClient, session: Session, auth_headers):
    """Test getting conversation branches via API."""
    user_id = 1
    conversation = Conversation(user_id=user_id, title="Test Conversation")
    session.add(conversation)
    session.flush()

    # Create multiple branches
    main_branch = MessageBranch(conversation_id=conversation.id, sequence_number=1, branch_name="Main")
    session.add(main_branch)

    alt_branch = MessageBranch(
        conversation_id=conversation.id, parent_message_id=uuid4(), sequence_number=1, branch_name="Alternative"
    )
    session.add(alt_branch)
    session.commit()

    # Get branches
    response = client.get(f"/api/v1/conversations/{conversation.id}/branches", headers=auth_headers)

    assert response.status_code == 200
    branches = response.json()
    assert len(branches) == 2
    branch_names = [b["branch_name"] for b in branches]
    assert "Main" in branch_names
    assert "Alternative" in branch_names


def test_branch_tree_endpoint(client: TestClient, session: Session, auth_headers):
    """Test getting branch tree structure via API."""
    user_id = 1
    conversation = Conversation(user_id=user_id, title="Test Conversation")
    session.add(conversation)
    session.flush()

    # Create branch with messages
    branch = MessageBranch(conversation_id=conversation.id, sequence_number=1, branch_name="Main")
    session.add(branch)
    session.flush()

    # Add some messages
    for i in range(3):
        msg = ChatMessage(
            conversation_id=conversation.id,
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {i}",
            message_index=i,
            branch_id=branch.id,
        )
        session.add(msg)
    session.commit()

    # Get branch tree
    response = client.get(f"/api/v1/conversations/{conversation.id}/branch-tree", headers=auth_headers)

    assert response.status_code == 200
    tree = response.json()
    assert len(tree) == 1
    assert tree[0]["name"] == "Main"
    assert tree[0]["message_count"] == 3
