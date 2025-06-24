"""Repository for conversation-related database operations."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, UTC

from sqlmodel import Session, select, func, and_
from sqlalchemy.exc import SQLAlchemyError

from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage
from app.core.logging import logger


class ConversationRepository:
    """Repository for managing conversations in the database."""

    def __init__(self, session: Session):
        """Initialize repository with database session.

        Args:
            session: SQLModel database session
        """
        self.session = session

    def create_conversation(self, user_id: int, title: str = "New Conversation") -> Conversation:
        """Create a new conversation.

        Args:
            user_id: ID of the user creating the conversation
            title: Title of the conversation

        Returns:
            Created conversation
        """
        try:
            conversation = Conversation(user_id=user_id, title=title)
            self.session.add(conversation)
            self.session.commit()
            self.session.refresh(conversation)

            logger.info("conversation_created", conversation_id=str(conversation.id), user_id=user_id)
            return conversation
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("conversation_creation_error", error=str(e))
            raise

    def get_conversations_by_user(
        self, user_id: int, page: int = 1, limit: int = 20, search: Optional[str] = None
    ) -> tuple[List[Conversation], int]:
        """Get conversations for a user with pagination.

        Args:
            user_id: ID of the user
            page: Page number (1-indexed)
            limit: Number of items per page
            search: Optional search term for title/summary

        Returns:
            Tuple of (conversations, total_count)
        """
        try:
            # Base query
            query = select(Conversation).where(and_(Conversation.user_id == user_id, Conversation.is_deleted == False))

            # Add search filter if provided
            if search:
                search_term = f"%{search}%"
                query = query.where(Conversation.title.ilike(search_term) | Conversation.summary.ilike(search_term))

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_count = self.session.exec(count_query).one()

            # Add pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)

            conversations = self.session.exec(query).all()

            return conversations, total_count
        except SQLAlchemyError as e:
            logger.error("get_conversations_error", error=str(e))
            raise

    def get_conversation_by_id(self, conversation_id: UUID, user_id: int) -> Optional[Conversation]:
        """Get a conversation by ID, ensuring it belongs to the user.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)

        Returns:
            Conversation if found and authorized, None otherwise
        """
        try:
            conversation = self.session.exec(
                select(Conversation).where(
                    and_(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id,
                        Conversation.is_deleted == False,
                    )
                )
            ).first()

            return conversation
        except SQLAlchemyError as e:
            logger.error("get_conversation_error", error=str(e))
            raise

    def update_conversation(
        self,
        conversation_id: UUID,
        user_id: int,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        metadata_json: Optional[dict] = None,
    ) -> Optional[Conversation]:
        """Update a conversation.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)
            title: New title (optional)
            summary: New summary (optional)
            metadata: New metadata (optional)

        Returns:
            Updated conversation if found and authorized, None otherwise
        """
        try:
            conversation = self.get_conversation_by_id(conversation_id, user_id)
            if not conversation:
                return None

            if title is not None:
                conversation.title = title
            if summary is not None:
                conversation.summary = summary
            if metadata_json is not None:
                conversation.metadata_json = metadata_json

            conversation.updated_at = datetime.now(UTC)

            self.session.add(conversation)
            self.session.commit()
            self.session.refresh(conversation)

            logger.info("conversation_updated", conversation_id=str(conversation_id))
            return conversation
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("update_conversation_error", error=str(e))
            raise

    def soft_delete_conversation(self, conversation_id: UUID, user_id: int) -> bool:
        """Soft delete a conversation.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)

        Returns:
            True if deleted, False if not found
        """
        try:
            conversation = self.get_conversation_by_id(conversation_id, user_id)
            if not conversation:
                return False

            conversation.is_deleted = True
            conversation.updated_at = datetime.now(UTC)

            self.session.add(conversation)
            self.session.commit()

            logger.info("conversation_deleted", conversation_id=str(conversation_id))
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("delete_conversation_error", error=str(e))
            raise

    def get_message_count(self, conversation_id: UUID) -> int:
        """Get the count of messages in a conversation.

        Args:
            conversation_id: ID of the conversation

        Returns:
            Number of messages
        """
        try:
            count = self.session.exec(
                select(func.count()).select_from(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
            ).one()

            return count
        except SQLAlchemyError as e:
            logger.error("get_message_count_error", error=str(e))
            raise
