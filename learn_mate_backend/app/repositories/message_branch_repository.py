"""Repository for message branch operations."""

from typing import List, Optional
from uuid import UUID
from sqlmodel import Session
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload

from app.models.message_branch import MessageBranch
from app.models.chat_message import ChatMessage


class MessageBranchRepository:
    """Repository for message branch database operations."""

    def __init__(self, session: Session):
        """Initialize repository with database session."""
        self.session = session

    def create_branch(
        self, conversation_id: UUID, parent_message_id: Optional[UUID] = None, branch_name: Optional[str] = None
    ) -> MessageBranch:
        """Create a new message branch."""
        # Get next sequence number
        result = self.session.execute(
            select(func.coalesce(func.max(MessageBranch.sequence_number), 0)).where(
                and_(
                    MessageBranch.conversation_id == conversation_id,
                    MessageBranch.parent_message_id == parent_message_id,
                )
            )
        )
        max_sequence = result.scalar()
        next_sequence = max_sequence + 1

        # Generate branch name if not provided
        if not branch_name:
            if parent_message_id:
                branch_name = f"Alternative {next_sequence}"
            else:
                branch_name = "Main"

        branch = MessageBranch(
            conversation_id=conversation_id,
            parent_message_id=parent_message_id,
            sequence_number=next_sequence,
            branch_name=branch_name,
        )

        self.session.add(branch)
        self.session.commit()
        self.session.refresh(branch)

        return branch

    def get_branch(self, branch_id: UUID) -> Optional[MessageBranch]:
        """Get a branch by ID."""
        result = self.session.execute(
            select(MessageBranch).where(MessageBranch.id == branch_id).options(selectinload(MessageBranch.messages))
        )
        return result.scalar_one_or_none()

    def get_conversation_branches(self, conversation_id: UUID) -> List[MessageBranch]:
        """Get all branches for a conversation."""
        result = self.session.execute(
            select(MessageBranch)
            .where(MessageBranch.conversation_id == conversation_id)
            .order_by(MessageBranch.created_at)
        )
        return list(result.scalars().all())

    def get_default_branch(self, conversation_id: UUID) -> Optional[MessageBranch]:
        """Get the default (main) branch for a conversation."""
        result = self.session.execute(
            select(MessageBranch)
            .where(and_(MessageBranch.conversation_id == conversation_id, MessageBranch.parent_message_id.is_(None)))
            .order_by(MessageBranch.sequence_number)
            .limit(1)
        )
        return result.scalar_one_or_none()

    def update_branch_name(self, branch_id: UUID, name: str) -> Optional[MessageBranch]:
        """Update branch name."""
        branch = self.get_branch(branch_id)
        if branch:
            branch.branch_name = name
            self.session.commit()
            self.session.refresh(branch)
        return branch

    def get_message_versions(self, original_message_id: UUID) -> List[ChatMessage]:
        """Get all versions of a message."""
        # First get the original message to find the root
        result = self.session.execute(select(ChatMessage).where(ChatMessage.id == original_message_id))
        original = result.scalar_one_or_none()

        if not original:
            return []

        # Find the root message (version 1) with cycle detection
        root_id = original_message_id
        visited_ids = {original_message_id}

        if original.parent_version_id:
            # Traverse up to find the root
            current = original
            while current.parent_version_id:
                # Check for cycle
                if current.parent_version_id in visited_ids:
                    break

                result = self.session.execute(select(ChatMessage).where(ChatMessage.id == current.parent_version_id))
                parent = result.scalar_one_or_none()
                if not parent:
                    break

                visited_ids.add(parent.id)
                current = parent
                root_id = current.id

        # Get all versions by traversing the version tree
        all_versions = []
        to_process = [root_id]
        processed = set()

        while to_process:
            current_id = to_process.pop(0)
            if current_id in processed:
                continue

            processed.add(current_id)

            # Get the current message
            result = self.session.execute(select(ChatMessage).where(ChatMessage.id == current_id))
            message = result.scalar_one_or_none()
            if message:
                all_versions.append(message)

                # Find all messages that have this as parent
                result = self.session.execute(select(ChatMessage).where(ChatMessage.parent_version_id == current_id))
                children = result.scalars().all()
                for child in children:
                    if child.id not in processed:
                        to_process.append(child.id)

        # Sort by version number
        all_versions.sort(key=lambda m: m.version_number)
        return all_versions
