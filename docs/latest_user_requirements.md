# Latest User Requirements

## 当前任务：账号登录功能实现 - 第二阶段

### 任务描述
完成账号登录功能的实现，包括前后端集成和测试。

### 已完成工作

1. **设计文档**
   - ✅ 创建了详细的设计文档 `docs/design/account-login-design.md`

2. **后端实现**
   - ✅ 扩展 User 模型添加认证字段（username, is_active, is_verified, last_login_at）
   - ✅ 创建 LoginHistory 模型记录登录历史
   - ✅ 实现 JWT 认证工具（JWTManager）
   - ✅ 创建认证 API 端点（/auth/register, /auth/login, /auth/refresh, /auth/logout, /auth/me）
   - ✅ 实现 AuthServiceSync 处理认证业务逻辑
   - ✅ 修复同步/异步数据库不一致问题

3. **前端实现**
   - ✅ 创建 Login 组件（登录/注册界面）
   - ✅ 实现 AuthContext 和 useAuth Hook
   - ✅ 更新 authService 支持账号登录
   - ✅ 集成登录界面到 NewTab 组件
   - ✅ 添加登出功能

4. **数据库迁移**
   - ✅ 创建 Alembic 迁移添加认证字段
   - ✅ 创建 login_history 表

### 当前问题

1. **测试失败**
   - 部分测试因为缺少 username 字段而失败
   - 需要运行数据库迁移更新表结构

2. **待完成工作**
   - 修复所有测试，确保 before_commit.sh 通过
   - 手动测试前后端集成的登录功能
   - 添加密码重置功能（可选）
   - 完善错误处理和用户提示

### 技术要点

1. **认证流程**
   - 使用 JWT 双令牌机制（access token + refresh token）
   - 支持"记住我"功能（返回 refresh token）
   - 登录历史记录追踪

2. **安全措施**
   - bcrypt 密码加密（cost factor 12）
   - JWT 有效期：access token 1小时，refresh token 7天
   - 登录失败记录

3. **兼容性**
   - 保留临时用户（访客模式）功能
   - 支持从访客升级为注册用户

### 下一步行动

1. 运行数据库迁移：`alembic upgrade head`
2. 修复测试中的 username 字段问题
3. 手动测试登录功能：
   - 注册新用户
   - 登录/登出
   - 访客模式
   - Token 刷新

### 相关文件

- 设计文档：`/docs/design/account-login-design.md`
- 后端认证：`/app/api/v1/account.py`, `/app/services/auth_service_sync.py`
- 前端组件：`/pages/new-tab/src/components/Login.tsx`
- 认证上下文：`/pages/new-tab/src/contexts/AuthContext.tsx`
- 数据库迁移：`/alembic/versions/e0c85538e3c1_add_user_authentication_tables.py`