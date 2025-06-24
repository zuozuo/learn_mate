import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
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

export interface ConversationListRef {
  refresh: () => void;
}

export const ConversationList = forwardRef<ConversationListRef, ConversationListProps>(({
  currentConversationId,
  onSelectConversation,
  onCreateConversation,
  isLight = true,
}, ref) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  // 暴露刷新方法给父组件
  useImperativeHandle(ref, () => ({
    refresh: () => {
      loadConversations(searchTerm);
    }
  }));

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
    <div className={cn('conversation-list', 
      isLight ? 'bg-gray-50' : 'bg-gray-900'
    )}>
      <div className={cn('conversation-list-header',
        isLight ? 'border-gray-200' : 'border-gray-800'
      )}>
        <button 
          className={cn('new-chat-button',
            isLight 
              ? 'bg-white border-gray-200 text-gray-900 hover:bg-gray-50' 
              : 'bg-gray-800 border-gray-700 text-gray-100 hover:bg-gray-700'
          )}
          onClick={onCreateConversation}
          aria-label="New Chat"
        >
          <Plus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      <div className="search-container">
        <Search size={16} className={cn('search-icon',
          isLight ? 'text-gray-500' : 'text-gray-400'
        )} />
        <input
          type="text"
          placeholder="Search conversations..."
          value={searchTerm}
          onChange={handleSearch}
          className={cn('search-input',
            isLight 
              ? 'bg-white border-gray-200 text-gray-900 placeholder-gray-400' 
              : 'bg-gray-800 border-gray-700 text-gray-100 placeholder-gray-500'
          )}
        />
      </div>

      <div className="conversations-container">
        {loading ? (
          <div className={cn('loading-state',
            isLight ? 'text-gray-600' : 'text-gray-400'
          )}>
            <div className="spinner"></div>
            <span>Loading conversations...</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className={cn('empty-state',
            isLight ? 'text-gray-500' : 'text-gray-400'
          )}>
            <MessageSquare size={32} />
            <p>No conversations yet</p>
            <p className={cn('empty-state-hint',
              isLight ? 'text-gray-400' : 'text-gray-500'
            )}>Start a new chat to begin</p>
          </div>
        ) : (
          Object.entries(conversationGroups).map(([dateLabel, convs]) => (
            <div key={dateLabel} className="conversation-group">
              <div className={cn('group-label',
                isLight ? 'text-gray-600' : 'text-gray-400'
              )}>{dateLabel}</div>
              {convs.map(conversation => (
                <div
                  key={conversation.id}
                  className={cn(
                    'conversation-item',
                    currentConversationId === conversation.id && 'active',
                    isLight ? 'hover:bg-gray-100' : 'hover:bg-gray-800',
                    currentConversationId === conversation.id && (
                      isLight ? 'bg-white shadow-sm' : 'bg-gray-800'
                    )
                  )}
                  onClick={() => onSelectConversation(conversation.id)}
                >
                  <MessageSquare size={16} className={cn('conversation-icon',
                    isLight ? 'text-gray-500' : 'text-gray-400'
                  )} />
                  <div className="conversation-content">
                    <div className={cn('conversation-title',
                      isLight ? 'text-gray-900' : 'text-gray-100',
                      currentConversationId === conversation.id && 'font-semibold'
                    )}>{conversation.title}</div>
                    {conversation.message_count !== undefined && (
                      <div className={cn('conversation-meta',
                        isLight ? 'text-gray-500' : 'text-gray-400'
                      )}>
                        {conversation.message_count} messages
                      </div>
                    )}
                  </div>
                  <button
                    className={cn(
                      'delete-button',
                      deletingId === conversation.id && 'deleting',
                      isLight 
                        ? 'text-gray-400 hover:text-red-600 hover:bg-red-50' 
                        : 'text-gray-500 hover:text-red-400 hover:bg-red-900/20'
                    )}
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
});