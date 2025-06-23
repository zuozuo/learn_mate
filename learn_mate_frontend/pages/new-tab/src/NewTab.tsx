import '@src/NewTab.css';
import '@src/NewTab.scss';
import { t } from '@extension/i18n';
import { useStorage, withErrorBoundary, withSuspense } from '@extension/shared';
import { exampleThemeStorage } from '@extension/storage';
import { cn, ErrorDisplay, LoadingSpinner, ToggleButton } from '@extension/ui';
import { useState, useRef, useEffect } from 'react';
import { apiService, type Message } from './services/api';
import { authService, type User } from './services/auth';

// Stream Parser for handling <think> tags
class StreamParser {
  private buffer: string = '';
  private isInThinking: boolean = false;
  private thinkingContent: string = '';
  private responseContent: string = '';
  private chunkCount: number = 0;

  // Process a new chunk and return the thinking and response parts
  processChunk(chunk: string): { thinking: string; response: string; thinkingComplete: boolean } {
    this.chunkCount++;
    console.log(`🔄 StreamParser chunk #${this.chunkCount}:`, {
      incoming: JSON.stringify(chunk),
      bufferBefore: JSON.stringify(this.buffer),
      isInThinking: this.isInThinking,
      chunkLength: chunk.length
    });

    this.buffer += chunk;
    let result = { thinking: '', response: '', thinkingComplete: false };

    // Check for <think> start tag
    if (!this.isInThinking && this.buffer.includes('<think>')) {
      console.log(`🧠 Found <think> tag start in chunk #${this.chunkCount}`);
      const parts = this.buffer.split('<think>');
      console.log(`📋 Split by <think>:`, parts.map(p => JSON.stringify(p)));
      
      // Content before <think> goes to response
      if (parts[0]) {
        this.responseContent += parts[0];
        result.response = parts[0];
        console.log(`💬 Response content before thinking:`, JSON.stringify(parts[0]));
      }
      
      // Start thinking mode
      this.isInThinking = true;
      this.buffer = parts.slice(1).join('<think>'); // Keep everything after first <think>
      console.log(`🔄 Switched to thinking mode, new buffer:`, JSON.stringify(this.buffer));
    }

    // Check for </think> end tag
    if (this.isInThinking && this.buffer.includes('</think>')) {
      console.log(`🧠 Found </think> tag end in chunk #${this.chunkCount}`);
      const parts = this.buffer.split('</think>');
      console.log(`📋 Split by </think>:`, parts.map(p => JSON.stringify(p)));
      
      // Content before </think> goes to thinking
      this.thinkingContent += parts[0];
      result.thinking = parts[0];
      result.thinkingComplete = true;
      console.log(`🧠 Thinking content:`, JSON.stringify(parts[0]));
      console.log(`✅ Thinking phase completed`);
      
      // End thinking mode
      this.isInThinking = false;
      
      // Content after </think> goes to response
      const afterThinking = parts.slice(1).join('</think>');
      if (afterThinking) {
        this.responseContent += afterThinking;
        result.response = (result.response || '') + afterThinking;
        console.log(`💬 Response content after thinking:`, JSON.stringify(afterThinking));
      }
      
      this.buffer = '';
      console.log(`🔄 Switched to response mode, buffer cleared`);
    } else if (this.isInThinking) {
      // We're in thinking mode but haven't found closing tag yet
      // Output the buffered content as thinking
      if (this.buffer) {
        this.thinkingContent += this.buffer;
        result.thinking = this.buffer;
        this.buffer = '';
        console.log(`🧠 In thinking mode, outputting content:`, JSON.stringify(result.thinking));
      }
    } else {
      // We're in response mode
      this.responseContent += this.buffer;
      result.response = (result.response || '') + this.buffer;
      this.buffer = '';
      console.log(`💬 Adding to response:`, JSON.stringify(result.response));
    }

    console.log(`📊 Chunk #${this.chunkCount} result:`, {
      thinking: JSON.stringify(result.thinking),
      response: JSON.stringify(result.response),
      thinkingComplete: result.thinkingComplete,
      totalThinking: this.thinkingContent.length,
      totalResponse: this.responseContent.length
    });

    return result;
  }

