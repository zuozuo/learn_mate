# LangGraph + Ollama Token 级流式响应问题深度分析

## 摘要

本文档详细记录了在使用 LangGraph + Ollama + LangChain 技术栈时遇到的 token 级流式响应失效问题。通过深入分析和多方验证，我们发现这是一个由 `bind_tools()` 方法引起的已知上游问题，而非 LangGraph 本身的设计缺陷。

## 问题现象

### 1. 预期行为
- 使用流式 API 时，LLM 应该逐 token 输出响应
- 前端能够实时显示正在生成的内容，提供打字机效果
- 每个 chunk 应该只包含少量字符（1-5个）

### 2. 实际行为
- 整个响应作为一个大的 chunk 发送
- 包括 `<think>` 标签在内的完整内容一次性返回
- 流式 API 退化为"伪流式"（只有 1-2 个 chunks）

### 3. 具体表现

```bash
# 期望的流式输出（Ollama 直接调用）
{"content": "The", "done": false}
{"content": " word", "done": false}
{"content": " contains", "done": false}
...

# 实际的输出（通过 LangGraph）
{"content": "<think>完整的思考过程...</think>\n\n完整的回答", "done": false}
{"content": "", "done": true}
```

## 问题诊断过程

### 第一阶段：排查 LangGraph 配置

初始假设是 LangGraph 的 `stream_mode` 配置问题。

```python
# 尝试的各种 stream_mode
stream_mode="messages"  # 官方推荐用于 token 流式
stream_mode="values"    # 状态值流式
stream_mode="updates"   # 状态更新流式
```

**结论**：更改 stream_mode 并未解决问题。

### 第二阶段：验证 LLM 本身的流式能力

直接测试 Ollama API：

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:30b",  
  "messages": [{"role": "user", "content": "how many r in strawberry?"}],
  "stream": true 
}'
```

**结果**：Ollama 本身完美支持 token 级流式，每个响应只包含 1-3 个字符。

### 第三阶段：定位问题根源

通过搜索相关 GitHub issues，发现了关键线索：

1. [LangChain Issue #26971](https://github.com/langchain-ai/langchain/issues/26971)
2. [LangChain Issue #27925](https://github.com/langchain-ai/langchain/issues/27925)
3. [Ollama Issue #5796](https://github.com/ollama/ollama/issues/5796)

## 根本原因

### 核心发现：`bind_tools()` 破坏流式功能

```python
# 正常流式工作
llm = ChatOpenAI(streaming=True)
async for chunk in llm.astream(messages):  # ✅ Token 级流式

# 绑定工具后流式失效
llm_with_tools = llm.bind_tools(tools)
async for chunk in llm_with_tools.astream(messages):  # ❌ 块级传输

# 即使是空工具列表也会触发问题
llm_empty_tools = llm.bind_tools([])
async for chunk in llm_empty_tools.astream(messages):  # ❌ 同样失效
```

### 为什么会这样？

1. **工具调用机制的影响**
   - 当绑定工具时，LangChain 需要解析可能的工具调用
   - 这种解析机制与流式输出产生冲突
   - 系统需要等待足够的内容来判断是否有工具调用

2. **Ollama 的特殊性**
   - Ollama 的工具调用支持是最近添加的功能
   - 与 OpenAI 等成熟 API 的实现存在差异
   - `finish_reason` 的处理不一致导致额外的兼容性问题

3. **LangGraph 的角色**
   - LangGraph 本身没有问题
   - 但因为使用了 `bind_tools()` 来支持工具调用，间接受到影响

## 影响范围

### 受影响的场景
1. 使用 LangGraph + Ollama 的项目
2. 需要同时支持工具调用和流式响应的应用
3. 依赖 token 级流式提供实时反馈的用户界面

### 不受影响的场景
1. 不使用工具的纯对话应用
2. 使用 OpenAI API 等其他 LLM 提供商
3. 不需要流式响应的批处理应用

## 解决方案

### 方案一：分离 LLM 实例（推荐）

```python
class LangGraphAgent:
    def __init__(self):
        # 用于流式响应的 LLM（不绑定工具）
        self.llm = self._create_llm()
        
        # 用于工具调用的 LLM
        self.llm_with_tools = self._create_llm().bind_tools(tools)
    
    async def get_stream_response(self, messages, session_id):
        # 使用无工具的 LLM 进行流式
        async for chunk in self.llm.astream(messages):
            yield chunk.content
    
    async def _chat(self, state):
        # 使用带工具的 LLM 进行推理
        response = await self.llm_with_tools.ainvoke(messages)
