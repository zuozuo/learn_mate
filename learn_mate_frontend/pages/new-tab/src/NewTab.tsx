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
  const [thinkingContent, setThinkingContent] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 获取问候语
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "早上好";
    if (hour < 18) return "下午好";
    return "晚上好";
  };

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
        setThinkingContent('');
        setIsThinking(true);
        
        await apiService.sendMessageStream(
          allMessages,
          // thinking 内容流式更新
          (thinkingChunk: string) => {
            setThinkingContent(prev => prev + thinkingChunk);
          },
          // response 内容流式更新
          (responseChunk: string) => {
            // 如果是第一个 response chunk，说明 thinking 阶段结束
            if (assistantContent === '') {
              setIsThinking(false);
              const assistantMessage = { 
                role: 'assistant' as const, 
                content: '', 
                timestamp: new Date() 
              };
              setMessages(prev => [...prev, assistantMessage]);
            }
            
            assistantContent += responseChunk;
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
            setIsThinking(false);
            setThinkingContent('');
          },
          (error: Error) => {
            console.error('Stream error:', error);
            setIsLoading(false);
            setIsThinking(false);
            setThinkingContent('');
            
            // 如果还没有添加助手消息，先添加一个
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              
              if (!lastMessage || lastMessage.role !== 'assistant') {
                newMessages.push({
                  role: 'assistant' as const,
                  content: '抱歉，发生了错误。请稍后重试。',
                  timestamp: new Date()
                });
              } else if (!lastMessage.content) {
                lastMessage.content = '抱歉，发生了错误。请稍后重试。';
              }
              
              return newMessages;
            });
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

  // 处理输入框自动调整高度
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputMessage(e.target.value);
    
    // 自动调整高度
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
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
      <div className={cn('min-h-screen flex items-center justify-center', 
        isLight ? 'bg-white' : 'bg-gray-950')}>
        <div className="text-center">
          <div className="mb-6">
            <div className={cn('w-16 h-16 rounded-full mx-auto flex items-center justify-center text-2xl',
              isLight ? 'bg-orange-100 text-orange-600' : 'bg-orange-500/20 text-orange-400')}>
              🎓
            </div>
          </div>
          <LoadingSpinner size="lg" />
          <p className={cn('mt-4 text-lg font-medium', 
            isLight ? 'text-gray-900' : 'text-gray-100')}>
            正在初始化 Learn Mate...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('min-h-screen', isLight ? 'bg-white' : 'bg-gray-950')}>
      {/* 左侧边栏 */}
      <div className={cn('fixed left-0 top-0 h-full w-64 border-r flex flex-col',
        isLight ? 'bg-gray-50 border-gray-200' : 'bg-gray-900 border-gray-800')}>
        
        {/* 顶部标题 */}
        <div className="p-4 border-b border-inherit">
          <div className="flex items-center space-x-3">
            <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center text-lg',
              isLight ? 'bg-orange-100 text-orange-600' : 'bg-orange-500/20 text-orange-400')}>
              🎓
            </div>
            <div>
              <h1 className={cn('text-lg font-semibold', 
                isLight ? 'text-gray-900' : 'text-white')}>
                Learn Mate
              </h1>
            </div>
          </div>
        </div>

        {/* 聊天历史占位符 */}
        <div className="flex-1 p-4">
          <div className={cn('text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>
            聊天记录
          </div>
        </div>

        {/* 底部设置 */}
        <div className="p-4 border-t border-inherit space-y-3">
          {/* 连接状态 */}
          <div className="flex items-center justify-between">
            <span className={cn('text-sm', isLight ? 'text-gray-600' : 'text-gray-300')}>
              连接状态
            </span>
            <div className="flex items-center space-x-1">
              <div className={cn('w-2 h-2 rounded-full', 
                isConnected ? 'bg-green-500' : 'bg-red-500')} />
              <span className={cn('text-xs', isLight ? 'text-gray-500' : 'text-gray-400')}>
                {isConnected ? '已连接' : '未连接'}
              </span>
            </div>
          </div>

          {/* 用户信息 */}
          {user && (
            <div className="flex items-center justify-between">
              <span className={cn('text-sm', isLight ? 'text-gray-600' : 'text-gray-300')}>
                用户
              </span>
              <span className={cn('text-xs', isLight ? 'text-gray-500' : 'text-gray-400')}>
                {user.username.startsWith('temp_') ? '游客模式' : user.username}
              </span>
            </div>
          )}

          {/* 功能按钮 */}
          <div className="flex space-x-2">
            <button
              onClick={() => setUseStream(!useStream)}
              className={cn('flex-1 px-2 py-1 rounded text-xs font-medium transition-colors',
                useStream 
                  ? isLight ? 'bg-blue-100 text-blue-700' : 'bg-blue-500/20 text-blue-400'
                  : isLight ? 'bg-gray-100 text-gray-600' : 'bg-gray-800 text-gray-400'
              )}
            >
              {useStream ? '流式' : '普通'}
            </button>
            
            <button
              onClick={clearChat}
              disabled={isLoading}
              className={cn('flex-1 px-2 py-1 rounded text-xs font-medium transition-colors',
                isLight ? 'bg-gray-100 text-gray-600 hover:bg-gray-200' : 'bg-gray-800 text-gray-400 hover:bg-gray-700',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              清空
            </button>
            
            <ToggleButton onClick={exampleThemeStorage.toggle} className="p-1">
              <span className="text-lg">{isLight ? '🌙' : '☀️'}</span>
            </ToggleButton>
          </div>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="ml-64 flex flex-col min-h-screen">
        {messages.length === 0 ? (
          /* 欢迎界面 */
          <div className="flex-1 flex flex-col items-center justify-center px-8">
            <div className="max-w-2xl w-full text-center">
              {/* 问候语 */}
              <div className="mb-12">
                <div className={cn('text-2xl mb-2 flex items-center justify-center space-x-2',
                  isLight ? 'text-gray-900' : 'text-gray-100')}>
                  <span>🌟</span>
                  <span className="font-medium">{getGreeting()}, 学习者</span>
                </div>
                <p className={cn('text-lg', isLight ? 'text-gray-600' : 'text-gray-400')}>
                  今天想学点什么？
                </p>
              </div>

              {/* 输入框 */}
              <div className="relative">
                <textarea
                  ref={inputRef}
                  value={inputMessage}
                  onChange={handleInputChange}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    !isConnected ? "请先启动后端服务..." :
                    !user ? "正在初始化用户..." :
                    isLoading ? "正在思考中..." :
                    "向 Learn Mate 提问..."
                  }
                  disabled={!isConnected || !user || isLoading}
                  className={cn(
                    'w-full resize-none rounded-2xl border-2 p-4 pr-16 text-lg focus:outline-none transition-all duration-200',
                    'placeholder:text-gray-400',
                    isLight 
                      ? 'bg-white border-gray-200 text-gray-900 focus:border-orange-400 shadow-sm focus:shadow-md' 
                      : 'bg-gray-900 border-gray-700 text-white focus:border-orange-500',
                    (!isConnected || isLoading) && 'opacity-50 cursor-not-allowed'
                  )}
                  rows={1}
                  style={{ minHeight: '60px', maxHeight: '160px' }}
                />
                
                {/* 发送按钮 */}
                <button
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || !isConnected || !user || isLoading}
                  className={cn(
                    'absolute right-3 top-1/2 transform -translate-y-1/2',
                    'w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200',
                    inputMessage.trim() && isConnected && user && !isLoading
                      ? 'bg-orange-500 hover:bg-orange-600 text-white shadow-md hover:shadow-lg' 
                      : isLight ? 'bg-gray-200 text-gray-400' : 'bg-gray-700 text-gray-500',
                    'disabled:cursor-not-allowed'
                  )}
                >
                  {isLoading ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"/>
                    </svg>
                  )}
                </button>
              </div>

              {/* 快捷操作提示 */}
              <div className={cn('mt-6 text-sm flex items-center justify-center space-x-6',
                isLight ? 'text-gray-500' : 'text-gray-400')}>
                <div className="flex items-center space-x-1">
                  <kbd className={cn('px-2 py-1 rounded text-xs',
                    isLight ? 'bg-gray-100 text-gray-600' : 'bg-gray-800 text-gray-300')}>
                    Enter
                  </kbd>
                  <span>发送</span>
                </div>
                <div className="flex items-center space-x-1">
                  <kbd className={cn('px-2 py-1 rounded text-xs',
                    isLight ? 'bg-gray-100 text-gray-600' : 'bg-gray-800 text-gray-300')}>
                    Shift + Enter
                  </kbd>
                  <span>换行</span>
                </div>
              </div>

              {!isConnected && (
                <div className={cn('mt-6 p-4 rounded-lg',
                  isLight ? 'bg-red-50 text-red-700' : 'bg-red-500/10 text-red-400')}>
                  <p className="text-sm">
                    无法连接到后端服务，请确保后端服务已启动 (http://localhost:8000)
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* 聊天界面 */
          <div className="flex-1 flex flex-col">
            {/* 消息列表 */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-4xl mx-auto px-8 py-8 space-y-8">
                {messages.map((message, index) => (
                  <div key={index} className="flex items-start space-x-4">
                    {/* 头像 */}
                    <div className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold shrink-0',
                      message.role === 'user'
                        ? isLight 
                          ? 'bg-gray-600 text-white' 
                          : 'bg-gray-700 text-white'
                        : isLight 
                          ? 'bg-orange-100 text-orange-600' 
                          : 'bg-orange-500/20 text-orange-400'
                    )}>
                      {message.role === 'user' ? 'Z' : '🎓'}
                    </div>
                    
                    {/* 消息内容 */}
                    <div className="flex-1 min-w-0">
                      <div className={cn(
                        'rounded-2xl px-6 py-4',
                        message.role === 'user' 
                          ? isLight 
                            ? 'bg-gray-100 text-gray-900' 
                            : 'bg-gray-800 text-gray-100'
                          : isLight 
                            ? 'bg-gray-100 text-gray-900' 
                            : 'bg-gray-800 text-gray-100'
                      )}>
                        <div className="whitespace-pre-wrap break-words leading-relaxed">
                          {message.content}
                        </div>
                        {message.timestamp && (
                          <div className={cn('text-xs mt-2 opacity-70')}>
                            {message.timestamp.toLocaleTimeString()}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                
                {/* 加载状态 */}
                {isLoading && (
                  <div className="flex items-start space-x-4">
                    {/* AI 头像 */}
                    <div className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0',
                      isLight 
                        ? 'bg-orange-100 text-orange-600' 
                        : 'bg-orange-500/20 text-orange-400'
                    )}>
                      🎓
                    </div>
                    
                    {/* 思考和回复内容 */}
                    <div className="flex-1 min-w-0">
                      {/* 思考过程卡片 - 显示实时思考内容 */}
                      {isThinking && (
                        <div className={cn(
                          'rounded-xl border px-4 py-3 mb-3 loading-message',
                          isLight 
                            ? 'bg-gray-50 border-gray-200 text-gray-700' 
                            : 'bg-gray-800/50 border-gray-700 text-gray-300'
                        )}>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <div className="flex space-x-1">
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-gray-500' : 'bg-gray-400'
                                )}></div>
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-gray-500' : 'bg-gray-400'
                                )}></div>
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-gray-500' : 'bg-gray-400'
                                )}></div>
                              </div>
                              <span className="text-sm font-medium">
                                思考过程
                              </span>
                            </div>
                            <div className="flex items-center space-x-2 text-xs text-gray-500">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                              </svg>
                              <span>1s</span>
                              <svg className="w-3 h-3 transform rotate-180" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd"/>
                              </svg>
                            </div>
                          </div>
                          {/* 显示实时思考内容 */}
                          {thinkingContent && (
                            <div className="text-sm leading-relaxed whitespace-pre-wrap">
                              {thinkingContent}
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* 实际回复气泡 */}
                      {(!isThinking && isLoading) && (
                        <div className={cn(
                          'rounded-2xl px-6 py-4',
                          isLight 
                            ? 'bg-gray-100 text-gray-900' 
                            : 'bg-gray-800 text-gray-100'
                        )}>
                          <div className="flex items-center space-x-3">
                            <div className="flex space-x-1">
                              <div className={cn(
                                'w-2 h-2 rounded-full thinking-dot',
                                isLight ? 'bg-orange-500' : 'bg-orange-400'
                              )}></div>
                              <div className={cn(
                                'w-2 h-2 rounded-full thinking-dot',
                                isLight ? 'bg-orange-500' : 'bg-orange-400'
                              )}></div>
                              <div className={cn(
                                'w-2 h-2 rounded-full thinking-dot',
                                isLight ? 'bg-orange-500' : 'bg-orange-400'
                              )}></div>
                            </div>
                            <span className="text-sm">
                              Learn Mate 正在回复...
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* 底部输入区域 */}
            <div className="border-t border-inherit">
              <div className="max-w-4xl mx-auto px-8 py-6">
                <div className="relative">
                  <textarea
                    ref={inputRef}
                    value={inputMessage}
                    onChange={handleInputChange}
                    onKeyPress={handleKeyPress}
                    placeholder={
                      !isConnected ? "请先启动后端服务..." :
                      !user ? "正在初始化用户..." :
                      isLoading ? "正在思考中..." :
                      "继续对话..."
                    }
                    disabled={!isConnected || !user || isLoading}
                    className={cn(
                      'w-full resize-none rounded-2xl border-2 p-4 pr-16 focus:outline-none transition-all duration-200',
                      'placeholder:text-gray-400',
                      isLight 
                        ? 'bg-white border-gray-200 text-gray-900 focus:border-orange-400 shadow-sm focus:shadow-md' 
                        : 'bg-gray-900 border-gray-700 text-white focus:border-orange-500',
                      (!isConnected || isLoading) && 'opacity-50 cursor-not-allowed'
                    )}
                    rows={1}
                    style={{ minHeight: '56px', maxHeight: '120px' }}
                  />
                  
                  {/* 发送按钮 */}
                  <button
                    onClick={sendMessage}
                    disabled={!inputMessage.trim() || !isConnected || !user || isLoading}
                    className={cn(
                      'absolute right-3 top-1/2 transform -translate-y-1/2',
                      'w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200',
                      inputMessage.trim() && isConnected && user && !isLoading
                        ? 'bg-orange-500 hover:bg-orange-600 text-white' 
                        : isLight ? 'bg-gray-200 text-gray-400' : 'bg-gray-700 text-gray-500',
                      'disabled:cursor-not-allowed'
                    )}
                  >
                    {isLoading ? (
                      <LoadingSpinner size="sm" />
                    ) : (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"/>
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default withErrorBoundary(withSuspense(NewTab, <LoadingSpinner />), ErrorDisplay);