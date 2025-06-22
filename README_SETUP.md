# Learn Mate 开发环境设置指南

## 概述

本项目包含了基于 FastAPI LangGraph 模板构建的 Learn Mate 学习助手后端服务。本指南将帮助您快速设置完整的开发环境。

## 项目结构

```
learn_mate/
├── learn_mate_backend/     # FastAPI 后端服务
├── learn_mate_frontend/    # 前端应用
├── setup_dev_env.sh       # 自动化环境设置脚本
├── start_backend.sh       # 后端启动脚本
└── start_frontend.sh      # 前端启动脚本
```

## 快速开始

### 方法一：自动化设置（推荐）

1. 运行自动化设置脚本：
```bash
./setup_dev_env.sh
```

这个脚本会自动：
- 检查并安装必要的系统依赖（PostgreSQL, uv 等）
- 设置 Python 虚拟环境和依赖
- 创建并启动 PostgreSQL 数据库
- 配置环境变量文件
- 创建便捷启动脚本

### 方法二：手动设置

#### 1. 系统依赖

确保已安装以下依赖：
- Python 3.13+
- PostgreSQL 15+
- uv (Python 包管理器)
- Node.js 18+ (用于前端)

```bash
# macOS 使用 Homebrew
brew install postgresql@15
pip install uv

# 启动 PostgreSQL 服务
brew services start postgresql@15
```

#### 2. 后端环境设置

```bash
cd learn_mate_backend

# 安装依赖
uv sync

# 创建数据库
createdb learn_mate_dev

# 配置环境变量
cp .env.example .env.development
# 编辑 .env.development 文件，设置正确的配置项
```

#### 3. 前端环境设置

```bash
cd learn_mate_frontend

# 安装依赖
pnpm install
# 或
npm install
```

## 启动服务

### 后端服务

```bash
# 使用便捷脚本
./start_backend.sh

# 或手动启动
cd learn_mate_backend
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
unset http_proxy https_proxy all_proxy  # 清除代理设置
make dev
```

### 前端服务

```bash
# 使用便捷脚本
./start_frontend.sh

# 或手动启动
cd learn_mate_frontend
pnpm dev  # 或 npm run dev
```

## 访问服务

- **后端 API 文档**: http://localhost:8000/docs
- **后端健康检查**: http://localhost:8000/health
- **前端应用**: http://localhost:3000 (根据前端配置可能不同)

## 重要配置

### 环境变量配置

编辑 `learn_mate_backend/.env.development` 文件：

```bash
# 必需配置
LLM_API_KEY="your-openai-api-key-here"
POSTGRES_URL="postgresql://你的用户名:@localhost:5432/learn_mate_dev"

# 可选配置
LANGFUSE_PUBLIC_KEY="your-langfuse-public-key"  # LLM 监控
LANGFUSE_SECRET_KEY="your-langfuse-secret-key"
```

### 数据库配置

默认数据库连接：
- **主机**: localhost
- **端口**: 5432
- **数据库名**: learn_mate_dev
- **用户**: 当前系统用户
- **密码**: 无

## 常见问题

### 1. PostgreSQL 连接失败

```bash
# 确保 PostgreSQL 服务运行
brew services start postgresql@15

# 检查数据库是否存在
psql -l | grep learn_mate_dev

# 重新创建数据库
dropdb learn_mate_dev  # 如果需要删除现有数据库
createdb learn_mate_dev
```

### 2. 代理相关错误

如果遇到 SOCKS 代理错误，运行：
```bash
unset http_proxy https_proxy all_proxy
```

### 3. OpenAI API 错误

确保在 `.env.development` 中设置了有效的 OpenAI API 密钥：
```bash
LLM_API_KEY="sk-your-actual-openai-api-key"
```

### 4. 端口冲突

如果 8000 端口被占用：
```bash
# 查找占用端口的进程
lsof -i:8000

# 杀死进程
kill -9 PID
```

## 开发工具

### 代码格式化和检查

```bash
cd learn_mate_backend

# 代码格式化
make format

# 代码检查
make lint
```

### 数据库管理

```bash
# 查看数据库
psql learn_mate_dev

# 执行 SQL 脚本
psql learn_mate_dev < schema.sql
```

## 项目特性

### 后端特性
- FastAPI 高性能异步 Web 框架
- LangGraph AI Agent 工作流
- PostgreSQL 数据持久化
- JWT 身份认证
- 速率限制保护
- 结构化日志记录
- Prometheus 监控指标
- 模型评估框架

### 前端特性
- 现代化前端框架
- 与后端 API 集成
- 响应式设计
- 用户界面组件

## 部署

### Docker 部署

```bash
# 构建镜像
make docker-build-env ENV=development

# 运行容器
make docker-run-env ENV=development

# 完整监控栈
make docker-compose-up ENV=development
```

监控服务：
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## 支持

如遇到问题，请检查：
1. 系统依赖是否正确安装
2. 环境变量是否正确配置
3. 数据库服务是否正常运行
4. 网络代理设置是否正确

更多详情请参考项目文档或提出 Issue。