#!/usr/bin/env python3
"""测试流式传输是否正常工作的脚本"""

import asyncio
import json
import time
import httpx


async def test_streaming():
    """测试流式响应"""
    # 配置
    base_url = "http://localhost:8000"
    auth_token = "your-auth-token-here"  # 替换为实际的 token
    
    # 准备请求数据
    data = {
        "messages": [
            {
                "role": "user",
                "content": "写一个关于春天的短诗，要有韵律感"
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    print("开始测试流式响应...")
    print("-" * 50)
    
    chunk_count = 0
    first_chunk_time = None
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST", 
            f"{base_url}/api/v1/chat/stream",
            json=data,
            headers=headers,
            timeout=30.0
        ) as response:
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            print("-" * 50)
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_count += 1
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        print(f"第一个 chunk 到达时间: {first_chunk_time - start_time:.3f}秒")
                    
                    try:
                        data = json.loads(line[6:])
                        content = data.get("content", "")
                        done = data.get("done", False)
                        
                        current_time = time.time() - start_time
                        print(f"[{current_time:.3f}s] Chunk #{chunk_count}: {repr(content[:50])}... (长度: {len(content)})")
                        
                        if done:
                            print(f"\n流式传输完成，总共 {chunk_count} 个 chunks")
                            break
                    except json.JSONDecodeError:
                        print(f"解析错误: {line}")
    
    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.3f}秒")
    print(f"平均每个 chunk: {total_time / chunk_count:.3f}秒" if chunk_count > 0 else "没有收到 chunks")


async def test_direct_llm_streaming():
    """直接测试 LLM 流式传输"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    import os
    
    print("\n" + "=" * 50)
    print("测试直接 LLM 流式传输...")
    print("=" * 50)
    
    # 创建带流式传输的 LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        streaming=True,
        api_key=os.getenv("LLM_API_KEY")
    )
    
    messages = [HumanMessage(content="写一个关于春天的短诗")]
    
    chunk_count = 0
    start_time = time.time()
    
    async for chunk in llm.astream(messages):
        chunk_count += 1
        current_time = time.time() - start_time
        content = chunk.content
        print(f"[{current_time:.3f}s] Chunk #{chunk_count}: {repr(content)}")
    
    print(f"\n直接 LLM 流式传输: 总共 {chunk_count} 个 chunks")


if __name__ == "__main__":
    print("注意：请确保后端服务正在运行，并且已经设置了正确的认证 token")
    print("如果需要测试直接 LLM 流式传输，请确保设置了 LLM_API_KEY 环境变量\n")
    
    # 运行测试
    asyncio.run(test_streaming())
    
    # 可选：测试直接 LLM 流式传输
    # asyncio.run(test_direct_llm_streaming())