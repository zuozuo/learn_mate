# Latest User Requirements

## 当前需求：消息修改和分支功能设计

### 需求描述
用户希望实现类似 ChatGPT 的消息编辑功能：
1. 用户可以修改某个对话中的某一条历史消息
2. 修改后重新发送，会在该节点形成一个新的消息历史分支
3. 用户可以在修改的消息上切换不同版本对应的消息历史
4. 类似树状结构的对话历史管理

### 设计方案

#### 1. 数据库设计

**消息分支表 (message_branches)**
```sql
CREATE TABLE message_branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    parent_message_id UUID REFERENCES chat_messages(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    branch_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(conversation_id, parent_message_id, sequence_number)
);
```

**修改 chat_messages 表**
```sql
ALTER TABLE chat_messages ADD COLUMN branch_id UUID REFERENCES message_branches(id) ON DELETE CASCADE;
ALTER TABLE chat_messages ADD COLUMN version_number INTEGER DEFAULT 1;
ALTER TABLE chat_messages ADD COLUMN is_current_version BOOLEAN DEFAULT true;
CREATE INDEX idx_chat_messages_branch_version ON chat_messages(branch_id, version_number);
```

#### 2. 后端API设计

**新增API端点**
- `POST /api/v1/conversations/{id}/messages/{message_id}/edit` - 编辑消息
- `GET /api/v1/conversations/{id}/branches` - 获取对话分支列表
- `POST /api/v1/conversations/{id}/branches/{branch_id}/switch` - 切换分支
- `GET /api/v1/conversations/{id}/messages/{message_id}/versions` - 获取消息版本

#### 3. 前端UI设计

**消息编辑界面**
- 每条用户消息旁添加编辑按钮
- 点击编辑进入编辑模式，显示文本框
- 编辑完成后可以发送新版本

**分支导航界面**
- 在有多个版本的消息上显示版本切换器
- 显示当前版本和总版本数 (如 "1/3")
- 左右箭头切换版本
- 分支指示器显示当前所在分支

#### 4. 实现复杂度评估

**高复杂度部分**
1. 消息树状结构管理
2. 分支切换时的状态同步
3. UI组件的版本控制
4. 数据一致性保证

**实现优先级**
1. 数据库结构设计和迁移
2. 后端API实现
3. 前端基础编辑功能
4. 分支导航和版本切换

### 实施计划
1. 设计并实现数据库结构
2. 开发后端API接口
3. 实现前端编辑和分支UI
4. 集成测试和优化

### 技术风险
1. 复杂的树状数据结构可能影响性能
2. 分支切换的状态管理复杂
3. 用户界面的直观性和易用性挑战