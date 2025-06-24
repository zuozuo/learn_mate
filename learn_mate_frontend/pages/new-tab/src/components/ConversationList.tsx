import React, { useState, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, Search } from 'lucide-react';
import { conversationService, Conversation } from '../services/conversation';
import { cn } from '@extension/ui';
import './ConversationList.scss';

interface ConversationListProps {
  currentConversationId?: string;
  onSelectConversation: (id: string) => void;
  onCreateConversation: () => void;
  isLight?: boolean;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  currentConversationId,
  onSelectConversation,
  onCreateConversation,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async (search?: string) => {
    try {
      setLoading(true);
      const response = await conversationService.getConversations(1, 50, search);
      setConversations(response.conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchTerm(value);
    
    // Debounce search
    const timeoutId = setTimeout(() => {
      loadConversations(value);
    }, 300);

    return () => clearTimeout(timeoutId);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this conversation?')) {
      return;
    }

    try {
      setDeletingId(id);
      await conversationService.deleteConversation(id);
      setConversations(conversations.filter(c => c.id !== id));
      
      // If deleting current conversation, create a new one
      if (currentConversationId === id) {
        onCreateConversation();
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('Failed to delete conversation');
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return 'Today';
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const groupConversationsByDate = (conversations: Conversation[]) => {
    const groups: { [key: string]: Conversation[] } = {};
    
    conversations.forEach(conv => {
      const dateLabel = formatDate(conv.updated_at);
      if (!groups[dateLabel]) {
        groups[dateLabel] = [];
      }
      groups[dateLabel].push(conv);
    });

    return groups;
  };

  const conversationGroups = groupConversationsByDate(conversations);

  return (
    <div className="conversation-list">
      <div className="conversation-list-header">
        <button 
          className="new-chat-button"
          onClick={onCreateConversation}
          aria-label="New Chat"
        >
          <Plus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      <div className="search-container">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          placeholder="Search conversations..."
          value={searchTerm}
          onChange={handleSearch}
          className="search-input"
        />
      </div>

      <div className="conversations-container">
        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <span>Loading conversations...</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="empty-state">
            <MessageSquare size={32} />
            <p>No conversations yet</p>
            <p className="empty-state-hint">Start a new chat to begin</p>
          </div>
        ) : (
          Object.entries(conversationGroups).map(([dateLabel, convs]) => (
            <div key={dateLabel} className="conversation-group">
              <div className="group-label">{dateLabel}</div>
              {convs.map(conversation => (
                <div
                  key={conversation.id}
                  className={`conversation-item ${
                    currentConversationId === conversation.id ? 'active' : ''
                  }`}
                  onClick={() => onSelectConversation(conversation.id)}
                >
                  <MessageSquare size={16} className="conversation-icon" />
                  <div className="conversation-content">
                    <div className="conversation-title">{conversation.title}</div>
                    {conversation.message_count !== undefined && (
                      <div className="conversation-meta">
                        {conversation.message_count} messages
                      </div>
                    )}
                  </div>
                  <button
                    className={`delete-button ${deletingId === conversation.id ? 'deleting' : ''}`}
                    onClick={(e) => handleDelete(e, conversation.id)}
                    disabled={deletingId === conversation.id}
                    aria-label="Delete conversation"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
};