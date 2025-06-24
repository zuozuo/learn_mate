"""Service layer for conversation management."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlmodel import Session

from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage, MessageRole
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.chat_message_repository import ChatMessageRepository
from app.core.logging import logger


class ConversationService:
    """Service for managing conversations and messages."""

    def __init__(self, session: Session):
        """Initialize service with database session.

        Args:
            session: SQLModel database session
        """
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = ChatMessageRepository(session)

    async def create_conversation(
        self, user_id: int, title: Optional[str] = None, first_message: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation.

        Args:
            user_id: ID of the user
            title: Optional title (auto-generated if not provided)
            first_message: Optional first user message

        Returns:
            Created conversation
        """
        # Generate title from first message if not provided
        if not title and first_message:
            title = self._generate_title_from_message(first_message)
        elif not title:
            title = "New Conversation"

        # Create conversation
        conversation = self.conversation_repo.create_conversation(user_id, title)

        # Add first message if provided
        if first_message:
            self.message_repo.create_message(
                conversation_id=conversation.id, role=MessageRole.USER, content=first_message
            )

        return conversation

    async def get_conversations(
        self, user_id: int, page: int = 1, limit: int = 20, search: Optional[str] = None
    ) -> Tuple[List[dict], int]:
        """Get conversations for a user with pagination.

        Args:
            user_id: ID of the user
            page: Page number
            limit: Items per page
            search: Optional search term

        Returns:
            Tuple of (conversation_list, total_count)
        """
        conversations, total = self.conversation_repo.get_conversations_by_user(user_id, page, limit, search)

        # Enhance with message count
        conversation_list = []
        for conv in conversations:
            message_count = self.conversation_repo.get_message_count(conv.id)
            conv_dict = conv.model_dump()
            conv_dict["message_count"] = message_count
            conversation_list.append(conv_dict)

        return conversation_list, total

    async def get_conversation_with_messages(self, conversation_id: UUID, user_id: int) -> Optional[dict]:
        """Get a conversation with all its messages.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)

        Returns:
            Conversation with messages if found and authorized
        """
        conversation = self.conversation_repo.get_conversation_by_id(conversation_id, user_id)

        if not conversation:
            return None

        # Get all messages
        messages = self.message_repo.get_messages_by_conversation(conversation_id)

        # Build response
        conv_dict = conversation.model_dump()
        conv_dict["messages"] = [msg.model_dump() for msg in messages]

        return conv_dict

    async def update_conversation_title(
        self, conversation_id: UUID, user_id: int, title: str
    ) -> Optional[Conversation]:
        """Update conversation title.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user
            title: New title

        Returns:
            Updated conversation if found and authorized
        """
        return self.conversation_repo.update_conversation(conversation_id, user_id, title=title)

    async def delete_conversation(self, conversation_id: UUID, user_id: int) -> bool:
        """Soft delete a conversation.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user

        Returns:
            True if deleted, False if not found
        """
        return self.conversation_repo.soft_delete_conversation(conversation_id, user_id)

    async def add_message(
        self, conversation_id: UUID, user_id: int, role: MessageRole, content: str, thinking: Optional[str] = None
    ) -> Optional[ChatMessage]:
        """Add a message to a conversation.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)
            role: Message role
            content: Message content
            thinking: Optional thinking content

        Returns:
            Created message if authorized
        """
        # Verify conversation belongs to user
        conversation = self.conversation_repo.get_conversation_by_id(conversation_id, user_id)

        if not conversation:
            logger.warning("unauthorized_message_attempt", conversation_id=str(conversation_id), user_id=user_id)
            return None

        # Create message
        message = self.message_repo.create_message(
            conversation_id=conversation_id, role=role, content=content, thinking=thinking
        )

        # Auto-update title if it's still "New Conversation" and this is one of the first messages
        if conversation.title == "New Conversation" and role == MessageRole.USER:
            message_count = self.conversation_repo.get_message_count(conversation_id)
            if message_count <= 2:  # First user message
                new_title = self._generate_title_from_message(content)
                self.conversation_repo.update_conversation(conversation_id, user_id, title=new_title)

        return message

    def _generate_title_from_message(self, message: str, max_length: int = 50) -> str:
        """Generate a conversation title from the first message.

        Args:
            message: Message content
            max_length: Maximum title length

        Returns:
            Generated title
        """
        # Clean up the message
        title = message.strip().replace("\n", " ")

        # Truncate if too long
        if len(title) > max_length:
            title = title[: max_length - 3] + "..."

        return title or "New Conversation"