  // Get the accumulated content
  getContent(): { thinking: string; response: string } {
    const content = {
      thinking: this.thinkingContent,
      response: this.responseContent
    };
    console.log(`📈 Total accumulated content:`, {
      thinkingLength: content.thinking.length,
      responseLength: content.response.length,
      thinking: content.thinking.slice(0, 100) + (content.thinking.length > 100 ? '...' : ''),
      response: content.response.slice(0, 100) + (content.response.length > 100 ? '...' : '')
    });
    return content;
  }

  // Reset the parser
  reset(): void {
    console.log(`🔄 StreamParser reset - previous stats:`, {
      totalChunks: this.chunkCount,
      finalThinkingLength: this.thinkingContent.length,
      finalResponseLength: this.responseContent.length
    });
    
    this.buffer = '';
    this.isInThinking = false;
    this.thinkingContent = '';
    this.responseContent = '';
    this.chunkCount = 0;
  }
}

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
  const [showThinking, setShowThinking] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const streamParserRef = useRef<StreamParser | null>(null);

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
        streamParserRef.current = new StreamParser();
        let assistantMessageAdded = false;
        
        // 重置状态
        setThinkingContent('');
        setShowThinking(false);
        setIsThinking(false);
        
        await apiService.sendMessageStream(
          allMessages,
          // 统一的chunk处理函数
          (chunk: string) => {
            console.log(`🔥 Received raw chunk from API:`, JSON.stringify(chunk));
            const parsed = streamParserRef.current!.processChunk(chunk);
            
            // 处理thinking内容
            if (parsed.thinking) {
              console.log(`🧠 UI: Processing thinking content:`, JSON.stringify(parsed.thinking));
              if (!showThinking) {
                console.log(`👁️ UI: Showing thinking panel for first time`);
                setShowThinking(true);
                setIsThinking(true);
              }
              setThinkingContent(prev => {
                const newContent = prev + parsed.thinking;
                console.log(`🧠 UI: Updated thinking content length: ${newContent.length}`);
                return newContent;
              });
            }
            
            // thinking完成时停止thinking状态
            if (parsed.thinkingComplete) {
              console.log(`✅ UI: Thinking phase completed, switching to response mode`);
              setIsThinking(false);
            }
            
            // 处理response内容
            if (parsed.response) {
              console.log(`💬 UI: Processing response content:`, JSON.stringify(parsed.response));
              // 如果还没有添加assistant消息，添加一个
              if (!assistantMessageAdded) {
                console.log(`➕ UI: Adding first assistant message`);
                assistantMessageAdded = true;
                const assistantMessage = { 
                  role: 'assistant' as const, 
                  content: parsed.response, 
                  timestamp: new Date() 
                };
                setMessages(prev => [...prev, assistantMessage]);
              } else {
                console.log(`🔄 UI: Updating existing assistant message`);
                // 更新现有的assistant消息
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage.role === 'assistant') {
                    const newContent = lastMessage.content + parsed.response;
                    console.log(`💬 UI: Updated response content length: ${newContent.length}`);
                    lastMessage.content = newContent;
                  }
                  return newMessages;
                });
              }
            }
          },
          () => {
            console.log(`✅ Stream completed successfully`);
            const finalContent = streamParserRef.current?.getContent();
            console.log(`📊 Final stream statistics:`, {
              thinkingLength: finalContent?.thinking.length || 0,
              responseLength: finalContent?.response.length || 0,
              assistantMessageAdded
            });
            setIsLoading(false);
            setIsThinking(false);
          },
          (error: Error) => {
            console.error('❌ Stream error:', error);
            console.log(`📊 Error state statistics:`, {
              assistantMessageAdded,
              currentThinkingLength: thinkingContent.length,
              parseState: streamParserRef.current ? 'exists' : 'null'
            });
            setIsLoading(false);
            setIsThinking(false);
            
            // 如果还没有添加助手消息，先添加一个错误消息
            if (!assistantMessageAdded) {
              console.log(`➕ Adding error message (no assistant message yet)`);
              setMessages(prev => [...prev, {
                role: 'assistant' as const,
                content: '抱歉，发生了错误。请稍后重试。',
                timestamp: new Date()
              }]);
            } else {
              console.log(`🔄 Updating existing message with error`);
              // 更新现有消息为错误状态
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage.role === 'assistant' && !lastMessage.content) {
                  lastMessage.content = '抱歉，发生了错误。请稍后重试。';
                }
                return newMessages;
              });
            }
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
      setShowThinking(false);
      setIsThinking(false);
      if (streamParserRef.current) {
        streamParserRef.current.reset();
      }
    } catch (error) {
      console.error('Failed to clear chat history:', error);
      // 即使清空失败，也清空本地消息
      setMessages([]);
      setThinkingContent('');
      setShowThinking(false);
      setIsThinking(false);
      if (streamParserRef.current) {
        streamParserRef.current.reset();
      }
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
                {messages.map((message, index) => {
                  const isLastMessage = index === messages.length - 1;
                  const isAssistantMessage = message.role === 'assistant';
                  
                  return (
                    <div key={index} className={cn("mb-6", isLastMessage && "mb-0")}>
                      {message.role === 'user' ? (
                        /* 用户消息 - 头像在卡片内部 */
                        <div className="flex justify-start">
                          <div className={cn(
                            'rounded-2xl px-4 py-3 flex items-start gap-3',
                            isLight 
                              ? 'bg-gray-100 text-gray-900' 
                              : 'bg-gray-800 text-gray-100'
                          )}>
                            <div className={cn(
                              'w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 mt-0.5',
                              isLight 
                                ? 'bg-gray-300 text-gray-700' 
                                : 'bg-gray-600 text-gray-200'
                            )}>
                              Z
                            </div>
                            <div className="whitespace-pre-wrap break-words leading-relaxed text-base">
                              {message.content}
                            </div>
                          </div>
                        </div>
                      ) : (
                        /* Assistant消息 - 无头像，简化设计 */
                        <div className="space-y-3">
                          {/* Thinking 卡片 - 在response上方 */}
                          {isLastMessage && thinkingContent && (
                            <div className={cn(
                              'rounded-lg border',
                              isLight 
                                ? 'bg-gray-50 border-gray-200' 
                                : 'bg-gray-800 border-gray-700'
                            )}>
                              {isThinkingExpanded ? (
                                <>
                                  {/* Header - 只在展开时显示 */}
                                  <div className="px-4 py-3 flex items-center justify-between">
                                    <h3 className={cn(
                                      'text-base font-medium',
                                      isLight ? 'text-gray-900' : 'text-gray-100'
                                    )}>
                                      Thought process
                                    </h3>
                                    <div className="flex items-center gap-2">
                                      <span className={cn(
                                        'text-sm',
                                        isLight ? 'text-gray-500' : 'text-gray-400'
                                      )}>
                                        1s
                                      </span>
                                      <button
                                        onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
                                        className={cn(
                                          'p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors',
                                          isLight ? 'text-gray-600' : 'text-gray-400'
                                        )}
                                      >
                                        <svg className={cn('w-5 h-5 transition-transform', isThinkingExpanded && 'rotate-180')} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                      </button>
                                    </div>
                                  </div>
                                  
                                  {/* Content */}
                                  <div className={cn(
                                    'px-4 pb-3 text-sm leading-relaxed',
                                    isLight ? 'text-gray-700' : 'text-gray-300'
                                  )}>
                                    {thinkingContent}
                                  </div>
                                </>
                              ) : (
                                /* Collapsed content - 无header，可点击整个区域展开 */
                                <button
                                  onClick={() => setIsThinkingExpanded(true)}
                                  className={cn(
                                    'w-full text-left px-4 py-3 flex items-center justify-between group',
                                    'hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors'
                                  )}
                                >
                                  <span className={cn(
                                    'text-sm leading-relaxed flex-1',
                                    isLight ? 'text-gray-700' : 'text-gray-300'
                                  )}>
                                    {(() => {
                                      // 获取第一句话（到句号、感叹号或问号为止）
                                      const firstSentence = thinkingContent.match(/^[^.!?]+[.!?]/)?.[0] || thinkingContent.split('\n')[0];
                                      return firstSentence.length < thinkingContent.length 
                                        ? firstSentence + '...' 
                                        : firstSentence;
                                    })()}
                                  </span>
                                  <span className={cn(
                                    'text-sm ml-2 shrink-0',
                                    isLight ? 'text-gray-500' : 'text-gray-400'
                                  )}>
                                    1s
                                  </span>
                                </button>
                              )}
                            </div>
                          )}
                          
                          {/* Response内容 */}
                          <div className="max-w-4xl">
                            <div className={cn(
                              'text-base leading-relaxed',
                              isLight ? 'text-gray-900' : 'text-gray-100'
                            )}>
                              {message.content || (
                                isLoading && isLastMessage && (
                                  <span className="inline-block w-2 h-4 bg-current animate-pulse" />
                                )
                              )}
                            </div>
                            
                            {/* 底部操作栏 */}
                            {isLastMessage && message.content && (
                              <div className="flex items-center gap-1 mt-3">
                                {/* Loading spinner */}
                                {isLoading && (
                                  <div className={cn(
                                    'w-6 h-6 flex items-center justify-center',
                                    isLight ? 'text-orange-500' : 'text-orange-400'
                                  )}>
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                  </div>
                                )}
                                
                                {/* Copy button */}
                                <button
                                  onClick={() => navigator.clipboard.writeText(message.content)}
                                  className={cn(
                                    'p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors',
                                    isLight ? 'text-gray-500 hover:text-gray-700' : 'text-gray-400 hover:text-gray-200'
                                  )}
                                  title="复制"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                  </svg>
                                </button>
                                
                                {/* Thumbs up */}
                                <button
                                  className={cn(
                                    'p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors',
                                    isLight ? 'text-gray-500 hover:text-gray-700' : 'text-gray-400 hover:text-gray-200'
                                  )}
                                  title="有帮助"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                                  </svg>
                                </button>
                                
                                {/* Thumbs down */}
                                <button
                                  className={cn(
                                    'p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors',
                                    isLight ? 'text-gray-500 hover:text-gray-700' : 'text-gray-400 hover:text-gray-200'
                                  )}
                                  title="无帮助"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                                  </svg>
                                </button>
                                
                                {/* Retry button */}
                                <button
                                  onClick={() => {
                                    // 获取上一个用户消息进行重试
                                    const lastUserMessageIndex = messages.slice(0, -1).findLastIndex(m => m.role === 'user');
                                    if (lastUserMessageIndex >= 0) {
                                      const lastUserMessage = messages[lastUserMessageIndex];
                                      setMessages(messages.slice(0, lastUserMessageIndex + 1));
                                      setInputMessage(lastUserMessage.content);
                                      setTimeout(() => sendMessage(), 100);
                                    }
                                  }}
                                  className={cn(
                                    'p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-1',
                                    isLight ? 'text-gray-500 hover:text-gray-700' : 'text-gray-400 hover:text-gray-200'
                                  )}
                                  title="重试"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                  </svg>
                                  <span className="text-xs">Retry</span>
                                </button>
                                
                                {/* Disclaimer text */}
                                <span className={cn(
                                  'text-xs ml-auto',
                                  isLight ? 'text-gray-400' : 'text-gray-500'
                                )}>
                                  Claude can make mistakes. Please double-check responses.
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
                
                
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