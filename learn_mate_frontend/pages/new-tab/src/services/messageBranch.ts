import { apiService } from './api';

interface MessageVersion {
  id: string;
  content: string;
  version_number: number;
  branch_id: string;
  branch_name?: string;
  created_at: string;
  is_current_version: boolean;
}

interface MessageBranch {
  id: string;
  conversation_id: string;
  parent_message_id?: string;
  sequence_number: number;
  branch_name?: string;
  created_at: string;
  updated_at: string;
}

interface EditMessageResponse {
  message: MessageVersion;
  branch?: MessageBranch;
  new_assistant_message?: MessageVersion;
}

interface BranchTreeNode {
  id: string;
  name?: string;
  parent_message_id?: string;
  message_count: number;
  children: BranchTreeNode[];
}

class MessageBranchService {
  async editMessage(
    conversationId: string,
    messageId: string,
    content: string,
    createBranch: boolean = true,
  ): Promise<EditMessageResponse> {
    const response = await fetch(
      `${apiService.getBaseUrl()}/api/v1/conversations/${conversationId}/messages/${messageId}/edit`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiService.getAuthToken()}`,
        },
        body: JSON.stringify({
          content,
          create_branch: createBranch,
        }),
      },
    );

    if (!response.ok) {
      throw new Error('Failed to edit message');
    }

    return response.json();
  }

  async getMessageVersions(conversationId: string, messageId: string): Promise<MessageVersion[]> {
    const response = await fetch(
      `${apiService.getBaseUrl()}/api/v1/conversations/${conversationId}/messages/${messageId}/versions`,
      {
        headers: {
          Authorization: `Bearer ${apiService.getAuthToken()}`,
        },
      },
    );

    if (!response.ok) {
      throw new Error('Failed to get message versions');
    }

    return response.json();
  }

  async getConversationBranches(conversationId: string): Promise<MessageBranch[]> {
    const response = await fetch(`${apiService.getBaseUrl()}/api/v1/conversations/${conversationId}/branches`, {
      headers: {
        Authorization: `Bearer ${apiService.getAuthToken()}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get conversation branches');
    }

    return response.json();
  }

  async switchBranch(conversationId: string, branchId: string): Promise<{ status: string; branch_id: string }> {
    const response = await fetch(
      `${apiService.getBaseUrl()}/api/v1/conversations/${conversationId}/branches/${branchId}/switch`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiService.getAuthToken()}`,
        },
      },
    );

    if (!response.ok) {
      throw new Error('Failed to switch branch');
    }

    return response.json();
  }

  async getBranchTree(conversationId: string): Promise<BranchTreeNode[]> {
    const response = await fetch(`${apiService.getBaseUrl()}/api/v1/conversations/${conversationId}/branch-tree`, {
      headers: {
        Authorization: `Bearer ${apiService.getAuthToken()}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get branch tree');
    }

    return response.json();
  }
}

export const messageBranchService = new MessageBranchService();
