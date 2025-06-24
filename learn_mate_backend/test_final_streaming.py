#!/usr/bin/env python3
"""最终测试：验证前后端流式响应效果."""

import asyncio
from app.core.langgraph.graph import LangGraphAgent
from app.schemas import Message


async def test_streaming():
    """测试流式响应，模拟前端行为."""
    print("=== 测试前后端流式响应效果 ===\n")

    agent = LangGraphAgent()
    messages = [Message(role="user", content="什么是递归？请先思考再回答")]
    session_id = "test-final-streaming"

    # 模拟前端的StreamParser行为
    buffer = ""
    is_in_thinking = False
    thinking_content = ""
    response_content = ""
    chunk_count = 0

    print("开始流式响应...\n")

    try:
        async for chunk in agent.get_stream_response(messages, session_id):
            chunk_count += 1
            buffer += chunk

            # 检查thinking开始
            if not is_in_thinking and "<think>" in buffer:
                parts = buffer.split("<think>")
                if parts[0]:
                    response_content += parts[0]
                    print(f"[Response] {parts[0]}", end="", flush=True)
                is_in_thinking = True
                buffer = parts[1] if len(parts) > 1 else ""
                print("\n\n--- 开始思考 ---")

            # 检查thinking结束
            elif is_in_thinking and "</think>" in buffer:
                parts = buffer.split("</think>")
                thinking_content += parts[0]
                print(f"[Thinking] {parts[0]}", end="", flush=True)
                is_in_thinking = False
                buffer = parts[1] if len(parts) > 1 else ""
                print("\n--- 思考结束 ---\n")

            # 输出内容
            elif is_in_thinking:
                # 在thinking模式，实时输出thinking内容
                print(f"[Thinking] {buffer}", end="", flush=True)
                thinking_content += buffer
                buffer = ""
            else:
                # 在response模式，实时输出response内容
                print(f"[Response] {buffer}", end="", flush=True)
                response_content += buffer
                buffer = ""

        print("\n\n=== 流式统计 ===")
        print(f"总chunks数: {chunk_count}")
        print(f"Thinking内容长度: {len(thinking_content)} 字符")
        print(f"Response内容长度: {len(response_content)} 字符")
        print(f"平均每chunk字符数: {(len(thinking_content) + len(response_content)) / chunk_count:.2f}")

        if chunk_count > 50:
            print("\n✅ 优秀！真正的token级流式响应")
            print("✅ thinking和response都能实时流式显示")
        elif chunk_count > 20:
            print("\n✅ 良好的流式响应效果")
        else:
            print("\n⚠️  流式效果有待改进")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_streaming())
