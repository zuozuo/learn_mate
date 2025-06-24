# 聊天历史功能设计文档

## 1. 功能概述

### 1.1 核心功能
- 支持多会话管理：用户可以创建、切换、删除多个独立的对话
- 历史记录持久化：所有对话和消息保存在PostgreSQL数据库中
- thinking内容保存：完整保存AI的思考过程内容
- 会话列表展示：左侧边栏显示所有历史对话
- 实时同步：新消息实时更新到当前会话

### 1.2 用户场景
1. 用户可以创建新的对话会话
2. 用户可以查看所有历史对话列表
3. 用户可以切换到任意历史对话继续聊天
4. 用户可以删除不需要的对话
5. 用户可以搜索历史对话（未来功能）

## 2. 数据库设计

### 2.1 conversations 表
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 索引
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at DESC);
CREATE INDEX idx_conversations_is_deleted ON conversations(is_deleted);
```

### 2.2 chat_messages 表
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    thinking TEXT, -- AI的思考过程内容
    message_index INTEGER NOT NULL, -- 消息在会话中的顺序
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 索引
CREATE INDEX idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX idx_chat_messages_conv_idx ON chat_messages(conversation_id, message_index);

-- 唯一约束：确保同一会话中消息顺序唯一
ALTER TABLE chat_messages ADD CONSTRAINT unique_conversation_message_index 
    UNIQUE (conversation_id, message_index);
```

### 2.3 数据库触发器
```sql
-- 自动更新conversations的updated_at
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_conversation_on_new_message
AFTER INSERT ON chat_messages
FOR EACH ROW
EXECUTE FUNCTION update_conversation_timestamp();
```

## 3. 后端API设计

### 3.1 会话管理API

#### 创建新会话
```
POST /api/v1/conversations
Request:
{
    "title": "New Conversation" // 可选，默认根据第一条消息生成
}
Response:
{
    "id": "uuid",
    "title": "New Conversation",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 获取会话列表
```
GET /api/v1/conversations?page=1&limit=20&search=keyword
Response:
{
    "conversations": [
        {
            "id": "uuid",
            "title": "Discussion about AI",
            "summary": "First 100 chars of first message...",
            "message_count": 10,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ],
    "total": 50,
    "page": 1,
    "limit": 20
}
```

#### 获取单个会话详情
```
GET /api/v1/conversations/{conversation_id}
Response:
{
    "id": "uuid",
    "title": "Discussion about AI",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "messages": [
        {
            "id": "uuid",
            "role": "user",
            "content": "Hello",
            "created_at": "2024-01-01T00:00:00Z"
        },
        {
            "id": "uuid",
            "role": "assistant",
            "content": "Hi! How can I help you?",
            "thinking": "<think>User greeted me...</think>",
            "created_at": "2024-01-01T00:00:01Z"
        }
    ]
}
```

#### 更新会话标题
```
PATCH /api/v1/conversations/{conversation_id}
Request:
{
    "title": "Updated Title"
}
```

#### 删除会话（软删除）
```
DELETE /api/v1/conversations/{conversation_id}
```

### 3.2 消息管理API

#### 发送消息（修改现有接口）
```
POST /api/v1/conversations/{conversation_id}/messages
Request:
{
    "content": "User message"
}
Response:
{
    "id": "uuid",
    "role": "user",
    "content": "User message",
    "created_at": "2024-01-01T00:00:00Z"
}
```

#### 流式响应（修改现有接口）
```
POST /api/v1/conversations/{conversation_id}/messages/stream
Request:
{
    "content": "User message"
}
Response: Server-Sent Events
data: {"content": "chunk1", "thinking": "thinking chunk"}
data: {"content": "chunk2"}
data: {"done": true, "message_id": "uuid"}
```

### 3.3 兼容性处理
为了保持向后兼容，保留现有的聊天API：
- `POST /api/v1/chatbot/chat` - 创建临时会话并返回响应
- `POST /api/v1/chatbot/chat/stream` - 创建临时会话的流式响应

## 4. 前端设计

### 4.1 UI布局更新
```
+------------------+---------------------------+
|   Conversations  |      Chat Area           |
|                  |                          |
| [New Chat]       | +----------------------+ |
|                  | |   Thinking Card      | |
| ▼ Today          | +----------------------+ |
|   • Chat 1       |                          |
|   • Chat 2       | User: Hello              |
|                  |                          |
| ▼ Yesterday      | Assistant: Hi!           |
|   • Chat 3       |                          |
|                  | +----------------------+ |
| ▼ Last 7 days    | | Input Box            | |
|   • Chat 4       | +----------------------+ |
+------------------+---------------------------+
```

### 4.2 状态管理
```typescript
interface AppState {
    // 会话列表
    conversations: Conversation[];
    currentConversationId: string | null;
    
    // 当前会话消息
    messages: Message[];
    
    // UI状态
    isLoadingConversations: boolean;
    isLoadingMessages: boolean;
    isSending: boolean;
    
    // 实时状态
    thinkingContent: string;
    streamingMessageId: string | null;
}
```

### 4.3 关键组件
1. **ConversationList**: 左侧会话列表
   - 显示所有会话
   - 支持创建新会话
   - 支持切换会话
   - 支持删除会话

2. **ChatArea**: 右侧聊天区域
   - 显示当前会话的所有消息
   - 保持现有的thinking卡片功能
   - 支持继续对话

3. **MessageList**: 消息列表组件
   - 复用现有的消息渲染逻辑
   - 支持thinking内容展示

## 5. 数据流设计

### 5.1 创建新会话流程
1. 用户点击"New Chat"或发送第一条消息
2. 前端调用创建会话API
3. 后端创建conversation记录
4. 前端更新会话列表并切换到新会话

### 5.2 加载历史会话流程
1. 用户点击会话列表中的某个会话
2. 前端调用获取会话详情API
3. 后端返回该会话的所有消息
4. 前端渲染消息列表，包括thinking内容

### 5.3 发送消息流程
1. 用户在当前会话中发送消息
2. 前端调用发送消息API（带conversation_id）
3. 后端保存用户消息并生成AI响应
4. 流式返回AI响应，包括thinking内容
5. 响应完成后，后端保存完整的assistant消息

## 6. 实现步骤

### 6.1 后端实现顺序
1. 创建数据库表和迁移脚本
2. 实现Conversation模型和repository
3. 实现ChatMessage模型和repository
4. 实现会话管理API endpoints
5. 修改现有聊天API支持conversation
6. 实现消息的thinking字段保存

### 6.2 前端实现顺序
1. 添加会话列表UI组件
2. 实现会话状态管理
3. 修改现有聊天逻辑支持conversation_id
4. 实现会话切换功能
5. 实现创建/删除会话功能
6. 更新消息渲染支持持久化的thinking

## 7. 技术要点

### 7.1 性能优化
- 会话列表分页加载
- 消息列表虚拟滚动（大量消息时）
- 会话列表缓存策略
- 数据库查询优化

### 7.2 实时同步
- 使用WebSocket实现多设备同步（未来功能）
- 乐观更新提升用户体验
- 断线重连机制

### 7.3 数据安全
- 会话隔离：确保用户只能访问自己的会话
- 软删除：保留数据可恢复性
- 定期清理已删除数据

## 8. 未来扩展
1. 会话搜索功能
2. 会话分类/标签
3. 会话导出功能
4. 会话分享功能
5. 多设备同步