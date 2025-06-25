# Latest User Requirements

## 当前任务：账号登录功能实现

### 需求描述
添加账号登录功能，支持用户注册、登录、认证和会话管理。

### 设计方案
1. **功能需求**：
   - 用户注册（邮箱+密码）
   - 用户登录
   - 密码重置
   - 会话管理（JWT Token）
   - 自动登录（Remember Me）
   - 登出功能

2. **技术架构**：
   - 后端：FastAPI + SQLAlchemy + PostgreSQL + JWT + bcrypt
   - 前端：React + TypeScript + Axios + React Context

3. **安全措施**：
   - 密码使用 bcrypt 加密（cost factor: 12）
   - JWT Token 认证（Access Token: 1小时，Refresh Token: 7天）
   - 登录保护（连续失败5次锁定15分钟）

### 进度跟踪
- [x] 创建设计文档 docs/design/account-login-design.md
- [ ] 实现后端用户认证系统
  - [ ] 创建用户数据模型
  - [ ] 实现密码加密工具
  - [ ] 实现 JWT 工具类
  - [ ] 创建认证路由和控制器
  - [ ] 添加认证中间件
  - [ ] 更新现有 API 添加认证保护
- [ ] 实现前端登录界面和逻辑
  - [ ] 创建登录/注册页面组件
  - [ ] 实现 AuthContext 和 useAuth Hook
  - [ ] 创建 API 认证拦截器
  - [ ] 实现路由保护
  - [ ] 添加自动登录功能
- [ ] 集成前后端登录功能
- [ ] 测试登录功能

### 注意事项
1. 需要考虑与现有临时用户系统的兼容性
2. 数据迁移方案：为现有对话记录添加 user_id 字段
3. 确保所有敏感操作都需要认证
4. 实现合理的会话超时机制