# LangGraph 流式响应分析报告

## 问题诊断

### 1. 现象
- 使用 LangGraph 的 `stream_mode="messages"` 时，整个响应（包括 `<think>` 标签）作为一个大块发送
- 前端收到的是完整的消息，而不是逐 token 的流式数据

### 2. 排除的因素
- ✅ **LLM 本身支持流式**：Ollama 测试显示 LLM 可以逐 token 输出
- ✅ **`<think>` 标签不阻塞**：thinking 内容也是逐 token 流式的
- ✅ **LLM 配置正确**：已设置 `streaming=True`

### 3. 根本原因
**LangGraph 的 `stream_mode="messages"` 是消息级流式，不是 token 级流式**

根据官方文档和实际测试：
- `stream_mode="messages"` 会等待整个消息生成完成后才发送
- 这是 LangGraph 当前版本的设计限制
- `astream_events` API 在 LangGraph 中可能不完全支持或需要特殊配置

## 解决方案

### 方案一：直接使用 LLM 流式（推荐）

```python
async def get_stream_response(self, messages, session_id, user_id=None):
    # 1. 直接从 LLM 获取 token 级流式
    langchain_messages = convert_to_langchain_format(messages)
    
    async for chunk in self.llm.astream(langchain_messages):
        if chunk.content:
            yield chunk.content
    
    # 2. 流式完成后保存到历史记录
    # 使用 LangGraph 的 ainvoke 保存完整对话
```

**优点**：
- 真正的 token 级流式
- 保持聊天历史功能
- 实现简单

**缺点**：
- 绕过了 LangGraph 的部分功能
- 需要手动处理历史记录

### 方案二：使用自定义流式（Custom Stream Mode）

根据 LangGraph 文档，可以使用 `StreamWriter` 实现自定义流式：

```python
# 在 LLM 节点中使用 StreamWriter
from langgraph.checkpoint.base import get_stream_writer

async def chat_node(state):
    stream_writer = get_stream_writer()
    
    # 流式生成并写入
    async for token in llm.astream(messages):
        await stream_writer({"token": token.content})
    
    return {"messages": [complete_message]}

# 客户端使用 stream_mode="custom"
async for chunk in graph.astream(input, stream_mode="custom"):
    print(chunk["token"])
```

**优点**：
- 保持在 LangGraph 框架内
- 可以利用 LangGraph 的所有功能

**缺点**：
- 需要修改图结构
- 实现相对复杂

### 方案三：等待 LangGraph 更新

监控 LangGraph 的更新，等待官方支持真正的 token 级流式。

## 建议

1. **短期方案**：使用方案一（直接 LLM 流式），快速解决问题
2. **长期方案**：考虑方案二或等待 LangGraph 更新
3. **监控**：添加详细的流式监控，确保性能符合预期

## 技术细节

### LangGraph Stream Modes 对比

| Mode | 描述 | Token 级流式 | 适用场景 |
|------|------|------------|---------|
| `"values"` | 完整状态 | ❌ | 调试、状态跟踪 |
| `"updates"` | 状态更新 | ❌ | 增量更新监控 |
| `"messages"` | 消息级 | ❌（当前实现） | 消息传递 |
| `"custom"` | 自定义 | ✅（需实现） | 灵活的流式需求 |

### 性能对比

- **Ollama 直接流式**：~600+ chunks，真正的 token 级
- **LangGraph messages 模式**：1-2 chunks，消息级
- **预期的 token 级流式**：应该有 100+ chunks

## 参考资料

1. [LangGraph Streaming Documentation](https://langchain-ai.github.io/langgraph/how-tos/streaming/)
2. [LangGraph Stream Modes](https://langchain-ai.github.io/langgraph/concepts/streaming/)
3. [Custom Streaming with StreamWriter](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/concepts/streaming.md)