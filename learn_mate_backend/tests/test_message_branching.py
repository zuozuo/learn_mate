"""Unit tests for message branching functionality."""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlmodel import Session

from app.models.message_branch import MessageBranch
from app.models.chat_message import ChatMessage, MessageRole
from app.repositories.message_branch_repository import MessageBranchRepository
from app.services.message_branch_service import MessageBranchService


def test_create_branch(session: Session):
    """Test creating a new message branch."""
    repo = MessageBranchRepository(session)
    conversation_id = uuid4()

    # Create main branch
    main_branch = repo.create_branch(conversation_id=conversation_id, parent_message_id=None, branch_name="Main")

    assert main_branch.conversation_id == conversation_id
    assert main_branch.parent_message_id is None
    assert main_branch.branch_name == "Main"
    assert main_branch.sequence_number == 1

    # Create alternative branch
    parent_message_id = uuid4()
    alt_branch = repo.create_branch(conversation_id=conversation_id, parent_message_id=parent_message_id)

    assert alt_branch.conversation_id == conversation_id
    assert alt_branch.parent_message_id == parent_message_id
    assert alt_branch.branch_name == "Alternative 1"
    assert alt_branch.sequence_number == 1


def test_get_message_versions(session: Session):
    """Test getting all versions of a message."""
    repo = MessageBranchRepository(session)
    conversation_id = uuid4()

    # Create a branch
    branch = repo.create_branch(conversation_id)

    # Create original message
    original = ChatMessage(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content="Original content",
        message_index=1,
        branch_id=branch.id,
        version_number=1,
    )
    session.add(original)
    session.commit()

    # Create edited version - use same branch but set is_current_version
    original.is_current_version = False
    session.add(original)

    edited = ChatMessage(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content="Edited content",
        message_index=2,  # Use different message_index to avoid constraint violation
        branch_id=branch.id,
        version_number=2,
        parent_version_id=original.id,
        is_current_version=True,
    )
    session.add(edited)
    session.commit()

    # Get versions
    versions = repo.get_message_versions(original.id)

    assert len(versions) == 2
    assert versions[0].content == "Original content"
    assert versions[1].content == "Edited content"


def test_edit_message_service(session: Session, test_user):
    """Test editing a message through the service layer."""
    service = MessageBranchService(session)
    conversation_id = uuid4()

    # Create initial branch and message
    branch_repo = MessageBranchRepository(session)
    main_branch = branch_repo.create_branch(conversation_id)

    # Create user message
    user_message = ChatMessage(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content="Tell me about Python",
        message_index=1,
        branch_id=main_branch.id,
    )
    session.add(user_message)
    session.commit()

    # Edit the message
    result = service.edit_message(
        conversation_id=conversation_id,
        message_id=user_message.id,
        new_content="Tell me about JavaScript",
        create_branch=True,
    )

    assert result is not None
    assert result.message.content == "Tell me about JavaScript"
    assert result.message.version_number == 2
    assert result.branch is not None
    assert result.branch.parent_message_id == user_message.id


def test_branch_tree_structure(session: Session):
    """Test building branch tree structure."""
    service = MessageBranchService(session)
    conversation_id = uuid4()

    # Create main branch
    branch_repo = MessageBranchRepository(session)
    main_branch = branch_repo.create_branch(conversation_id=conversation_id, branch_name="Main")

    # Create some messages
    for i in range(3):
        msg = ChatMessage(
            conversation_id=conversation_id,
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {i}",
            message_index=i,
            branch_id=main_branch.id,
        )
        session.add(msg)
    session.commit()

    # Create alternative branch
    parent_msg_id = uuid4()
    alt_branch = branch_repo.create_branch(
        conversation_id=conversation_id, parent_message_id=parent_msg_id, branch_name="Alternative"
    )

    # Add messages to alternative branch
    for i in range(2):
        msg = ChatMessage(
            conversation_id=conversation_id,
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Alt message {i}",
            message_index=i + 3,
            branch_id=alt_branch.id,
        )
        session.add(msg)
    session.commit()

    # Get branch tree
    tree = service.get_branch_tree(conversation_id)

    assert len(tree) == 1  # One root branch
    assert tree[0].name == "Main"
    assert tree[0].message_count == 3
    assert len(tree[0].children) == 0  # No children in this test setup
