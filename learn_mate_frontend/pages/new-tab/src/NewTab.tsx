import '@src/NewTab.css';
import '@src/NewTab.scss';
import { t } from '@extension/i18n';
import { useStorage, withErrorBoundary, withSuspense } from '@extension/shared';
import { exampleThemeStorage } from '@extension/storage';
import { cn, ErrorDisplay, LoadingSpinner, ToggleButton } from '@extension/ui';
import { useState, useRef, useEffect } from 'react';
import { apiService, type Message } from './services/api';
import { authService, type User } from './services/auth';

const NewTab = () => {
  const { isLight } = useStorage(exampleThemeStorage);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [useStream, setUseStream] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初始化应用
  useEffect(() => {
    const initApp = async () => {
      try {
        // 1. 检查后端连接状态
        const connected = await apiService.checkHealth();
        setIsConnected(connected);
        
        if (!connected) {
          setIsInitializing(false);
          return;
        }

        // 2. 初始化认证
        authService.init();
        
        // 3. 检查是否已有认证用户
        let currentUser = authService.getUser();
        
        if (!currentUser && connected) {
          // 4. 创建临时会话
          try {
            currentUser = await authService.createTemporarySession();
          } catch (error) {
            console.error('Failed to create temporary session:', error);
          }
        }
        
        setUser(currentUser);

        // 5. 加载聊天历史
        if (currentUser && connected) {
          try {
            const history = await apiService.getChatHistory();
            setMessages(history.map(msg => ({ ...msg, timestamp: new Date() })));
          } catch (error) {
            console.error('Failed to load chat history:', error);
          }
        }
      } catch (error) {
        console.error('App initialization failed:', error);
      } finally {
        setIsInitializing(false);
      }
    };

    initApp();
  }, []);

  // 定期检查后端连接状态
  useEffect(() => {
    if (isInitializing) return;
    
    const checkConnection = async () => {
      const connected = await apiService.checkHealth();
      setIsConnected(connected);
    };
    
    const interval = setInterval(checkConnection, 30000); // 每30秒检查一次
    return () => clearInterval(interval);
  }, [isInitializing]);

  // 发送消息
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !isConnected || !user) return;

    const userMessage: Message = {
      role: 'user',
      content: inputMessage.trim(),
    };

    const messageWithTimestamp = { ...userMessage, timestamp: new Date() };
    setMessages(prev => [...prev, messageWithTimestamp]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // 准备发送的消息列表（包含历史消息）
      const allMessages = [...messages, userMessage];

      if (useStream) {
        // 使用流式响应
        let assistantContent = '';
        const assistantMessage = { 
          role: 'assistant' as const, 
          content: '', 
          timestamp: new Date() 
        };
        
        // 先添加空的助手消息
        setMessages(prev => [...prev, assistantMessage]);
        
        await apiService.sendMessageStream(
          allMessages,
          (chunk: string) => {
            assistantContent += chunk;
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage.role === 'assistant') {
                lastMessage.content = assistantContent;
              }
              return newMessages;
            });
          },
          () => {
            setIsLoading(false);
          },
          (error: Error) => {
            console.error('Stream error:', error);
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage.role === 'assistant' && !lastMessage.content) {
                lastMessage.content = '抱歉，发生了错误。请稍后重试。';
              }
              return newMessages;
            });
            setIsLoading(false);
          }
        );
      } else {
        // 使用普通响应
        const response = await apiService.sendMessage(allMessages);
        const assistantMessages = response.messages.filter(msg => msg.role === 'assistant');
        
        if (assistantMessages.length > 0) {
          const newMessages = assistantMessages.map(msg => ({
            ...msg,
            timestamp: new Date()
          }));
          setMessages(prev => [...prev, ...newMessages]);
        }
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant' as const,
        content: '抱歉，发生了错误。请检查网络连接或稍后重试。',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
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
  const clearChat = async () => {
    try {
      if (user && isConnected) {
        await apiService.clearChatHistory();
      }
      setMessages([]);
    } catch (error) {
      console.error('Failed to clear chat history:', error);
      // 即使清空失败，也清空本地消息
      setMessages([]);
    }
  };

  // 显示初始化加载状态
  if (isInitializing) {
    return (
      <div className={cn('min-h-screen flex items-center justify-center', isLight ? 'bg-gray-50' : 'bg-gray-900')}>
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className={cn('mt-4 text-lg', isLight ? 'text-gray-600' : 'text-gray-400')}>
            正在初始化 Learn Mate...
          </p>
        </div>
      </div>
    );
  }

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
          {/* 流式响应切换 */}
          <button
            onClick={() => setUseStream(!useStream)}
            className={cn('px-2 py-1 rounded text-xs', 
              useStream 
                ? isLight ? 'bg-blue-100 text-blue-600' : 'bg-blue-600 text-white'
                : isLight ? 'bg-gray-100 text-gray-600' : 'bg-gray-700 text-gray-300'
            )}
            title={useStream ? '使用流式响应' : '使用普通响应'}
          >
            {useStream ? '流式' : '普通'}
          </button>
          
          {/* 用户状态 */}
          {user && (
            <div className={cn('text-xs', isLight ? 'text-gray-500' : 'text-gray-400')}>
              {user.username.startsWith('temp_') ? '游客模式' : user.username}
            </div>
          )}
          
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
            disabled={isLoading}
            className={cn('px-3 py-1 rounded text-sm', 
              isLight ? 'bg-gray-100 text-gray-600 hover:bg-gray-200' : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
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
              placeholder={
                !isConnected ? "请先启动后端服务..." :
                !user ? "正在初始化用户..." :
                isLoading ? "正在思考中..." :
                "输入你的问题..."
              }
              disabled={!isConnected || !user || isLoading}
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
              disabled={!inputMessage.trim() || !isConnected || !user || isLoading}
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
