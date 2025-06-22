import '@src/NewTab.css';
import '@src/NewTab.scss';
import { t } from '@extension/i18n';
import { useStorage, withErrorBoundary, withSuspense } from '@extension/shared';
import { exampleThemeStorage } from '@extension/storage';
import { cn, ErrorDisplay, LoadingSpinner, ToggleButton } from '@extension/ui';
import { useState, useRef, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
}

const NewTab = () => {
  const { isLight } = useStorage(exampleThemeStorage);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 检查后端连接状态
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch('http://localhost:8000/health');
        setIsConnected(response.ok);
      } catch (error) {
        setIsConnected(false);
      }
    };
    
    checkConnection();
    const interval = setInterval(checkConnection, 30000); // 每30秒检查一次
    return () => clearInterval(interval);
  }, []);

  // 发送消息
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // 这里暂时模拟响应，后续会实现真实的 API 调用
      setTimeout(() => {
        const assistantMessage: Message = {
          role: 'assistant',
          content: `你好！我收到了你的消息："${userMessage.content}"。我是 Learn Mate，你的学习助手。目前我正在开发中，很快就会有更多功能！`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, assistantMessage]);
        setIsLoading(false);
      }, 1000);
    } catch (error) {
      console.error('Error sending message:', error);
      setIsLoading(false);
    }
  };

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // 清空聊天历史
  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div className={cn('min-h-screen flex flex-col', isLight ? 'bg-gray-50' : 'bg-gray-900')}>
      {/* 头部 */}
      <header className={cn('border-b p-4 flex items-center justify-between', 
        isLight ? 'bg-white border-gray-200' : 'bg-gray-800 border-gray-700')}>
        <div className="flex items-center space-x-3">
          <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center',
            isLight ? 'bg-blue-100 text-blue-600' : 'bg-blue-600 text-white')}>
            🎓
          </div>
          <div>
            <h1 className={cn('text-xl font-semibold', isLight ? 'text-gray-900' : 'text-white')}>
              Learn Mate
            </h1>
            <p className={cn('text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>
              你的智能学习助手
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* 连接状态指示器 */}
          <div className="flex items-center space-x-1">
            <div className={cn('w-2 h-2 rounded-full', isConnected ? 'bg-green-500' : 'bg-red-500')} />
            <span className={cn('text-xs', isLight ? 'text-gray-500' : 'text-gray-400')}>
              {isConnected ? '已连接' : '未连接'}
            </span>
          </div>
          
          <ToggleButton onClick={exampleThemeStorage.toggle} className="p-2">
            {isLight ? '🌙' : '☀️'}
          </ToggleButton>
          
          <button
            onClick={clearChat}
            className={cn('px-3 py-1 rounded text-sm', 
              isLight ? 'bg-gray-100 text-gray-600 hover:bg-gray-200' : 'bg-gray-700 text-gray-300 hover:bg-gray-600')}
          >
            清空
          </button>
        </div>
      </header>

      {/* 聊天区域 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className={cn('w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center',
                  isLight ? 'bg-blue-100 text-blue-600' : 'bg-blue-600 text-white')}>
                  🤖
                </div>
                <h3 className={cn('text-lg font-medium mb-2', isLight ? 'text-gray-900' : 'text-white')}>
                  欢迎使用 Learn Mate！
                </h3>
                <p className={cn('text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>
                  我是你的智能学习助手，可以帮助你学习、解答问题、整理知识点。
                  <br />
                  开始对话吧！
                </p>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}>
                <div className={cn('max-w-xs lg:max-w-md xl:max-w-lg rounded-lg p-3',
                  message.role === 'user' 
                    ? isLight ? 'bg-blue-500 text-white' : 'bg-blue-600 text-white'
                    : isLight ? 'bg-white text-gray-900 border border-gray-200' : 'bg-gray-800 text-white border border-gray-700'
                )}>
                  <div className="whitespace-pre-wrap break-words">{message.content}</div>
                  {message.timestamp && (
                    <div className={cn('text-xs mt-1 opacity-70')}>
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          
          {/* 加载状态 */}
          {isLoading && (
            <div className="flex justify-start">
              <div className={cn('rounded-lg p-3 flex items-center space-x-2',
                isLight ? 'bg-white border border-gray-200' : 'bg-gray-800 border border-gray-700')}>
                <LoadingSpinner size="sm" />
                <span className={cn('text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>
                  正在思考...
                </span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div className={cn('border-t p-4', isLight ? 'bg-white border-gray-200' : 'bg-gray-800 border-gray-700')}>
          <div className="flex space-x-2">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isConnected ? "输入你的问题..." : "请先启动后端服务..."}
              disabled={!isConnected || isLoading}
              className={cn(
                'flex-1 resize-none rounded-lg border p-3 focus:outline-none focus:ring-2 focus:ring-blue-500',
                isLight 
                  ? 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-500' 
                  : 'bg-gray-700 border-gray-600 text-white placeholder-gray-400',
                (!isConnected || isLoading) && 'opacity-50 cursor-not-allowed'
              )}
              rows={1}
              style={{ minHeight: '44px', maxHeight: '120px' }}
            />
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || !isConnected || isLoading}
              className={cn(
                'px-4 py-2 rounded-lg font-medium transition-colors',
                'bg-blue-500 hover:bg-blue-600 text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-500'
              )}
            >
              发送
            </button>
          </div>
          
          {!isConnected && (
            <p className={cn('text-xs mt-2', isLight ? 'text-red-500' : 'text-red-400')}>
              无法连接到后端服务，请确保后端服务已启动 (http://localhost:8000)
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default withErrorBoundary(withSuspense(NewTab, <LoadingSpinner />), ErrorDisplay);
