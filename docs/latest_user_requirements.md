# Latest User Requirements

## 当前任务：修复消息分支测试问题

### 问题描述
- test_get_message_versions 测试会hang住不结束

### 根本原因
1. get_message_versions 方法中存在潜在的无限循环（当消息版本链形成循环引用时）
2. 数据库约束设计不合理，导致编辑消息时违反唯一性约束
3. 测试使用了错误的 fixture

### 已完成修复
1. ✅ 重写 get_message_versions 方法，添加循环检测机制
2. ✅ 更新数据库约束，允许同一 message_index 在不同分支/版本中存在
3. ✅ 修复测试中的 fixture 使用（mock_db_session → session）
4. ✅ 修复 edit_message 服务中的异步调用问题

### 待办事项
1. 修复 API 测试中的 fixture 问题（test_message_branch_api.py）
2. 完善消息编辑功能的异步 AI 响应生成
3. 添加更多边界情况的测试用例