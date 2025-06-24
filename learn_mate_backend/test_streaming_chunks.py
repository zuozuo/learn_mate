#!/usr/bin/env python3
"""测试流式响应的chunk数量"""

import asyncio
import aiohttp
import json


async def test_streaming():
    """测试API的流式响应质量"""
    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # 首先创建临时会话
        auth_response = await session.post(f"{base_url}/api/v1/auth/temporary", json={})
        if auth_response.status != 200:
            print(f"Failed to create temporary session: {auth_response.status}")
            return

        auth_data = await auth_response.json()
        token = auth_data.get("access_token")

        # 使用token进行流式请求
        url = f"{base_url}/api/v1/chatbot/chat/stream"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        data = {"messages": [{"role": "user", "content": "请简单解释什么是递归"}]}

        chunk_count = 0
        total_content = ""

        async with session.post(url, json=data, headers=headers) as response:
            print(f"Response status: {response.status}")

            if response.status != 200:
                text = await response.text()
                print(f"Error response: {text}")
                return

            # 读取流式响应
            async for line in response.content:
                if line:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        chunk_data = line_str[6:]
                        if chunk_data == "[DONE]":
                            break

                        try:
                            chunk_json = json.loads(chunk_data)
                            content = chunk_json.get("content", "")
                            if content:
                                chunk_count += 1
                                total_content += content

                                # 只打印前10个chunks
                                if chunk_count <= 10:
                                    print(f"Chunk {chunk_count}: {repr(content)}")
                                elif chunk_count == 11:
                                    print("... (more chunks)")
                        except json.JSONDecodeError:
                            print(f"Failed to parse chunk: {chunk_data}")

    print("\n=== 流式响应统计 ===")
    print(f"总chunks数: {chunk_count}")
    print(f"总字符数: {len(total_content)}")
    print(f"平均每个chunk字符数: {len(total_content) / chunk_count if chunk_count > 0 else 0:.2f}")

    # 检查是否包含thinking标签
    if "<think>" in total_content:
        think_start = total_content.find("<think>")
        think_end = total_content.find("</think>")
        if think_end > think_start:
            thinking_content = total_content[think_start + 7 : think_end]
            response_content = total_content[think_end + 8 :].strip()
            print("\n包含thinking标签:")
            print(f"- Thinking长度: {len(thinking_content)} 字符")
            print(f"- Response长度: {len(response_content)} 字符")

    # 评估流式质量
    if chunk_count > 50:
        print("\n✅ 优秀的token级流式响应")
    elif chunk_count > 20:
        print("\n✅ 良好的流式响应")
    elif chunk_count > 5:
        print("\n⚠️  块级流式响应（不够细粒度）")
    else:
        print("\n❌ 伪流式响应（chunks太少）")


if __name__ == "__main__":
    asyncio.run(test_streaming())
