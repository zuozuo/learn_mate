# 账号登录功能设计文档

## 1. 概述

本文档描述 LearnMate 应用的账号登录功能设计，包括用户注册、登录、认证和会话管理。

## 2. 功能需求

### 2.1 核心功能
- 用户注册（邮箱+密码）
- 用户登录
- 密码重置
- 会话管理（JWT Token）
- 自动登录（Remember Me）
- 登出功能

### 2.2 安全要求
- 密码加密存储（bcrypt）
- JWT Token 认证
- Token 过期管理
- 防止暴力破解（登录频率限制）

## 3. 技术架构

### 3.1 后端技术栈
- FastAPI 框架
- SQLAlchemy ORM
- PostgreSQL 数据库
- JWT 认证
- bcrypt 密码加密

### 3.2 前端技术栈
- React
- TypeScript
- Axios（HTTP 请求）
- React Context（状态管理）
- LocalStorage（Token 存储）

## 4. 数据模型

### 4.1 用户表（users）
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);
```

### 4.2 登录记录表（login_history）
```sql
CREATE TABLE login_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    ip_address VARCHAR(45),
    user_agent TEXT,
    login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE
);
```

## 5. API 设计

### 5.1 注册接口
```
POST /api/auth/register
Request:
{
    "email": "user@example.com",
    "username": "username",
    "password": "password123"
}
Response:
{
    "message": "User registered successfully",
    "user_id": "uuid"
}
```

### 5.2 登录接口
```
POST /api/auth/login
Request:
{
    "email": "user@example.com",
    "password": "password123",
    "remember_me": false
}
Response:
{
    "access_token": "jwt_token",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "username": "username"
    }
}
```

### 5.3 刷新Token接口
```
POST /api/auth/refresh
Headers: Authorization: Bearer <refresh_token>
Response:
{
    "access_token": "new_jwt_token",
    "token_type": "bearer",
    "expires_in": 3600
}
```

### 5.4 登出接口
```
POST /api/auth/logout
Headers: Authorization: Bearer <access_token>
Response:
{
    "message": "Logged out successfully"
}
```

### 5.5 获取当前用户信息
```
GET /api/auth/me
Headers: Authorization: Bearer <access_token>
Response:
{
    "id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "created_at": "2024-01-01T00:00:00Z"
}
```

## 6. 前端实现

### 6.1 路由设计
- `/login` - 登录页面
- `/register` - 注册页面
- `/forgot-password` - 忘记密码页面
- 受保护路由使用 PrivateRoute 组件

### 6.2 状态管理
使用 React Context 管理认证状态：
- AuthContext: 存储用户信息和认证状态
- useAuth Hook: 提供认证相关方法

### 6.3 Token 管理
- Access Token 存储在内存中
- Refresh Token 存储在 httpOnly Cookie 中（可选）
- 自动刷新机制

## 7. 安全措施

### 7.1 密码策略
- 最小长度：8个字符
- 必须包含：大小写字母、数字
- 使用 bcrypt 加密（cost factor: 12）

### 7.2 Token 安全
- Access Token 有效期：1小时
- Refresh Token 有效期：7天
- Token 黑名单机制

### 7.3 登录保护
- 连续失败5次后锁定账号15分钟
- 记录所有登录尝试
- 异常登录提醒

## 8. 实现步骤

### 8.1 后端实现
1. 创建用户数据模型
2. 实现密码加密工具
3. 实现 JWT 工具类
4. 创建认证路由和控制器
5. 添加认证中间件
6. 更新现有 API 添加认证保护

### 8.2 前端实现
1. 创建登录/注册页面组件
2. 实现 AuthContext 和 useAuth Hook
3. 创建 API 认证拦截器
4. 实现路由保护
5. 添加自动登录功能

## 9. 数据迁移

对于现有数据：
1. 为现有对话记录添加 user_id 字段
2. 创建默认用户迁移现有数据
3. 更新相关 API 支持多用户

## 10. 测试计划

### 10.1 单元测试
- 密码加密/验证
- JWT 生成/验证
- API 端点测试

### 10.2 集成测试
- 完整登录流程
- Token 刷新机制
- 会话过期处理

### 10.3 安全测试
- SQL 注入测试
- 暴力破解防护
- Token 伪造测试