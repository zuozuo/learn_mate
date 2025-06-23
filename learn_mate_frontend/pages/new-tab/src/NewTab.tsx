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
  const [currentThinking, setCurrentThinking] = useState(''); // 当前正在接收的thinking内容
  const [showThinking, setShowThinking] = useState(false); // 是否显示thinking卡片
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true); // thinking卡片是否展开
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const currentThinkingRef = useRef(''); // 用于在闭包中获取最新的thinking内容

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
        let hasReceivedThinking = false;
        
        // 重置状态
        setCurrentThinking('');
        setShowThinking(false);
        setIsThinking(false);
        currentThinkingRef.current = '';
        
        await apiService.sendMessageStream(
          allMessages,
          // thinking 内容流式更新
          (thinkingChunk: string) => {
            if (!hasReceivedThinking) {
              hasReceivedThinking = true;
              setShowThinking(true);
              setIsThinking(true);
            }
            currentThinkingRef.current += thinkingChunk;
            setCurrentThinking(prev => prev + thinkingChunk);
          },
          // response 内容流式更新
          (responseChunk: string) => {
            // 如果是第一个 response chunk，说明 thinking 阶段结束，开始response
            if (assistantContent === '') {
              setIsThinking(false); // thinking阶段结束
              // 保存thinking内容到thinkingContent用于显示
              setThinkingContent(currentThinkingRef.current);
              
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
            // 保存thinking内容，不要清空
            if (hasReceivedThinking && currentThinkingRef.current) {
              setThinkingContent(currentThinkingRef.current);
            }
          },
          (error: Error) => {
            console.error('Stream error:', error);
            setIsLoading(false);
            setIsThinking(false);
            // 保留thinking内容，不要清空
            
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
      // 清空thinking相关状态
      setThinkingContent('');
      setCurrentThinking('');
      setShowThinking(false);
      setIsThinking(false);
      currentThinkingRef.current = '';
    } catch (error) {
      console.error('Failed to clear chat history:', error);
      // 即使清空失败，也清空本地消息
      setMessages([]);
      setThinkingContent('');
      setCurrentThinking('');
      setShowThinking(false);
      setIsThinking(false);
      currentThinkingRef.current = '';
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
                          {/* 如果是assistant消息且内容为空且正在加载，显示loading指示器 */}
                          {message.role === 'assistant' && !message.content && isLoading && (
                            <div className="flex items-center space-x-2 text-sm opacity-70">
                              <div className="flex space-x-1">
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-orange-500' : 'bg-orange-400'
                                )}></div>
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-orange-500' : 'bg-orange-400'
                                )}></div>
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-orange-500' : 'bg-orange-400'
                                )}></div>
                              </div>
                              <span>正在回复...</span>
                            </div>
                          )}
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
                
                {/* Thinking 卡片 - 独立显示，与消息分离 */}
                {(showThinking || thinkingContent) && (
                  <div className="mb-6">
                    <div className={cn(
                      'rounded-xl border px-4 py-3 loading-message',
                      isLight 
                        ? 'bg-blue-50 border-blue-200' 
                        : 'bg-blue-500/10 border-blue-500/20'
                    )}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <div className="flex space-x-1">
                            {isThinking ? (
                              <>
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-blue-500' : 'bg-blue-400'
                                )}></div>
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-blue-500' : 'bg-blue-400'
                                )}></div>
                                <div className={cn(
                                  'w-1.5 h-1.5 rounded-full thinking-dot',
                                  isLight ? 'bg-blue-500' : 'bg-blue-400'
                                )}></div>
                              </>
                            ) : (
                              <div className={cn(
                                'w-4 h-4 rounded-full flex items-center justify-center',
                                isLight ? 'bg-blue-100 text-blue-600' : 'bg-blue-500/20 text-blue-400'
                              )}>
                                🧠
                              </div>
                            )}
                          </div>
                          <span className={cn(
                            'text-sm font-medium',
                            isLight ? 'text-blue-700' : 'text-blue-300'
                          )}>
                            {isThinking ? 'Thinking...' : 'Thought process'}
                          </span>
                        </div>
                        
                        {/* 展开收起按钮 */}
                        {(thinkingContent && !isThinking) && (
                          <button
                            onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
                            className={cn(
                              'text-xs px-2 py-1 rounded transition-colors',
                              isLight 
                                ? 'text-blue-600 hover:bg-blue-100' 
                                : 'text-blue-400 hover:bg-blue-500/10'
                            )}
                          >
                            {isThinkingExpanded ? '收起' : '展开'}
                          </button>
                        )}
                      </div>
                      
                      {/* 思考内容 */}
                      <div className={cn(
                        'text-sm leading-relaxed whitespace-pre-wrap transition-all duration-200',
                        isLight ? 'text-blue-800' : 'text-blue-200'
                      )}>
                        {isThinking ? currentThinking : (
                          isThinkingExpanded ? thinkingContent : 
                          (thinkingContent ? `${thinkingContent.slice(0, 100)}${thinkingContent.length > 100 ? '...' : ''}` : '')
                        )}
                      </div>
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