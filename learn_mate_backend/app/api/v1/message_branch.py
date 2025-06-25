"""API endpoints for message branching functionality."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.message_branch import (
    MessageBranch as MessageBranchSchema,
    MessageEditRequest,
    MessageEditResponse,
    MessageVersion,
    BranchTreeNode,
)
from app.services.database import database_service
from app.services.message_branch_service import MessageBranchService
from app.repositories.conversation_repository import ConversationRepository

router = APIRouter(prefix="/conversations", tags=["message-branches"])


@router.post("/{conversation_id}/messages/{message_id}/edit", response_model=MessageEditResponse)
def edit_message(
    conversation_id: UUID,
    message_id: UUID,
    request: MessageEditRequest,
    current_user: User = Depends(get_current_user),
):
    """Edit a message and create a new branch if requested."""
    with Session(database_service.engine) as session:
        # Verify user owns the conversation
        conv_repo = ConversationRepository(session)
        conversation = conv_repo.get_by_id(conversation_id)

        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        # Edit the message
        service = MessageBranchService(session)
        result = service.edit_message(
            conversation_id=conversation_id,
            message_id=message_id,
            new_content=request.content,
            create_branch=request.create_branch,
        )

        if not result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to edit message")

        return result


@router.get("/{conversation_id}/messages/{message_id}/versions", response_model=List[MessageVersion])
def get_message_versions(
    conversation_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Get all versions of a message."""
    with Session(database_service.engine) as session:
        # Verify user owns the conversation
        conv_repo = ConversationRepository(session)
        conversation = conv_repo.get_by_id(conversation_id)

        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        service = MessageBranchService(session)
        versions = service.get_message_versions(message_id)

        return versions


@router.get("/{conversation_id}/branches", response_model=List[MessageBranchSchema])
def get_conversation_branches(conversation_id: UUID, current_user: User = Depends(get_current_user)):
    """Get all branches for a conversation."""
    with Session(database_service.engine) as session:
        # Verify user owns the conversation
        conv_repo = ConversationRepository(session)
        conversation = conv_repo.get_by_id(conversation_id)

        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        service = MessageBranchService(session)
        branches = service.get_conversation_branches(conversation_id)

        return branches


@router.post("/{conversation_id}/branches/{branch_id}/switch")
def switch_branch(
    conversation_id: UUID,
    branch_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Switch to a different branch in the conversation."""
    with Session(database_service.engine) as session:
        # Verify user owns the conversation
        conv_repo = ConversationRepository(session)
        conversation = conv_repo.get_by_id(conversation_id)

        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        service = MessageBranchService(session)
        success = service.switch_branch(conversation_id, branch_id)

        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to switch branch")

        return {"status": "success", "branch_id": str(branch_id)}


@router.get("/{conversation_id}/branch-tree", response_model=List[BranchTreeNode])
def get_branch_tree(conversation_id: UUID, current_user: User = Depends(get_current_user)):
    """Get the branch tree structure for visualization."""
    with Session(database_service.engine) as session:
        # Verify user owns the conversation
        conv_repo = ConversationRepository(session)
        conversation = conv_repo.get_by_id(conversation_id)

        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        service = MessageBranchService(session)
        tree = service.get_branch_tree(conversation_id)

        return tree
