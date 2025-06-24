#!/usr/bin/env python3
"""验证流式响应修复效果."""

import asyncio
from app.core.langgraph.graph import LangGraphAgent
from app.schemas import Message


async def verify_fix():
    """验证bind_tools问题的修复."""
    print("=== 验证流式响应修复 ===\n")

    agent = LangGraphAgent()
    messages = [Message(role="user", content="解释什么是递归，用简单的例子说明")]
    session_id = "test-streaming-fix"

    print("1. 测试修复后的流式响应:")
    print("-" * 50)

    chunk_count = 0
    total_content = ""
    thinking_chunks = 0
    response_chunks = 0

    try:
        async for chunk in agent.get_stream_response(messages, session_id):
            chunk_count += 1
            total_content += chunk

            # 统计thinking和response的chunks
            if "<think>" in total_content and "</think>" not in total_content:
                thinking_chunks += 1
            else:
                response_chunks += 1

            # 只显示前10个chunks
            if chunk_count <= 10:
                print(f"Chunk {chunk_count}: {repr(chunk)}")
            elif chunk_count == 11:
                print("... (更多chunks)")

        print(f"\n总chunks数: {chunk_count}")
        print(f"- Thinking阶段chunks: {thinking_chunks}")
        print(f"- Response阶段chunks: {response_chunks}")
        print(f"总字符数: {len(total_content)}")
        print(f"平均每chunk字符数: {len(total_content) / chunk_count:.2f}")

        # 分析内容
        if "<think>" in total_content and "</think>" in total_content:
            think_start = total_content.find("<think>")
            think_end = total_content.find("</think>") + 8
            thinking_part = total_content[think_start:think_end]
            response_part = total_content[think_end:].strip()

            print("\n内容分析:")
            print(f"- Thinking部分长度: {len(thinking_part)} 字符")
            print(f"- Response部分长度: {len(response_part)} 字符")
            print(f"- Thinking内容预览: {thinking_part[:100]}...")
            print(f"- Response内容预览: {response_part[:100]}...")

        # 评估
        print("\n评估结果:")
        if chunk_count > 50:
            print("✅ 优秀！真正的token级流式响应")
            print("✅ bind_tools问题已成功解决")
        elif chunk_count > 20:
            print("✅ 良好的流式响应")
            print("✅ 基本达到token级效果")
        else:
            print("❌ 流式响应仍有问题")
            print(f"❌ chunks太少 ({chunk_count}), 可能仍受bind_tools影响")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("2. 对比LLM实例状态:")
    print("-" * 50)
    print(f"- agent.llm (用于流式): {type(agent.llm).__name__}")
    print(f"  - 有bind_tools: {'bind_tools' in dir(agent.llm)}")
    print(f"  - streaming设置: {getattr(agent.llm, 'streaming', 'N/A')}")

    print(f"\n- agent.llm_with_tools (用于推理): {type(agent.llm_with_tools).__name__}")
    print(f"  - 有bind_tools: {'bind_tools' in dir(agent.llm_with_tools)}")
    print(f"  - tool_calls: {hasattr(agent.llm_with_tools, 'tool_calls')}")


if __name__ == "__main__":
    asyncio.run(verify_fix())
