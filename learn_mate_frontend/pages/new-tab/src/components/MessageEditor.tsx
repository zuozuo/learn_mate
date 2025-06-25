import { cn } from '@extension/ui';
import { useState, useRef, useEffect } from 'react';

interface MessageEditorProps {
  content: string;
  onSave: (newContent: string) => void;
  onCancel: () => void;
  isLight: boolean;
  isLoading?: boolean;
}

export const MessageEditor: React.FC<MessageEditorProps> = ({
  content,
  onSave,
  onCancel,
  isLight,
  isLoading = false,
}) => {
  const [editedContent, setEditedContent] = useState(content);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // 自动聚焦并调整高度
    if (textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, []);

  const handleSave = () => {
    if (editedContent.trim() && editedContent !== content) {
      onSave(editedContent.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditedContent(e.target.value);
    // 自动调整高度
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={editedContent}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
        className={cn(
          'w-full resize-none rounded-lg border-2 p-3 pr-24 text-base transition-all',
          'focus:outline-none',
          isLight
            ? 'border-orange-300 bg-white text-gray-900 focus:border-orange-400'
            : 'border-orange-600 bg-gray-800 text-gray-100 focus:border-orange-500',
          isLoading && 'cursor-not-allowed opacity-50',
        )}
        style={{ minHeight: '60px' }}
      />
      <div className="absolute bottom-2 right-2 flex gap-1">
        <button
          onClick={handleSave}
          disabled={!editedContent.trim() || editedContent === content || isLoading}
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-md transition-all',
            editedContent.trim() && editedContent !== content && !isLoading
              ? 'bg-orange-500 text-white hover:bg-orange-600'
              : isLight
                ? 'bg-gray-200 text-gray-400'
                : 'bg-gray-700 text-gray-500',
            'disabled:cursor-not-allowed',
          )}
          title="发送编辑 (Enter)">
          {isLoading ? (
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          )}
        </button>
        <button
          onClick={onCancel}
          disabled={isLoading}
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-md transition-all',
            isLight ? 'bg-gray-200 text-gray-600 hover:bg-gray-300' : 'bg-gray-700 text-gray-400 hover:bg-gray-600',
            'disabled:cursor-not-allowed disabled:opacity-50',
          )}
          title="取消 (Esc)">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};
