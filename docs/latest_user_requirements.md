# Latest User Requirements

## 当前任务：清理旧认证代码

### 任务描述
清理 learn_mate_backend 中的旧认证代码，包括：
1. 删除旧的 /register 和 /login 端点
2. 删除相关测试文件
3. 更新路由配置

### 已完成工作

1. **清理 auth.py**
   - ✅ 删除了 `/register` 端点（第170-204行）
   - ✅ 删除了 `/login` 端点（第206-251行）
   - ✅ 清理了不再需要的导入语句
   - ✅ 保留了 session 相关的端点

2. **删除测试文件**
   - ✅ 删除了 `tests/api/v1/test_auth.py` 文件

3. **更新路由配置**
   - ✅ 修改 `app/api/v1/api.py`，将 auth_router 的前缀改为 `/sessions`
   - ✅ 更新 auth.py 中的路由定义，适配新的前缀

### 当前问题

执行 `before_commit.sh` 时测试失败，原因是：
- 某些测试在创建用户时没有提供 username 字段
- 数据库服务已经自动为用户生成默认 username

### 路由变更总结

旧路由：
- `/api/v1/auth/register` -> 已删除
- `/api/v1/auth/login` -> 已删除
- `/api/v1/auth/session` -> `/api/v1/sessions`
- `/api/v1/auth/session/{id}/name` -> `/api/v1/sessions/{id}/name`
- `/api/v1/auth/session/{id}` -> `/api/v1/sessions/{id}`
- `/api/v1/auth/sessions` -> `/api/v1/sessions`

新认证路由（在 account.py 中）：
- `/api/v1/auth/register`
- `/api/v1/auth/login`
- `/api/v1/auth/refresh`
- `/api/v1/auth/logout`
- `/api/v1/auth/me`

### 下一步行动

1. 提交当前的代码变更
2. 运行数据库迁移确保表结构最新
3. 修复其他测试中的 username 字段问题（如果有）

### 相关文件

- 修改的文件：
  - `/app/api/v1/auth.py` - 删除了旧端点，保留 session 端点
  - `/app/api/v1/api.py` - 更新了路由前缀
  - 删除了 `/tests/api/v1/test_auth.py`
- 新认证系统：
  - `/app/api/v1/account.py` - 新的认证端点
  - `/app/services/auth_service_sync.py` - 认证业务逻辑