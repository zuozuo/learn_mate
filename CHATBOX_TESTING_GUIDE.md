# Learn Mate Chatbox 测试指南

## 🎉 功能完成情况

✅ **已完成的功能**：
- Chrome 扩展配置（点击图标打开新标签页）
- 现代化的 chatbox UI 界面
- 多 LLM 提供商支持（OpenAI、OpenRouter、Ollama）
- 前后端 API 完整集成
- 流式和普通响应模式
- 聊天历史持久化
- 用户认证和会话管理

## 🚀 快速开始测试

### 1. 启动后端服务

```bash
# 方法一：使用便捷脚本
./start_backend.sh

# 方法二：手动启动
cd learn_mate_backend
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
unset http_proxy https_proxy all_proxy
make dev
```

后端成功启动后，你会看到：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### 2. 验证后端服务

访问以下链接确认服务正常：
- 健康检查: http://localhost:8000/health
- API 文档: http://localhost:8000/docs

### 3. 测试 Chrome 扩展

#### 开发模式加载扩展：

1. 构建前端扩展：
```bash
cd learn_mate_frontend
pnpm install  # 如果还没安装依赖
pnpm build    # 构建扩展
```

2. 在 Chrome 中加载扩展：
   - 打开 Chrome
   - 访问 `chrome://extensions/`
   - 开启"开发者模式"
   - 点击"加载已解压的扩展程序"
   - 选择 `learn_mate_frontend/dist` 目录

3. 测试扩展功能：
   - 点击扩展图标（应该会打开新标签页）
   - 新标签页应该显示 Learn Mate 聊天界面

## 🧪 测试场景

### 场景 1：基本聊天功能
1. 确保后端服务运行中
2. 点击扩展图标打开聊天界面
3. 观察连接状态（应显示"已连接"）
4. 发送消息："你好，介绍一下你自己"
5. 验证是否收到 AI 响应

### 场景 2：流式响应测试
1. 确保界面右上角显示"流式"模式
2. 发送长问题："请详细解释什么是机器学习？"
3. 观察响应是否逐字显示（流式效果）

### 场景 3：普通响应测试
1. 点击"流式"按钮切换到"普通"模式
2. 发送消息："什么是深度学习？"
3. 验证响应是否一次性完整显示

### 场景 4：聊天历史测试
1. 发送多条消息
2. 刷新页面或重新打开扩展
3. 验证聊天历史是否保持

### 场景 5：清空历史测试
1. 有聊天历史的情况下
2. 点击"清空"按钮
3. 验证消息是否全部清除

## ⚙️ LLM 提供商配置

### 使用 OpenAI（默认）
编辑 `learn_mate_backend/.env.development`：
```bash
LLM_PROVIDER="openai"
LLM_API_KEY="sk-your-actual-openai-api-key"
LLM_MODEL="gpt-4o-mini"
```

### 使用 OpenRouter
```bash
LLM_PROVIDER="openrouter"
OPENROUTER_API_KEY="sk-or-your-openrouter-key"
LLM_MODEL="openai/gpt-4o-mini"  # 或其他支持的模型
```

### 使用 Ollama（本地部署）
1. 首先安装并启动 Ollama：
```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型（如 llama3.2）
ollama pull llama3.2

# 启动 Ollama 服务
ollama serve
```

2. 配置环境变量：
```bash
LLM_PROVIDER="ollama"
LLM_MODEL="llama3.2"
OLLAMA_BASE_URL="http://localhost:11434"
```

## 🔧 故障排除

### 问题：前端显示"未连接"
**解决方案**：
1. 确认后端服务正在运行（`http://localhost:8000/health`）
2. 检查 CORS 配置是否包含前端地址
3. 查看浏览器控制台是否有错误信息

### 问题：认证失败
**解决方案**：
1. 检查数据库连接是否正常
2. 确认 PostgreSQL 服务已启动
3. 查看后端日志中的错误信息

### 问题：LLM 响应失败
**解决方案**：
1. 验证 API 密钥是否正确配置
2. 检查网络连接和代理设置
3. 查看后端日志中的 LLM 调用错误

### 问题：扩展加载失败
**解决方案**：
1. 确认前端已正确构建（`pnpm build`）
2. 检查 `dist` 目录是否存在且包含必要文件
3. 查看 Chrome 扩展页面的错误信息

## 📊 性能测试

### 响应时间测试
1. 发送相同问题多次
2. 观察响应时间的一致性
3. 比较流式和普通模式的性能差异

### 并发测试
1. 打开多个扩展标签页
2. 同时发送消息
3. 验证会话隔离是否正常

### 长时间使用测试
1. 连续聊天 30 分钟以上
2. 发送各种类型的消息
3. 检查内存使用情况

## 🎯 测试检查清单

- [ ] 后端服务正常启动
- [ ] API 文档可访问
- [ ] 扩展成功加载到 Chrome
- [ ] 点击图标打开新标签页
- [ ] 连接状态显示正常
- [ ] 基本聊天功能正常
- [ ] 流式响应工作正常
- [ ] 普通响应工作正常
- [ ] 聊天历史持久化
- [ ] 清空历史功能正常
- [ ] 错误处理显示友好消息
- [ ] 用户界面响应流畅
- [ ] 主题切换正常工作

## 💡 使用技巧

1. **快捷键**：在输入框中按 `Enter` 发送消息，`Shift+Enter` 换行
2. **模式切换**：根据需要在"流式"和"普通"模式间切换
3. **主题切换**：点击月亮/太阳图标切换亮色/暗色主题
4. **历史管理**：定期清空历史以获得更好的性能

## 🔍 开发调试

### 查看日志
```bash
# 后端日志
tail -f learn_mate_backend/logs/development-*.jsonl

# 前端控制台
# 打开 Chrome DevTools > Console
```

### API 测试
```bash
# 健康检查
curl http://localhost:8000/health

# 手动 API 测试
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

## 🎉 成功标准

当所有测试通过时，你应该拥有一个完全功能的 Learn Mate 聊天助手，支持：
- 智能对话交互
- 多种 LLM 提供商
- 现代化用户界面
- 会话持久化
- Chrome 扩展集成

祝你测试愉快！🚀