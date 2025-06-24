"""Repository for chat message-related database operations."""

from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select, func
from sqlalchemy.exc import SQLAlchemyError

from app.models.chat_message import ChatMessage, MessageRole
from app.core.logging import logger


class ChatMessageRepository:
    """Repository for managing chat messages in the database."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLModel database session
        """
        self.session = session
    
    def create_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        thinking: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> ChatMessage:
        """Create a new chat message.
        
        Args:
            conversation_id: ID of the conversation
            role: Message role (user/assistant/system)
            content: Message content
            thinking: AI thinking content (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Created message
        """
        try:
            # Get the next message index for this conversation
            message_index = self._get_next_message_index(conversation_id)
            
            message = ChatMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                thinking=thinking,
                message_index=message_index,
                metadata=metadata or {}
            )
            
            self.session.add(message)
            self.session.commit()
            self.session.refresh(message)
            
            logger.info("message_created", 
                       message_id=str(message.id),
                       conversation_id=str(conversation_id),
                       role=role)
            return message
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("message_creation_error", error=str(e))
            raise
    
    def get_messages_by_conversation(
        self,
        conversation_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get messages for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of messages ordered by message_index
        """
        try:
            query = select(ChatMessage).where(
                ChatMessage.conversation_id == conversation_id
            ).order_by(ChatMessage.message_index)
            
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            
            messages = self.session.exec(query).all()
            return messages
        except SQLAlchemyError as e:
            logger.error("get_messages_error", error=str(e))
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
                select(func.count()).select_from(ChatMessage).where(
                    ChatMessage.conversation_id == conversation_id
                )
            ).one()
            
            return count
        except SQLAlchemyError as e:
            logger.error("get_message_count_error", error=str(e))
            raise
    
    def bulk_create_messages(self, messages: List[dict]) -> List[ChatMessage]:
        """Create multiple messages at once.
        
        Args:
            messages: List of message dictionaries with required fields
            
        Returns:
            List of created messages
        """
        try:
            created_messages = []
            
            for msg_data in messages:
                # Get the next message index for this conversation
                message_index = self._get_next_message_index(msg_data['conversation_id'])
                
                message = ChatMessage(
                    conversation_id=msg_data['conversation_id'],
                    role=msg_data['role'],
                    content=msg_data['content'],
                    thinking=msg_data.get('thinking'),
                    message_index=message_index,
                    metadata=msg_data.get('metadata', {})
                )
                
                self.session.add(message)
                created_messages.append(message)
            
            self.session.commit()
            
            # Refresh all messages
            for message in created_messages:
                self.session.refresh(message)
            
            logger.info("bulk_messages_created", count=len(created_messages))
            return created_messages
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("bulk_message_creation_error", error=str(e))
            raise
    
    def _get_next_message_index(self, conversation_id: UUID) -> int:
        """Get the next message index for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Next available message index
        """
        max_index = self.session.exec(
            select(func.max(ChatMessage.message_index)).where(
                ChatMessage.conversation_id == conversation_id
            )
        ).one()
        
        return (max_index or -1) + 1