import { conversationService } from '../services/conversation';
import { cn } from '@extension/ui';
import { Search, Plus } from 'lucide-react';
import { useState, useEffect } from 'react';
import type { Conversation } from '../services/conversation';
import type React from 'react';

interface ChatHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectConversation: (id: string) => void;
  onCreateConversation: () => void;
  isLight?: boolean;
}

export const ChatHistory: React.FC<ChatHistoryProps> = ({
  isOpen,
  onClose,
  onSelectConversation,
  onCreateConversation,
  isLight = true,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredConversations, setFilteredConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    if (isOpen) {
      loadConversations();
    }
  }, [isOpen]);

  useEffect(() => {
    if (searchTerm) {
      const filtered = conversations.filter(conv => conv.title.toLowerCase().includes(searchTerm.toLowerCase()));
      setFilteredConversations(filtered);
    } else {
      setFilteredConversations(conversations);
    }
  }, [searchTerm, conversations]);

  const loadConversations = async () => {
    try {
      setLoading(true);
      const response = await conversationService.getConversations(1, 100);
      setConversations(response.conversations);
      setFilteredConversations(response.conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectConversation = (id: string) => {
    onSelectConversation(id);
    onClose();
  };

  const handleCreateConversation = () => {
    onCreateConversation();
    onClose();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 24) {
      return `Last message ${diffHours} hours ago`;
    } else if (diffDays === 1) {
      return 'Last message 1 day ago';
    } else {
      return `Last message ${diffDays} days ago`;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        onKeyDown={e => {
          if (e.key === 'Escape') {
            onClose();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Close dialog"
      />

      {/* 对话历史面板 */}
      <div
        className={cn(
          'relative z-10 flex h-[80vh] w-[90vw] max-w-5xl flex-col rounded-lg shadow-xl',
          isLight ? 'bg-white' : 'bg-gray-900',
        )}>
        {/* 头部 */}
        <div
          className={cn(
            'flex items-center justify-between border-b px-6 py-4',
            isLight ? 'border-gray-200' : 'border-gray-800',
          )}>
          <h2 className={cn('text-xl font-semibold', isLight ? 'text-gray-900' : 'text-white')}>Your chat history</h2>
          <div className="flex items-center gap-3">
            <button
              onClick={handleCreateConversation}
              className={cn(
                'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                isLight ? 'bg-black text-white hover:bg-gray-800' : 'bg-white text-black hover:bg-gray-200',
              )}>
              <Plus size={16} />
              New chat
            </button>
            <button
              onClick={onClose}
              className={cn(
                'rounded-lg p-2 transition-colors',
                isLight ? 'text-gray-500 hover:bg-gray-100' : 'text-gray-400 hover:bg-gray-800',
              )}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* 搜索框 */}
        <div className="border-b border-inherit px-6 py-4">
          <div className="relative">
            <Search
              size={20}
              className={cn('absolute left-3 top-1/2 -translate-y-1/2', isLight ? 'text-gray-400' : 'text-gray-500')}
            />
            <input
              type="text"
              placeholder="Search your chats..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className={cn(
                'w-full rounded-lg border py-3 pl-10 pr-4 text-sm outline-none transition-colors',
                isLight
                  ? 'border-gray-200 bg-white text-gray-900 placeholder-gray-400 focus:border-gray-300'
                  : 'border-gray-700 bg-gray-800 text-white placeholder-gray-500 focus:border-gray-600',
              )}
            />
          </div>
        </div>

        {/* 对话列表 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <div className={cn('text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>Loading conversations...</div>
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center">
              <div className={cn('text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>
                {searchTerm ? `No chats found for "${searchTerm}"` : 'No conversations yet'}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className={cn('mb-4 text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>
                You have {filteredConversations.length} previous chats with Claude
              </div>
              {filteredConversations.map(conversation => (
                <button
                  key={conversation.id}
                  onClick={() => handleSelectConversation(conversation.id)}
                  className={cn(
                    'w-full rounded-lg border p-4 text-left transition-colors',
                    isLight ? 'border-gray-200 hover:bg-gray-50' : 'border-gray-800 hover:bg-gray-800',
                  )}>
                  <div className={cn('font-medium', isLight ? 'text-gray-900' : 'text-white')}>
                    {conversation.title}
                  </div>
                  <div className={cn('mt-1 text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>
                    {formatDate(conversation.updated_at)}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
