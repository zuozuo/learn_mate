# Latest User Requirements

## 当前需求：实现多会话管理和历史记录功能

### 需求描述
1. 支持历史聊天记录
2. 每个历史聊天记录存储在postgres的conversations表里
3. 每个conversation里面的具体对话信息存储在chat_messages表里
4. 用户可以同时开启和维护多个conversations，每个conversations互不干扰
5. 用户可以在界面上看到历史的聊天记录，并且可以在chatbox里面加载每个聊天记录，继续聊天

### 设计方案
1. **数据库设计**
   - conversations表：存储会话元信息
   - chat_messages表：存储具体消息，包含thinking字段
   
2. **API设计**
   - 会话管理API：创建、列表、详情、更新、删除
   - 消息API：基于conversation_id发送和接收消息
   
3. **前端设计**
   - 左侧会话列表
   - 右侧聊天区域
   - 支持会话切换和管理

### TODO List
详见 docs/design/conversation_history_todo.md

### 相关文档
- 设计文档：docs/design/conversation_history_design.md
- 实现清单：docs/design/conversation_history_todo.md