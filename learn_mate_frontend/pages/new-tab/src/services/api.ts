// API服务层，处理与后端的通信

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ChatRequest {
  messages: Message[];
}

interface ChatResponse {
  messages: Message[];
}

interface StreamResponse {
  content: string;
  done: boolean;
}

class ApiService {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  // 设置认证token
  setToken(token: string) {
    this.token = token;
  }

  // 获取 baseUrl
  getBaseUrl(): string {
    return this.baseUrl;
  }

  // 获取认证 token
  getAuthToken(): string | null {
    return this.token;
  }

  // 获取请求头
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    return headers;
  }

  // 检查后端健康状态
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
      });
      return response.ok;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  // 用户注册
  async register(username: string, email: string, password: string): Promise<{ access_token: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/register`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        email,
        password,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    const data = await response.json();
    return { access_token: data.token.access_token };
  }

  // 用户登录（旧版本，用于临时用户）
  async login(username: string, password: string): Promise<{ access_token: string }> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('grant_type', 'password');

    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    return response.json();
  }

  // 账号登录（新版本）
  async accountLogin(
    email: string,
    password: string,
    rememberMe: boolean = false,
  ): Promise<{
    access_token: string;
    refresh_token?: string;
    token_type: string;
    expires_in: number;
    user: {
      id: number;
      email: string;
      username: string;
      created_at: string;
    };
  }> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        email,
        password,
        remember_me: rememberMe,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '登录失败');
    }

    return response.json();
  }

  // 账号注册（新版本）
  async accountRegister(
    email: string,
    username: string,
    password: string,
  ): Promise<{
    id: number;
    email: string;
    username: string;
    created_at: string;
  }> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/register`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        email,
        username,
        password,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '注册失败');
    }

    return response.json();
  }

  // 获取当前用户信息
  async getCurrentUser(): Promise<{
    id: number;
    email: string;
    username: string;
    created_at: string;
  }> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/me`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '获取用户信息失败');
    }

    return response.json();
  }

  // 登出
  async logout(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/logout`, {
      method: 'POST',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '登出失败');
    }
  }

  // 发送聊天消息
  async sendMessage(messages: Message[]): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/chatbot/chat`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ messages }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Chat request failed');
    }

    return response.json();
  }

  // 发送流式聊天消息
  async sendMessageStream(
    messages: Message[],
    onChunk: (chunk: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void,
  ): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/chatbot/chat/stream`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ messages }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Stream chat request failed');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Failed to get response reader');
      }

      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          onComplete();
          break;
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              const streamResponse: StreamResponse = data;

              if (streamResponse.content) {
                // 直接传递原始内容，不做任何类型区分
                onChunk(streamResponse.content);
              }

              if (streamResponse.done) {
                onComplete();
                return;
              }
            } catch (parseError) {
              console.warn('Failed to parse SSE data:', parseError);
            }
          }
        }
      }
    } catch (error) {
      onError(error instanceof Error ? error : new Error('Unknown error'));
    }
  }

  // 获取聊天历史
  async getChatHistory(): Promise<Message[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/chatbot/messages`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get chat history');
    }

    const data: ChatResponse = await response.json();
    return data.messages;
  }

  // 创建新的聊天会话
  async createSession(): Promise<{ session_id: string; token: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/session`, {
      method: 'POST',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create session');
    }

    const data = await response.json();
    return {
      session_id: data.session_id,
      token: data.token.access_token,
    };
  }

  // 清空聊天历史
  async clearChatHistory(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/chatbot/messages`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to clear chat history');
    }
  }
}

// 创建默认的API服务实例
export const apiService = new ApiService();
export type { Message, ChatRequest, ChatResponse, StreamResponse };
