# Ollama 本地 LLM 设置指南

为了快速测试 Learn Mate chatbox 而无需 OpenAI API 密钥，我们可以使用 Ollama 来运行本地 LLM。

## 🚀 快速设置 Ollama

### 1. 安装 Ollama

```bash
# macOS 使用 Homebrew
brew install ollama

# 或者使用官方安装脚本
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. 下载并运行模型

```bash
# 下载 llama3.2 模型（推荐，体积较小）
ollama pull llama3.2

# 或者下载其他模型
ollama pull llama3.2:1b      # 更小的模型
ollama pull qwen2.5:0.5b     # 非常小的模型
ollama pull codellama        # 专门用于编程的模型
```

### 3. 启动 Ollama 服务

```bash
# 启动 Ollama 服务（在后台运行）
ollama serve
```

你应该看到类似的输出：
```
2024/01/01 10:00:00 images.go:806: total blobs: 0
2024/01/01 10:00:00 images.go:813: total unused blobs removed: 0
2024/01/01 10:00:00 routes.go:1000: Listening on 127.0.0.1:11434 (version 0.x.x)
```

### 4. 验证 Ollama 正常工作

```bash
# 测试模型
ollama run llama3.2
# 输入一些问题，如 "Hello, how are you?"
# 按 Ctrl+D 退出

# 或者通过 API 测试
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

## 🔧 配置 Learn Mate 使用 Ollama

环境配置已经更新为使用 Ollama。确认 `learn_mate_backend/.env.development` 包含：

```bash
LLM_PROVIDER="ollama"
LLM_API_KEY=""
LLM_MODEL="llama3.2"
OLLAMA_BASE_URL="http://localhost:11434"
```

## 🧪 测试完整流程

### 1. 启动服务

```bash
# 终端 1: 启动 Ollama
ollama serve

# 终端 2: 启动后端
./start_backend.sh
```

### 2. 加载前端扩展

```bash
cd learn_mate_frontend
pnpm build
# 在 Chrome 中加载 dist 目录
```

### 3. 测试聊天

1. 点击扩展图标
2. 等待连接状态显示"已连接"
3. 发送消息："你好，请介绍一下你自己"
4. 观察是否收到 Ollama 的响应

## 📊 模型推荐

### 轻量级模型（推荐用于测试）
- `qwen2.5:0.5b` - 500MB，响应快
- `llama3.2:1b` - 1GB，质量较好
- `phi3:mini` - 2GB，Microsoft 的小模型

### 性能更好的模型
- `llama3.2` - 3GB，平衡性能和质量
- `qwen2.5:7b` - 7GB，更好的中文支持
- `codellama` - 专门用于编程任务

### 查看已安装的模型

```bash
ollama list
```

### 切换模型

只需要修改 `.env.development` 中的 `LLM_MODEL` 值：

```bash
LLM_MODEL="qwen2.5:0.5b"  # 切换到更小的模型
```

然后重启后端服务。

## 🔍 故障排除

### 问题：Ollama 服务启动失败
**解决方案**：
```bash
# 检查端口是否被占用
lsof -i:11434

# 强制停止 Ollama
pkill ollama

# 重新启动
ollama serve
```

### 问题：模型下载缓慢
**解决方案**：
```bash
# 使用镜像加速（如果在中国）
export OLLAMA_HOST=https://ollama.mirror.example.com
ollama pull llama3.2
```

### 问题：模型响应缓慢
**解决方案**：
1. 使用更小的模型（如 `qwen2.5:0.5b`）
2. 确保有足够的内存
3. 关闭其他占用内存的应用

### 问题：后端连接失败
**解决方案**：
1. 确认 Ollama 在 `http://localhost:11434` 运行
2. 检查防火墙设置
3. 验证 `OLLAMA_BASE_URL` 配置正确

## 💡 优化建议

### 1. 预加载模型
```bash
# 预加载模型到内存中，加快响应速度
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "",
  "keep_alive": "5m"
}'
```

### 2. 调整配置
```bash
# 减少最大 token 数以提高响应速度
MAX_TOKENS=1000

# 调整温度参数
DEFAULT_LLM_TEMPERATURE=0.3
```

### 3. 系统资源
- 建议至少 8GB 内存
- SSD 硬盘可以加快模型加载
- Apple Silicon Mac 性能更好

## 🔄 切换回 OpenAI

如果以后想使用 OpenAI，只需修改配置：

```bash
LLM_PROVIDER="openai"
LLM_API_KEY="sk-your-actual-openai-api-key"
LLM_MODEL="gpt-4o-mini"
```

然后重启后端服务即可。

## ✅ 完成测试

现在你可以：
1. 无需 API 密钥测试完整的聊天功能
2. 体验本地 LLM 的隐私优势
3. 在没有网络的情况下使用

享受你的本地 AI 助手！🎉