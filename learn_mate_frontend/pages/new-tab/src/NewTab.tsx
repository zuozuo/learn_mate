import '@src/NewTab.css';
import '@src/NewTab.scss';
import { ConversationList } from './components/ConversationList';
import { Login } from './components/Login';
import { MessageEditor } from './components/MessageEditor';
import { VersionSelector } from './components/VersionSelector';
import { useAuth } from './contexts/AuthContext';
import { apiService } from './services/api';
import { authService } from './services/auth';
import { conversationService } from './services/conversation';
import { messageBranchService } from './services/messageBranch';
import { useStorage, withErrorBoundary, withSuspense } from '@extension/shared';
import { exampleThemeStorage } from '@extension/storage';
import { cn, ErrorDisplay, LoadingSpinner } from '@extension/ui';
import { Plus, MessageSquare } from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import type { ConversationListRef } from './components/ConversationList';
import type { Message as ApiMessage } from './services/api';

// 扩展Message类型以包含thinking内容和版本信息
interface Message extends ApiMessage {
  thinking?: string;
  timestamp?: Date;
  id?: string;
  version_number?: number;
  branch_id?: string;
  branch_name?: string;
  versions?: Array<{
    id: string;
    content: string;
    version_number: number;
    branch_id: string;
    branch_name?: string;
  }>;
}

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

    // 处理JSON编码的字符串（如果chunk被JSON编码了）
    let processedChunk = chunk;
    if (chunk.startsWith('"') && chunk.endsWith('"')) {
      try {
        processedChunk = JSON.parse(chunk);
      } catch {
        // 如果解析失败，保持原样
      }
    }

    console.log(`🔄 StreamParser chunk #${this.chunkCount}:`, {
      incoming: JSON.stringify(chunk),
      processed: JSON.stringify(processedChunk),
      bufferBefore: JSON.stringify(this.buffer),
      isInThinking: this.isInThinking,
      chunkLength: processedChunk.length,
    });

    this.buffer += processedChunk;
    const result = { thinking: '', response: '', thinkingComplete: false };

    // Check for <think> start tag
    if (!this.isInThinking && this.buffer.includes('<think>')) {
      console.log(`🧠 Found <think> tag start in chunk #${this.chunkCount}`);
      const parts = this.buffer.split('<think>');
      console.log(
        `📋 Split by <think>:`,
        parts.map(p => JSON.stringify(p)),
      );

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
      console.log(
        `📋 Split by </think>:`,
        parts.map(p => JSON.stringify(p)),
      );

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
      totalResponse: this.responseContent.length,
    });

    return result;
  }

  // Get the accumulated content
  getContent(): { thinking: string; response: string } {
    const content = {
      thinking: this.thinkingContent,
      response: this.responseContent,
    };
    console.log(`📈 Total accumulated content:`, {
      thinkingLength: content.thinking.length,
      responseLength: content.response.length,
      thinking: content.thinking.slice(0, 100) + (content.thinking.length > 100 ? '...' : ''),
      response: content.response.slice(0, 100) + (content.response.length > 100 ? '...' : ''),
    });
    return content;
  }

  // Reset the parser
  reset(): void {
    console.log(`🔄 StreamParser reset - previous stats:`, {
      totalChunks: this.chunkCount,
      finalThinkingLength: this.thinkingContent.length,
      finalResponseLength: this.responseContent.length,
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
  const { user, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [useStream] = useState(true);
  const [thinkingContent, setThinkingContent] = useState('');
  const [showThinking, setShowThinking] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [expandedThinkingIds, setExpandedThinkingIds] = useState<Set<number>>(new Set());

  // 会话管理状态
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

  // 消息编辑状态
  const [editingMessageIndex, setEditingMessageIndex] = useState<number | null>(null);
  const [isEditLoading, setIsEditLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const streamParserRef = useRef<StreamParser | null>(null);
  const thinkingContentRef = useRef<string>('');
  const conversationListRef = useRef<ConversationListRef>(null);

  // URL 路由工具函数
  const getConversationIdFromUrl = (): string | null => {
    const hash = window.location.hash;
    if (hash.startsWith('#conversation/')) {
      return hash.replace('#conversation/', '');
    }
    return null;
  };

  const updateUrlWithConversationId = (conversationId: string | null) => {
    if (conversationId) {
      window.history.replaceState(null, '', `#conversation/${conversationId}`);
    } else {
      window.history.replaceState(null, '', '#');
    }
  };

  // 获取问候语
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return '早上好';
    if (hour < 18) return '下午好';
    return '晚上好';
  };

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 会话管理函数
  const loadConversation = useCallback(async (conversationId: string) => {
    try {
      setIsLoading(true);
      const conversation = await conversationService.getConversation(conversationId);

      // 转换消息格式
      const convertedMessages: Message[] = conversation.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        thinking: msg.thinking,
        timestamp: new Date(msg.created_at),
        id: msg.id,
      }));

      setMessages(convertedMessages);
      setCurrentConversationId(conversationId);

      // 更新 URL
      updateUrlWithConversationId(conversationId);

      // 恢复thinking展开状态
      const expandedIds = new Set<number>();
      convertedMessages.forEach((msg, index) => {
        if (msg.thinking) {
          expandedIds.add(index);
        }
      });
      setExpandedThinkingIds(expandedIds);
    } catch (error) {
      console.error('Failed to load conversation:', error);
      alert('Failed to load conversation');
    } finally {
      setIsLoading(false);
    }
  }, []);

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

        // 2. 检查 URL 中是否有对话 ID，如果有则加载对应对话
        if (isAuthenticated && connected) {
          const urlConversationId = getConversationIdFromUrl();
          if (urlConversationId) {
            try {
              await loadConversation(urlConversationId);
            } catch (error) {
              console.error('Failed to load conversation from URL:', error);
              // 如果加载失败，清除 URL 中的对话 ID
              updateUrlWithConversationId(null);
            }
          }
        }
      } catch (error) {
        console.error('App initialization failed:', error);
      } finally {
        setIsInitializing(false);
      }
    };

    if (!isAuthLoading) {
      initApp();
    }
  }, [loadConversation, isAuthenticated, isAuthLoading]);

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

  // 处理浏览器前进/后退按钮
  useEffect(() => {
    const handlePopState = async () => {
      const urlConversationId = getConversationIdFromUrl();

      if (urlConversationId && urlConversationId !== currentConversationId) {
        // URL 中有对话 ID 且与当前对话不同，加载新对话
        try {
          await loadConversation(urlConversationId);
        } catch (error) {
          console.error('Failed to load conversation from URL:', error);
          // 如果加载失败，清除 URL 中的对话 ID
          updateUrlWithConversationId(null);
          setCurrentConversationId(null);
          setMessages([]);
        }
      } else if (!urlConversationId && currentConversationId) {
        // URL 中没有对话 ID 但当前有对话，回到欢迎页面
        setCurrentConversationId(null);
        setMessages([]);
        setExpandedThinkingIds(new Set());
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [currentConversationId, loadConversation]);

  const createNewConversation = async () => {
    try {
      const conversation = await conversationService.createConversation({});
      setCurrentConversationId(conversation.id);
      setMessages([]);
      setExpandedThinkingIds(new Set());

      // 更新 URL
      updateUrlWithConversationId(conversation.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
      alert('Failed to create conversation');
    }
  };

  // 发送消息
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !isConnected || !user) return;

    // 如果没有当前会话，创建一个新会话
    let conversationId = currentConversationId;
    if (!conversationId) {
      try {
        const conversation = await conversationService.createConversation({
          first_message: inputMessage.trim(),
        });
        conversationId = conversation.id;
        setCurrentConversationId(conversationId);

        // 更新 URL
        updateUrlWithConversationId(conversationId);
      } catch (error) {
        console.error('Failed to create conversation:', error);
        alert('Failed to create conversation');
        return;
      }
    }

    const userMessage: Message = {
      role: 'user',
      content: inputMessage.trim(),
    };

    const messageWithTimestamp = { ...userMessage, timestamp: new Date() };
    setMessages(prev => [...prev, messageWithTimestamp]);
    setInputMessage('');
    setIsLoading(true);

    // 立即添加一个空的assistant消息，准备接收流式内容
    const emptyAssistantMessage = {
      role: 'assistant' as const,
      content: '',
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, emptyAssistantMessage]);

    try {
      // 准备发送的消息列表（包含历史消息）

      if (useStream) {
        // 使用流式响应
        streamParserRef.current = new StreamParser();

        // 重置状态并立即显示thinking
        setThinkingContent('');
        thinkingContentRef.current = '';
        setShowThinking(true);
        setIsThinkingExpanded(true); // 默认展开

        try {
          await conversationService.sendMessageStream(
            conversationId,
            userMessage.content,
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
                }
                setThinkingContent(prev => {
                  // 如果是第一次添加内容，去除开头的空白
                  if (!prev && parsed.thinking) {
                    const trimmed = parsed.thinking.trimStart();
                    console.log(`🧠 UI: First thinking content (trimmed): ${trimmed.length} chars`);
                    thinkingContentRef.current = trimmed;
                    return trimmed;
                  }
                  const newContent = prev + parsed.thinking;
                  console.log(`🧠 UI: Updated thinking content length: ${newContent.length}`);
                  thinkingContentRef.current = newContent;
                  return newContent;
                });
              }

              // thinking完成时停止thinking状态并自动收起
              if (parsed.thinkingComplete) {
                console.log(`✅ UI: Thinking phase completed, switching to response mode`);
                // 自动收起thinking卡片
                setTimeout(() => {
                  setIsThinkingExpanded(false);
                }, 500); // 延迟500ms收起，让用户能看到完整的thinking内容

                // 将thinking内容保存到assistant消息中
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage.role === 'assistant') {
                    lastMessage.thinking = thinkingContentRef.current;
                  }
                  return newMessages;
                });
              }

              // 处理response内容
              if (parsed.response) {
                console.log(`💬 UI: Processing response content:`, JSON.stringify(parsed.response));
                // 更新现有的assistant消息
                console.log(`🔄 UI: Updating existing assistant message`);
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage.role === 'assistant') {
                    // 如果是第一次添加response内容，去除开头的空白
                    if (!lastMessage.content && parsed.response) {
                      const trimmed = parsed.response.trimStart();
                      console.log(`💬 UI: First response content (trimmed): ${trimmed.length} chars`);
                      lastMessage.content = trimmed;
                    } else {
                      const newContent = lastMessage.content + parsed.response;
                      console.log(`💬 UI: Updated response content length: ${newContent.length}`);
                      lastMessage.content = newContent;
                    }
                  }
                  return newMessages;
                });
              }
            },
          );

          console.log(`✅ Stream completed successfully`);
          const finalContent = streamParserRef.current?.getContent();
          console.log(`📊 Final stream statistics:`, {
            thinkingLength: finalContent?.thinking.length || 0,
            responseLength: finalContent?.response.length || 0,
          });
          setIsLoading(false);

          // 刷新会话列表以更新消息计数
          conversationListRef.current?.refresh();
        } catch (error) {
          console.error('❌ Stream error:', error);
          console.log(`📊 Error state statistics:`, {
            currentThinkingLength: thinkingContent.length,
            parseState: streamParserRef.current ? 'exists' : 'null',
          });
          setIsLoading(false);

          // 如果还没有添加助手消息，先添加一个错误消息
          if (messages[messages.length - 1]?.role !== 'assistant') {
            console.log(`➕ Adding error message (no assistant message yet)`);
            setMessages(prev => [
              ...prev,
              {
                role: 'assistant' as const,
                content: '抱歉，发生了错误。请稍后重试。',
                timestamp: new Date(),
              },
            ]);
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
      } else {
        // 使用普通响应
        const response = await conversationService.sendMessage(conversationId, userMessage.content);

        // 更新最后一条assistant消息
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage.role === 'assistant') {
            lastMessage.content = response.content;
            lastMessage.thinking = response.thinking;
          }
          return newMessages;
        });

        setIsLoading(false);

        // 刷新会话列表以更新消息计数
        conversationListRef.current?.refresh();
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant' as const,
        content: '抱歉，发生了错误。请检查网络连接或稍后重试。',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  // 处理消息编辑
  const handleEditMessage = async (messageIndex: number, newContent: string) => {
    const message = messages[messageIndex];
    if (!message.id || !currentConversationId) return;

    try {
      setIsEditLoading(true);
      const response = await messageBranchService.editMessage(
        currentConversationId,
        message.id,
        newContent,
        true, // 创建新分支
      );

      // 更新消息内容
      const newMessages = [...messages];
      newMessages[messageIndex] = {
        ...newMessages[messageIndex],
        content: response.message.content,
        id: response.message.id,
        version_number: response.message.version_number,
        branch_id: response.message.branch_id,
        branch_name: response.branch?.branch_name,
      };

      // 如果有新的助手回复，添加到消息列表
      if (response.new_assistant_message) {
        // 移除该消息之后的所有消息
        const messagesUpToEdit = newMessages.slice(0, messageIndex + 1);

        // 添加新的助手回复
        messagesUpToEdit.push({
          role: 'assistant',
          content: response.new_assistant_message.content,
          id: response.new_assistant_message.id,
          timestamp: new Date(),
        });

        setMessages(messagesUpToEdit);
      } else {
        setMessages(newMessages);
      }

      setEditingMessageIndex(null);

      // 刷新会话列表
      conversationListRef.current?.refresh();
    } catch (error) {
      console.error('Failed to edit message:', error);
      alert('编辑消息失败，请重试');
    } finally {
      setIsEditLoading(false);
    }
  };

  // 加载消息版本
  const loadMessageVersions = async (messageIndex: number) => {
    const message = messages[messageIndex];
    if (!message.id || !currentConversationId) return;

    try {
      const versions = await messageBranchService.getMessageVersions(currentConversationId, message.id);

      if (versions.length > 1) {
        // 更新消息的版本信息
        const newMessages = [...messages];
        newMessages[messageIndex] = {
          ...newMessages[messageIndex],
          versions: versions.map(v => ({
            id: v.id,
            content: v.content,
            version_number: v.version_number,
            branch_id: v.branch_id,
            branch_name: v.branch_name,
          })),
        };
        setMessages(newMessages);
      }
    } catch (error) {
      console.error('Failed to load message versions:', error);
    }
  };

  // 切换消息版本
  const switchMessageVersion = async (messageIndex: number, versionNumber: number) => {
    const message = messages[messageIndex];
    if (!message.versions) return;

    const targetVersion = message.versions.find(v => v.version_number === versionNumber);
    if (!targetVersion) return;

    // 切换到目标版本的分支
    if (targetVersion.branch_id && currentConversationId) {
      try {
        await messageBranchService.switchBranch(currentConversationId, targetVersion.branch_id);

        // 重新加载会话以获取该分支的消息
        await loadConversation(currentConversationId);
      } catch (error) {
        console.error('Failed to switch branch:', error);
      }
    }
  };

  // 格式化内容，处理段落和代码块
  const formatContent = (content: string): React.ReactNode => {
    // 如果内容为空或只有空白字符，返回null
    if (!content || !content.trim()) {
      return null;
    }

    // 首先去除开头和结尾的空白，包括换行符
    let trimmedContent = content.trim();

    // 特殊处理：如果内容以多个换行符开始，去除它们
    trimmedContent = trimmedContent.replace(/^[\n\r]+/, '').replace(/[\n\r]+$/, '');

    // 如果处理后内容为空，返回null
    if (!trimmedContent) {
      return null;
    }

    // 将文本分割为段落
    const paragraphs = trimmedContent.split(/\n{2,}/); // 两个或更多换行符分割段落

    // 调试：打印段落信息
    console.log(`Formatting content, trimmed: "${trimmedContent}", paragraphs count: ${paragraphs.length}`);

    const elements = paragraphs
      .map((paragraph, index) => {
        // 跳过空段落
        if (!paragraph.trim()) {
          return null;
        }

        // 检查是否是代码块
        if (paragraph.startsWith('```')) {
          const lines = paragraph.split('\n');
          const language = lines[0].slice(3).trim();
          const code = lines.slice(1, -1).join('\n');

          return (
            <pre key={index}>
              <code className={language ? `language-${language}` : ''}>{code}</code>
            </pre>
          );
        }

        // 处理普通段落
        // 移除单个换行符，保留段落结构
        const cleanedParagraph = paragraph.replace(/(?<!\n)\n(?!\n)/g, ' ').trim();

        if (cleanedParagraph) {
          return <p key={index}>{cleanedParagraph}</p>;
        }

        return null;
      })
      .filter(Boolean);

    // 如果没有有效内容，返回null
    if (elements.length === 0) {
      return null;
    }

    // 如果只有一个段落，不需要额外的margin
    if (elements.length === 1) {
      return <div className="single-paragraph">{elements}</div>;
    }

    return elements;
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

  // 清空聊天历史功能暂时注释
  // const clearChat = async () => {
  //   try {
  //     if (user && isConnected) {
  //       await apiService.clearChatHistory();
  //     }
  //     setMessages([]);
  //     // 清空thinking相关状态
  //     setThinkingContent('');
  //     thinkingContentRef.current = '';
  //     setShowThinking(false);
  //     setIsThinkingExpanded(true); // 重置为默认展开
  //     setExpandedThinkingIds(new Set());
  //     if (streamParserRef.current) {
  //       streamParserRef.current.reset();
  //     }
  //   } catch (error) {
  //     console.error('Failed to clear chat history:', error);
  //     // 即使清空失败，也清空本地消息
  //     setMessages([]);
  //     setThinkingContent('');
  //     thinkingContentRef.current = '';
  //     setShowThinking(false);
  //     setIsThinkingExpanded(true); // 重置为默认展开
  //     setExpandedThinkingIds(new Set());
  //     if (streamParserRef.current) {
  //       streamParserRef.current.reset();
  //     }
  //   }
  // };

  // 显示初始化加载状态
  if (isInitializing) {
    return (
      <div className={cn('flex min-h-screen items-center justify-center', isLight ? 'bg-white' : 'bg-gray-950')}>
        <div className="text-center">
          <div className="mb-6">
            <div
              className={cn(
                'mx-auto flex h-16 w-16 items-center justify-center rounded-full text-2xl',
                isLight ? 'bg-orange-100 text-orange-600' : 'bg-orange-500/20 text-orange-400',
              )}>
              🎓
            </div>
          </div>
          <LoadingSpinner size={100} />
          <p className={cn('mt-4 text-lg font-medium', isLight ? 'text-gray-900' : 'text-gray-100')}>
            正在初始化 Learn Mate...
          </p>
        </div>
      </div>
    );
  }

  // 如果正在加载认证状态，显示加载界面
  if (isAuthLoading || isInitializing) {
    return (
      <div className={cn('flex min-h-screen items-center justify-center', isLight ? 'bg-white' : 'bg-gray-950')}>
        <LoadingSpinner />
      </div>
    );
  }

  // 如果未登录，显示登录界面
  if (!isAuthenticated) {
    return (
      <Login
        onLoginSuccess={() => {
          // 登录成功后重新加载页面以刷新认证状态
          window.location.reload();
        }}
      />
    );
  }

  return (
    <div className={cn('min-h-screen', isLight ? 'bg-white' : 'bg-gray-950')}>
      {/* 左侧边栏 */}
      <div
        className={cn(
          'fixed left-0 top-0 flex h-full flex-col border-r transition-all duration-300',
          isLight ? 'border-gray-200 bg-white' : 'border-gray-800 bg-gray-900',
          isSidebarCollapsed ? 'w-16' : 'w-64',
        )}>
        {!isSidebarCollapsed ? (
          <>
            {/* 展开状态 - 顶部标题 */}
            <div className="flex items-center gap-2 p-4">
              <div
                className={cn(
                  'flex h-7 w-7 items-center justify-center rounded-md text-lg',
                  isLight ? 'bg-orange-100 text-orange-600' : 'bg-orange-500/20 text-orange-400',
                )}>
                🎓
              </div>
              <h1 className={cn('text-lg font-semibold', isLight ? 'text-gray-900' : 'text-white')}>Learn Mate</h1>
            </div>

            {/* New Chat 按钮 */}
            <div className="px-3 pb-4">
              <button
                onClick={createNewConversation}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
                  isLight
                    ? 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                    : 'border-gray-700 bg-gray-800 text-gray-200 hover:bg-gray-700',
                )}>
                <Plus size={16} />
                New chat
              </button>
            </div>

            {/* 导航菜单 */}
            <div className="flex-1 px-3">
              <div className="space-y-1">
                <button
                  className={cn(
                    'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isLight ? 'text-gray-700 hover:bg-gray-100' : 'text-gray-200 hover:bg-gray-800',
                  )}>
                  <MessageSquare size={16} />
                  Chats
                </button>
              </div>

              {/* 最近对话 */}
              <div className="mt-6">
                <div className={cn('px-3 py-2 text-xs font-medium', isLight ? 'text-gray-500' : 'text-gray-400')}>
                  Recents
                </div>
                <ConversationList
                  ref={conversationListRef}
                  currentConversationId={currentConversationId || undefined}
                  onSelectConversation={loadConversation}
                  onCreateConversation={createNewConversation}
                  isLight={isLight}
                  collapsed={false}
                />
              </div>
            </div>

            {/* 底部用户信息 */}
            {user && (
              <div className={cn('border-t p-3', isLight ? 'border-gray-200' : 'border-gray-800')}>
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium',
                      isLight ? 'bg-gray-100 text-gray-700' : 'bg-gray-800 text-gray-200',
                    )}>
                    {user.username.startsWith('temp_') ? 'G' : user.username.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className={cn('truncate text-sm font-medium', isLight ? 'text-gray-900' : 'text-white')}>
                      {user.email || 'Guest'}
                    </div>
                    <div className={cn('truncate text-xs', isLight ? 'text-gray-500' : 'text-gray-400')}>
                      {user.username.startsWith('temp_') ? '游客模式' : 'Personal'}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      authService.logout();
                      window.location.reload();
                    }}
                    className={cn(
                      'rounded-md p-1 text-xs transition-colors',
                      isLight ? 'text-gray-500 hover:bg-gray-100' : 'text-gray-400 hover:bg-gray-800',
                    )}>
                    登出
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            {/* 收起状态 - 仅显示图标 */}
            <div className="flex flex-col items-center gap-4 py-4">
              {/* Logo 图标 */}
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-lg text-lg',
                  isLight ? 'bg-orange-100 text-orange-600' : 'bg-orange-500/20 text-orange-400',
                )}>
                🎓
              </div>

              {/* New Chat 图标 */}
              <button
                onClick={createNewConversation}
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-lg transition-colors',
                  isLight ? 'text-gray-600 hover:bg-gray-100' : 'text-gray-400 hover:bg-gray-800',
                )}>
                <Plus size={16} />
              </button>

              {/* Chats 图标 */}
              <button
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-lg transition-colors',
                  isLight ? 'text-gray-600 hover:bg-gray-100' : 'text-gray-400 hover:bg-gray-800',
                )}>
                <MessageSquare size={16} />
              </button>
            </div>

            {/* 底部用户头像 */}
            {user && (
              <div className="mt-auto p-3">
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium',
                    isLight ? 'bg-gray-100 text-gray-700' : 'bg-gray-800 text-gray-200',
                  )}>
                  {user.username.startsWith('temp_') ? 'G' : user.username.charAt(0).toUpperCase()}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* 侧边栏切换按钮 */}
      <button
        onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        className={cn(
          'fixed top-4 z-50 flex h-10 w-10 items-center justify-center rounded-full border transition-all duration-300',
          isLight
            ? 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
            : 'border-gray-700 bg-gray-900 text-gray-400 hover:bg-gray-800',
          isSidebarCollapsed ? 'left-20' : 'left-4',
        )}>
        <svg
          className={cn('h-5 w-5 transition-transform duration-300', isSidebarCollapsed ? 'rotate-180' : '')}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* 主内容区域 */}
      <div
        className={cn(
          'flex min-h-screen flex-col transition-all duration-300',
          isSidebarCollapsed ? 'ml-16' : 'ml-64',
        )}>
        {messages.length === 0 ? (
          /* 欢迎界面 */
          <div className="flex flex-1 flex-col items-center justify-center px-8">
            <div className="w-full max-w-2xl text-center">
              {/* 问候语 */}
              <div className="mb-12">
                <div
                  className={cn(
                    'flex items-center justify-center space-x-2 text-2xl',
                    isLight ? 'text-gray-900' : 'text-gray-100',
                  )}>
                  <span>🌟</span>
                  <span className="font-medium">{getGreeting()}, 学习者</span>
                  <span className={cn('ml-3 text-lg', isLight ? 'text-gray-600' : 'text-gray-400')}>
                    今天想学点什么？
                  </span>
                </div>
              </div>

              {/* 输入框 */}
              <div className="relative">
                <textarea
                  ref={inputRef}
                  value={inputMessage}
                  onChange={handleInputChange}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    !isConnected
                      ? '请先启动后端服务...'
                      : !user
                        ? '正在初始化用户...'
                        : isLoading
                          ? '正在思考中...'
                          : '向 Learn Mate 提问...'
                  }
                  disabled={!isConnected || !user || isLoading}
                  className={cn(
                    'w-full resize-none rounded-2xl border-2 p-4 pr-16 text-lg transition-all duration-200 focus:outline-none',
                    'placeholder:text-gray-400',
                    isLight
                      ? 'border-gray-200 bg-white text-gray-900 shadow-sm focus:border-orange-400 focus:shadow-md'
                      : 'border-gray-700 bg-gray-900 text-white focus:border-orange-500',
                    (!isConnected || isLoading) && 'cursor-not-allowed opacity-50',
                  )}
                  rows={1}
                  style={{ minHeight: '60px', maxHeight: '160px' }}
                />

                {/* 发送按钮 */}
                <button
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || !isConnected || !user || isLoading}
                  className={cn(
                    'absolute right-3 top-1/2 -translate-y-1/2 transform',
                    'flex h-10 w-10 items-center justify-center rounded-full transition-all duration-200',
                    inputMessage.trim() && isConnected && user && !isLoading
                      ? 'bg-orange-500 text-white shadow-md hover:bg-orange-600 hover:shadow-lg'
                      : isLight
                        ? 'bg-gray-200 text-gray-400'
                        : 'bg-gray-700 text-gray-500',
                    'disabled:cursor-not-allowed',
                  )}>
                  {isLoading ? (
                    <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                    </svg>
                  )}
                </button>
              </div>

              {/* 快捷操作提示 */}
              <div
                className={cn(
                  'mt-6 flex items-center justify-center space-x-6 text-sm',
                  isLight ? 'text-gray-500' : 'text-gray-400',
                )}>
                <div className="flex items-center space-x-1">
                  <kbd
                    className={cn(
                      'rounded px-2 py-1 text-xs',
                      isLight ? 'bg-gray-100 text-gray-600' : 'bg-gray-800 text-gray-300',
                    )}>
                    Enter
                  </kbd>
                  <span>发送</span>
                </div>
                <div className="flex items-center space-x-1">
                  <kbd
                    className={cn(
                      'rounded px-2 py-1 text-xs',
                      isLight ? 'bg-gray-100 text-gray-600' : 'bg-gray-800 text-gray-300',
                    )}>
                    Shift + Enter
                  </kbd>
                  <span>换行</span>
                </div>
              </div>

              {!isConnected && (
                <div
                  className={cn(
                    'mt-6 rounded-lg p-4',
                    isLight ? 'bg-red-50 text-red-700' : 'bg-red-500/10 text-red-400',
                  )}>
                  <p className="text-sm">无法连接到后端服务，请确保后端服务已启动 (http://localhost:8000)</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* 聊天界面 */
          <div className="flex flex-1 flex-col">
            {/* 消息列表 */}
            <div className="flex-1 overflow-y-auto">
              <div className="mx-auto max-w-4xl px-8 py-8">
                {messages.map((message, index) => {
                  const isLastMessage = index === messages.length - 1;
                  const messageThinking = isLastMessage && thinkingContent ? thinkingContent : message.thinking;
                  const isExpanded = isLastMessage ? isThinkingExpanded : expandedThinkingIds.has(index);

                  return (
                    <div key={index} className={cn('mb-4', isLastMessage && 'mb-0')}>
                      {message.role === 'user' ? (
                        /* 用户消息 - 头像在卡片内部 */
                        <div className="group relative flex justify-start">
                          <div
                            className={cn(
                              'flex items-start gap-3 rounded-2xl px-4 py-3',
                              isLight ? 'bg-gray-100 text-gray-900' : 'bg-gray-800 text-gray-100',
                            )}>
                            <div
                              className={cn(
                                'mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                                isLight ? 'bg-gray-300 text-gray-700' : 'bg-gray-600 text-gray-200',
                              )}>
                              Z
                            </div>
                            <div className="flex-1">
                              {editingMessageIndex === index ? (
                                <MessageEditor
                                  content={message.content}
                                  onSave={newContent => handleEditMessage(index, newContent)}
                                  onCancel={() => setEditingMessageIndex(null)}
                                  isLight={isLight}
                                  isLoading={isEditLoading}
                                />
                              ) : (
                                <div className="whitespace-pre-wrap break-words text-base leading-relaxed">
                                  {message.content}
                                </div>
                              )}
                            </div>

                            {/* 编辑按钮和版本选择器 */}
                            {editingMessageIndex !== index && (
                              <div className="ml-2 flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
                                <button
                                  onClick={() => {
                                    setEditingMessageIndex(index);
                                    // 加载版本信息
                                    loadMessageVersions(index);
                                  }}
                                  className={cn(
                                    'flex h-7 w-7 items-center justify-center rounded-md transition-colors',
                                    isLight ? 'text-gray-600 hover:bg-gray-200' : 'text-gray-400 hover:bg-gray-700',
                                  )}
                                  title="编辑消息">
                                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                    />
                                  </svg>
                                </button>

                                {/* 版本选择器 */}
                                {message.versions && message.versions.length > 1 && (
                                  <VersionSelector
                                    currentVersion={message.version_number || 1}
                                    totalVersions={message.versions.length}
                                    onVersionChange={version => switchMessageVersion(index, version)}
                                    isLight={isLight}
                                    branchName={message.branch_name}
                                  />
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      ) : (
                        /* Assistant消息 - 无头像，简化设计 */
                        <div>
                          {/* Thinking 卡片 - 在response上方 */}
                          {messageThinking && (
                            <div
                              className={cn(
                                'mb-4 overflow-hidden rounded-lg border transition-all duration-200',
                                isLight ? 'border-gray-200 bg-gray-50' : 'border-gray-700 bg-gray-800',
                              )}>
                              <div
                                className={cn(
                                  'transition-all duration-300 ease-in-out',
                                  isExpanded ? 'max-h-[500px]' : 'max-h-[60px]',
                                )}>
                                {isExpanded ? (
                                  <>
                                    {/* Header - 只在展开时显示，整个header可点击 */}
                                    <button
                                      onClick={() => {
                                        if (isLastMessage) {
                                          setIsThinkingExpanded(!isThinkingExpanded);
                                        } else {
                                          setExpandedThinkingIds(prev => {
                                            const newSet = new Set(prev);
                                            if (newSet.has(index)) {
                                              newSet.delete(index);
                                            } else {
                                              newSet.add(index);
                                            }
                                            return newSet;
                                          });
                                        }
                                      }}
                                      className={cn(
                                        'animate-fadeIn flex w-full items-center justify-between px-4 py-2',
                                        'transition-colors hover:bg-gray-100 dark:hover:bg-gray-700/50',
                                      )}>
                                      <h3
                                        className={cn(
                                          'text-base font-medium',
                                          isLight ? 'text-gray-900' : 'text-gray-100',
                                        )}>
                                        Thought process
                                      </h3>
                                      <div className="flex items-center gap-2">
                                        <span className={cn('text-sm', isLight ? 'text-gray-500' : 'text-gray-400')}>
                                          1s
                                        </span>
                                        <svg
                                          className={cn(
                                            'h-5 w-5 transition-transform duration-300',
                                            isExpanded && 'rotate-180',
                                          )}
                                          fill="none"
                                          stroke="currentColor"
                                          viewBox="0 0 24 24">
                                          <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M19 9l-7 7-7-7"
                                          />
                                        </svg>
                                      </div>
                                    </button>

                                    {/* Content */}
                                    <div
                                      className={cn(
                                        'animate-fadeIn thinking-content px-4 pb-6 text-sm leading-relaxed',
                                        isLight ? 'text-gray-700' : 'dark text-gray-300',
                                      )}>
                                      {formatContent(messageThinking)}
                                    </div>
                                  </>
                                ) : (
                                  /* Collapsed content - 无header，可点击整个区域展开 */
                                  <button
                                    onClick={() => {
                                      if (isLastMessage) {
                                        setIsThinkingExpanded(true);
                                      } else {
                                        setExpandedThinkingIds(prev => {
                                          const newSet = new Set(prev);
                                          newSet.add(index);
                                          return newSet;
                                        });
                                      }
                                    }}
                                    className={cn(
                                      'group flex w-full items-center justify-between px-4 py-3 text-left',
                                      'transition-all duration-200 hover:bg-gray-100 dark:hover:bg-gray-700/50',
                                    )}>
                                    <span
                                      className={cn(
                                        'flex-1 text-sm leading-relaxed',
                                        isLight ? 'text-gray-700' : 'text-gray-300',
                                      )}>
                                      {(() => {
                                        // 获取第一句话（到句号、感叹号或问号为止）
                                        const firstSentence =
                                          messageThinking.match(/^[^.!?。！？]+[.!?。！？]/)?.[0] ||
                                          messageThinking.split('\n')[0] ||
                                          messageThinking;
                                        // 限制最大长度为100个字符
                                        const truncated =
                                          firstSentence.length > 100 ? firstSentence.substring(0, 100) : firstSentence;
                                        return truncated.length < messageThinking.length
                                          ? truncated + '...'
                                          : truncated;
                                      })()}
                                    </span>
                                    <span
                                      className={cn(
                                        'ml-2 shrink-0 text-sm transition-opacity duration-200',
                                        isLight ? 'text-gray-500' : 'text-gray-400',
                                      )}>
                                      1s
                                    </span>
                                  </button>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Response内容 */}
                          <div className="max-w-4xl">
                            <div
                              className={cn(
                                'response-content text-base leading-relaxed',
                                isLight ? 'text-gray-900' : 'dark text-gray-100',
                              )}>
                              {message.content
                                ? formatContent(message.content)
                                : isLoading &&
                                  isLastMessage && <span className="inline-block h-4 w-2 animate-pulse bg-current" />}
                            </div>

                            {/* 底部操作栏 */}
                            {isLastMessage && (isLoading || message.content) && (
                              <div className="mt-3 flex items-center gap-1">
                                {/* Loading spinner */}
                                {isLoading && (
                                  <div
                                    className={cn(
                                      'flex h-6 w-6 items-center justify-center',
                                      isLight ? 'text-orange-500' : 'text-orange-400',
                                    )}>
                                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                                      <circle
                                        className="opacity-25"
                                        cx="12"
                                        cy="12"
                                        r="10"
                                        stroke="currentColor"
                                        strokeWidth="4"
                                        fill="none"
                                      />
                                      <path
                                        className="opacity-75"
                                        fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                      />
                                    </svg>
                                  </div>
                                )}

                                {/* Copy button */}
                                <button
                                  onClick={() => {
                                    navigator.clipboard.writeText(message.content);
                                    setCopiedMessageId(String(index));
                                    setTimeout(() => setCopiedMessageId(null), 2000);
                                  }}
                                  className={cn(
                                    'relative rounded p-1.5 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800',
                                    isLight ? 'text-gray-500 hover:text-gray-700' : 'text-gray-400 hover:text-gray-200',
                                  )}
                                  title="复制">
                                  {copiedMessageId === String(index) ? (
                                    <>
                                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path
                                          strokeLinecap="round"
                                          strokeLinejoin="round"
                                          strokeWidth={2}
                                          d="M5 13l4 4L19 7"
                                        />
                                      </svg>
                                      <span
                                        className={cn(
                                          'absolute left-full ml-2 whitespace-nowrap rounded px-2 py-1 text-xs',
                                          isLight ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-900',
                                        )}>
                                        已复制
                                      </span>
                                    </>
                                  ) : (
                                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                                      />
                                    </svg>
                                  )}
                                </button>

                                {/* Retry button */}
                                <button
                                  onClick={() => {
                                    // 找到最后一条用户消息
                                    const lastUserMessageIndex = messages.findLastIndex(m => m.role === 'user');
                                    if (lastUserMessageIndex >= 0) {
                                      // 保留到最后一条用户消息为止的所有消息
                                      setMessages(messages.slice(0, lastUserMessageIndex));
                                      // 清空thinking内容
                                      setThinkingContent('');
                                      thinkingContentRef.current = '';
                                      setShowThinking(false);
                                      // 直接使用最后的用户消息内容发送，不需要设置inputMessage
                                      const lastUserMessageContent = messages[lastUserMessageIndex].content;

                                      // 创建新的用户消息
                                      const userMessage = {
                                        role: 'user' as const,
                                        content: lastUserMessageContent,
                                      };

                                      const messageWithTimestamp = { ...userMessage, timestamp: new Date() };
                                      setMessages(prev => [...prev, messageWithTimestamp]);
                                      setIsLoading(true);

                                      // 立即添加空的assistant消息
                                      const emptyAssistantMessage = {
                                        role: 'assistant' as const,
                                        content: '',
                                        timestamp: new Date(),
                                      };
                                      setMessages(prev => [...prev, emptyAssistantMessage]);

                                      // 发送请求
                                      const allMessages = [...messages.slice(0, lastUserMessageIndex), userMessage];

                                      // 重置状态并显示thinking
                                      streamParserRef.current = new StreamParser();
                                      setThinkingContent('');
                                      setShowThinking(true);
                                      setIsThinkingExpanded(true);

                                      // 发送流式请求
                                      apiService.sendMessageStream(
                                        allMessages,
                                        (chunk: string) => {
                                          const parsed = streamParserRef.current!.processChunk(chunk);

                                          if (parsed.thinking) {
                                            setThinkingContent(prev => {
                                              // 如果是第一次添加内容，去除开头的空白
                                              if (!prev && parsed.thinking) {
                                                return parsed.thinking.trimStart();
                                              }
                                              return prev + parsed.thinking;
                                            });
                                          }

                                          if (parsed.thinkingComplete) {
                                            setTimeout(() => {
                                              setIsThinkingExpanded(false);
                                            }, 500);
                                          }

                                          if (parsed.response) {
                                            setMessages(prev => {
                                              const newMessages = [...prev];
                                              const lastMessage = newMessages[newMessages.length - 1];
                                              if (lastMessage.role === 'assistant') {
                                                // 如果是第一次添加response内容，去除开头的空白
                                                if (!lastMessage.content && parsed.response) {
                                                  lastMessage.content = parsed.response.trimStart();
                                                } else {
                                                  lastMessage.content = lastMessage.content + parsed.response;
                                                }
                                              }
                                              return newMessages;
                                            });
                                          }
                                        },
                                        () => {
                                          setIsLoading(false);
                                        },
                                        (error: Error) => {
                                          console.error('Stream error:', error);
                                          setIsLoading(false);
                                        },
                                      );
                                    }
                                  }}
                                  className={cn(
                                    'flex items-center gap-1 rounded p-1.5 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800',
                                    isLight ? 'text-gray-500 hover:text-gray-700' : 'text-gray-400 hover:text-gray-200',
                                  )}
                                  title="重试">
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                    />
                                  </svg>
                                  <span className="text-xs">Retry</span>
                                </button>

                                {/* Disclaimer text */}
                                <span className={cn('ml-auto text-xs', isLight ? 'text-gray-400' : 'text-gray-500')}>
                                  AI can make mistakes. Please double-check responses.
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

            {/* 底部输入区域 - 固定在底部 */}
            <div className="flex-shrink-0 border-t border-inherit bg-inherit">
              <div className="mx-auto max-w-4xl px-8 py-6">
                <div className="relative">
                  <textarea
                    ref={inputRef}
                    value={inputMessage}
                    onChange={handleInputChange}
                    onKeyPress={handleKeyPress}
                    placeholder={
                      !isConnected
                        ? '请先启动后端服务...'
                        : !user
                          ? '正在初始化用户...'
                          : isLoading
                            ? '正在思考中...'
                            : '继续对话...'
                    }
                    disabled={!isConnected || !user || isLoading}
                    className={cn(
                      'w-full resize-none rounded-2xl border-2 p-4 pr-16 transition-all duration-200 focus:outline-none',
                      'placeholder:text-gray-400',
                      isLight
                        ? 'border-gray-200 bg-white text-gray-900 shadow-sm focus:border-orange-400 focus:shadow-md'
                        : 'border-gray-700 bg-gray-900 text-white focus:border-orange-500',
                      (!isConnected || isLoading) && 'cursor-not-allowed opacity-50',
                    )}
                    rows={1}
                    style={{ minHeight: '56px', maxHeight: '120px' }}
                  />

                  {/* 发送按钮 */}
                  <button
                    onClick={sendMessage}
                    disabled={!inputMessage.trim() || !isConnected || !user || isLoading}
                    className={cn(
                      'absolute right-3 top-1/2 -translate-y-1/2 transform',
                      'flex h-8 w-8 items-center justify-center rounded-full transition-all duration-200',
                      inputMessage.trim() && isConnected && user && !isLoading
                        ? 'bg-orange-500 text-white hover:bg-orange-600'
                        : isLight
                          ? 'bg-gray-200 text-gray-400'
                          : 'bg-gray-700 text-gray-500',
                      'disabled:cursor-not-allowed',
                    )}>
                    {isLoading ? (
                      <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                          fill="none"
                        />
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