```

**优点**：
- 立即解决问题，无需等待上游修复
- 保持所有功能正常工作
- 代码改动最小

**缺点**：
- 需要创建两个 LLM 实例
- 增加了一定的内存开销

### 方案二：条件绑定工具

```python
async def process_message(self, messages, needs_tools=False):
    if needs_tools:
        llm = self.base_llm.bind_tools(tools)
        return await llm.ainvoke(messages)
    else:
        # 流式场景不绑定工具
        async for chunk in self.base_llm.astream(messages):
            yield chunk
```

**优点**：
- 更灵活的控制
- 只在需要时才绑定工具

**缺点**：
- 需要预先判断是否需要工具
- 逻辑更复杂

### 方案三：直接 LLM 流式 + 手动状态管理

```python
async def get_stream_response(self, messages, session_id):
    # 绕过 LangGraph，直接使用 LLM
    from langchain_core.messages import SystemMessage, HumanMessage
    
    langchain_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    langchain_messages.extend(convert_messages(messages))
    
    accumulated = ""
    async for chunk in self.llm.astream(langchain_messages):
        if chunk.content:
            accumulated += chunk.content
            yield chunk.content
    
    # 手动保存到历史
    await self.save_to_history(session_id, accumulated)
```

**优点**：
- 完全控制流式过程
- 最佳性能

**缺点**：
- 绕过了 LangGraph 的部分功能
- 需要手动处理状态管理

## 监控与验证

### 1. 流式质量指标

```python
def measure_streaming_quality(chunks):
    """评估流式响应的质量"""
    metrics = {
        "total_chunks": len(chunks),
        "avg_chunk_size": sum(len(c) for c in chunks) / len(chunks),
        "max_chunk_size": max(len(c) for c in chunks),
        "streaming_score": min(100, len(chunks) * 2)  # 期望 50+ chunks
    }
    return metrics
```

### 2. 测试用例

```python
async def test_streaming_behavior():
    """验证流式行为的测试"""
    # Test 1: 无工具绑定
    assert await count_chunks(llm_no_tools) > 50
    
    # Test 2: 有工具绑定
    assert await count_chunks(llm_with_tools) < 5  # 已知问题
    
    # Test 3: 我们的解决方案
    assert await count_chunks(our_solution) > 50
```

## 上游进展

### LangChain 方面
- PR #27689 已合并，部分解决了问题
- 但完整的修复可能需要更多时间

### Ollama 方面
- PR #10415 正在改进工具调用的流式支持
- 重点是增量解析和更好的兼容性

### 预期时间线
- 2024 Q1：Ollama 完成流式工具调用支持
- 2024 Q2：LangChain 完全兼容新的 Ollama API

## 最佳实践建议

1. **短期策略**
   - 使用分离 LLM 实例的方案
   - 添加流式质量监控
   - 记录用户反馈

2. **长期策略**
   - 跟踪上游修复进度
   - 准备迁移计划
   - 保持代码的可维护性

3. **架构考虑**
   - 将流式逻辑抽象为独立模块
   - 使用策略模式支持多种实现
   - 为未来的变化预留扩展点

## 经验教训

1. **深入调查的重要性**
   - 初始假设（LangGraph 配置问题）是错误的
   - 通过查阅 GitHub issues 找到了真正原因
   - 社区的集体智慧非常宝贵

2. **分层诊断方法**
   - 从底层（Ollama API）开始验证
   - 逐层向上（LangChain → LangGraph）
   - 隔离变量，精确定位

3. **临时方案的价值**
   - 不必等待完美的上游修复
   - 实用的解决方案可以立即改善用户体验
   - 保持代码的可演进性

## 参考资料

1. [LangChain Issue #26971 - Streaming breaks with bind_tools](https://github.com/langchain-ai/langchain/issues/26971)
2. [LangChain Issue #27925 - Ollama streaming with tools](https://github.com/langchain-ai/langchain/issues/27925)
3. [Ollama Issue #5796 - Tool calling finish_reason](https://github.com/ollama/ollama/issues/5796)
4. [Ollama PR #10415 - Streaming tool call parsing](https://github.com/ollama/ollama/pull/10415)
5. [LangGraph Streaming Documentation](https://langchain-ai.github.io/langgraph/how-tos/streaming/)

## 附录：调试命令

```bash
# 测试原始 Ollama 流式
curl -N http://localhost:11434/api/chat -d '{"model":"qwen3:30b","messages":[{"role":"user","content":"count 1 to 5"}],"stream":true}'

# 测试 LangGraph 流式
python test_bind_tools_streaming.py

# 监控流式质量
python test_simple_stream.py | grep "Total chunks"
```

---

*文档版本：1.0*  
*最后更新：2024-01-23*  
*作者：Learn Mate 开发团队*