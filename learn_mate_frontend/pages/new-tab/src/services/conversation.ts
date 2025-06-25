import { getAuthHeaders } from './auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface Conversation {
  id: string;
  title: string;
  summary?: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking?: string;
  created_at: string;
}

interface ConversationDetail extends Conversation {
  messages: ConversationMessage[];
}

interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
  page: number;
  limit: number;
}

interface ConversationCreateRequest {
  title?: string;
  first_message?: string;
}

interface ConversationUpdateRequest {
  title: string;
}

class ConversationService {
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = await getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...headers,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async getConversations(page: number = 1, limit: number = 20, search?: string): Promise<ConversationListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });

    if (search) {
      params.append('search', search);
    }

    return this.request<ConversationListResponse>(`/api/v1/conversations?${params.toString()}`);
  }

  async getConversation(id: string): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/api/v1/conversations/${id}`);
  }

  async createConversation(data: ConversationCreateRequest): Promise<Conversation> {
    try {
      return await this.request<Conversation>('/api/v1/conversations', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch (error) {
      // 如果是 session not found 错误，尝试重新创建 session
      if (error instanceof Error && error.message.includes('Session not found')) {
        // 重新创建临时会话
        const { authService } = await import('./auth');
        await authService.createTemporarySession();

        // 重试创建对话
        return this.request<Conversation>('/api/v1/conversations', {
          method: 'POST',
          body: JSON.stringify(data),
        });
      }
      throw error;
    }
  }

  async updateConversation(id: string, data: ConversationUpdateRequest): Promise<Conversation> {
    return this.request<Conversation>(`/api/v1/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteConversation(id: string): Promise<void> {
    await this.request(`/api/v1/conversations/${id}`, {
      method: 'DELETE',
    });
  }

  async sendMessage(conversationId: string, content: string): Promise<ConversationMessage> {
    const response = await this.request<{ role: string; content: string }>(
      `/api/v1/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({
          messages: [{ role: 'user', content }],
        }),
      },
    );

    return {
      id: Date.now().toString(),
      role: response.role as 'assistant',
      content: response.content,
      created_at: new Date().toISOString(),
    };
  }

  async sendMessageStream(
    conversationId: string,
    content: string,
    onChunk: (chunk: string) => void,
    onThinking?: (thinking: string) => void,
  ): Promise<void> {
    const headers = await getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}/messages/stream`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: [{ role: 'user', content }],
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No reader available');

    const decoder = new TextDecoder();
    let buffer = '';
    let thinkingContent = '';
    let inThinking = false;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.done) {
                return;
              }

              if (data.content) {
                // Check for thinking tags
                if (data.content.includes('<think>')) {
                  inThinking = true;
                }
                if (data.content.includes('</think>')) {
                  inThinking = false;
                  // Extract thinking content
                  const match = thinkingContent.match(/<think>(.*?)<\/think>/s);
                  if (match && onThinking) {
                    onThinking(match[1]);
                  }
                  thinkingContent = '';
                }

                if (inThinking) {
                  thinkingContent += data.content;
                }

                onChunk(data.content);
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}

export type {
  Conversation,
  ConversationMessage,
  ConversationDetail,
  ConversationListResponse,
  ConversationCreateRequest,
  ConversationUpdateRequest,
};
export const conversationService = new ConversationService();
