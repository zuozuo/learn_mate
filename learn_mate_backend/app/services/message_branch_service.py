"""Service layer for message branching functionality."""

from typing import List, Optional, Dict
from uuid import UUID
from sqlmodel import Session
from sqlalchemy import select, and_, func, update
from sqlalchemy.orm import selectinload

from app.models.chat_message import ChatMessage, MessageRole
from app.models.message_branch import MessageBranch
from app.repositories.message_branch_repository import MessageBranchRepository
from app.repositories.chat_message_repository import ChatMessageRepository
from app.schemas.message_branch import (
    MessageEditResponse,
    MessageVersion,
    MessageBranch as MessageBranchSchema,
    BranchTreeNode,
)
from app.services.enhanced_chat_service import EnhancedChatService


class MessageBranchService:
    """Service for handling message branching logic."""

    def __init__(self, session: Session):
        """Initialize service with database session."""
        self.session = session
        self.branch_repo = MessageBranchRepository(session)
        self.message_repo = ChatMessageRepository(session)

    def edit_message(
        self, conversation_id: UUID, message_id: UUID, new_content: str, create_branch: bool = True
    ) -> Optional[MessageEditResponse]:
        """Edit a message and optionally create a new branch."""
        # Get the original message
        result = self.session.execute(
            select(ChatMessage).where(ChatMessage.id == message_id).options(selectinload(ChatMessage.branch))
        )
        original_message = result.scalar_one_or_none()

        if not original_message or original_message.conversation_id != conversation_id:
            return None

        # Only allow editing user messages
        if original_message.role != MessageRole.USER:
            return None

        # Create new branch if requested
        new_branch = None
        if create_branch:
            new_branch = self.branch_repo.create_branch(
                conversation_id=conversation_id, parent_message_id=message_id
            )

        # Create new version of the message
        new_version = ChatMessage(
            conversation_id=conversation_id,
            role=original_message.role,
            content=new_content,
            message_index=original_message.message_index,
            branch_id=new_branch.id if new_branch else original_message.branch_id,
            version_number=original_message.version_number + 1,
            parent_version_id=original_message.id,
            is_current_version=True,
        )

        # Mark original as not current
        original_message.is_current_version = False

        self.session.add(new_version)
        self.session.commit()
        self.session.refresh(new_version)

        # Generate AI response if this was a user message
        new_assistant_message = None
        if original_message.role == MessageRole.USER:
            # Get conversation history up to this point
            messages = self._get_branch_messages(
                conversation_id,
                new_branch.id if new_branch else original_message.branch_id,
                up_to_index=original_message.message_index,
            )

            # Add the edited message
            messages.append(new_version)

            # Generate response
            chat_service = EnhancedChatService(self.session)
            assistant_response = chat_service.send_message(
                conversation_id=conversation_id, message=new_content, existing_messages=messages
            )

            if assistant_response:
                # Update the assistant message with branch info
                assistant_message = self.message_repo.get_by_id(assistant_response.id)
                if assistant_message:
                    assistant_message.branch_id = new_branch.id if new_branch else original_message.branch_id
                    self.session.commit()
                    self.session.refresh(assistant_message)
                    new_assistant_message = self._to_message_version(assistant_message)

        return MessageEditResponse(
            message=self._to_message_version(new_version),
            branch=MessageBranchSchema.from_orm(new_branch) if new_branch else None,
            new_assistant_message=new_assistant_message,
        )

    def get_message_versions(self, message_id: UUID) -> List[MessageVersion]:
        """Get all versions of a message."""
        versions = self.branch_repo.get_message_versions(message_id)
        return [self._to_message_version(v) for v in versions]

    def get_conversation_branches(self, conversation_id: UUID) -> List[MessageBranchSchema]:
        """Get all branches for a conversation."""
        branches = self.branch_repo.get_conversation_branches(conversation_id)
        return [MessageBranchSchema.from_orm(b) for b in branches]

    def switch_branch(self, conversation_id: UUID, branch_id: UUID) -> bool:
        """Switch to a different branch."""
        # Verify branch exists and belongs to conversation
        branch = self.branch_repo.get_branch(branch_id)
        if not branch or branch.conversation_id != conversation_id:
            return False

        # Update all messages in the conversation to mark current branch
        self.session.execute(
            update(ChatMessage)
            .where(and_(ChatMessage.conversation_id == conversation_id, ChatMessage.branch_id == branch_id))
            .values(is_current_version=True)
        )

        # Mark messages in other branches as not current
        self.session.execute(
            update(ChatMessage)
            .where(and_(ChatMessage.conversation_id == conversation_id, ChatMessage.branch_id != branch_id))
            .values(is_current_version=False)
        )

        self.session.commit()
        return True

    def get_branch_tree(self, conversation_id: UUID) -> List[BranchTreeNode]:
        """Get the branch tree structure."""
        branches = self.branch_repo.get_conversation_branches(conversation_id)

        # Build tree structure
        branch_map: Dict[Optional[UUID], List[MessageBranch]] = {}
        for branch in branches:
            parent_id = branch.parent_message_id
            if parent_id not in branch_map:
                branch_map[parent_id] = []
            branch_map[parent_id].append(branch)

        # Count messages per branch
        result = self.session.execute(
            select(ChatMessage.branch_id, func.count(ChatMessage.id).label("count"))
            .where(ChatMessage.conversation_id == conversation_id)
            .group_by(ChatMessage.branch_id)
        )
        message_counts = {row[0]: row[1] for row in result}

        # Build tree recursively
        def build_node(branch: MessageBranch) -> BranchTreeNode:
            children = branch_map.get(branch.id, [])
            return BranchTreeNode(
                id=branch.id,
                name=branch.branch_name,
                parent_message_id=branch.parent_message_id,
                message_count=message_counts.get(branch.id, 0),
                children=[build_node(child) for child in children],
            )

        # Start with root branches (no parent)
        roots = branch_map.get(None, [])
        return [build_node(root) for root in roots]

    def _get_branch_messages(
        self, conversation_id: UUID, branch_id: UUID, up_to_index: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get messages in a branch up to a certain index."""
        query = select(ChatMessage).where(
            and_(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.branch_id == branch_id,
                ChatMessage.is_current_version.is_(True),
            )
        )

        if up_to_index is not None:
            query = query.where(ChatMessage.message_index <= up_to_index)

        query = query.order_by(ChatMessage.message_index)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def _to_message_version(self, message: ChatMessage) -> MessageVersion:
        """Convert ChatMessage to MessageVersion."""
        return MessageVersion(
            id=message.id,
            content=message.content,
            version_number=message.version_number,
            branch_id=message.branch_id,
            branch_name=message.branch.branch_name if message.branch else None,
            created_at=message.created_at,
            is_current_version=message.is_current_version,
        )
