#!/usr/bin/env python3
"""Test streaming functionality to diagnose large chunk issue."""

import asyncio
import json
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent


async def test_direct_llm_streaming():
    """Test LLM streaming directly without LangGraph."""
    print("\n=== Testing Direct LLM Streaming ===")

    # Create LLM with streaming enabled
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.7,
        api_key=settings.LLM_API_KEY,
        streaming=True,
    )

    messages = [HumanMessage(content="Count from 1 to 10 slowly, one number per line.")]

    chunk_count = 0
    start_time = time.time()
    full_content = ""

    print("Streaming response:")
    async for chunk in llm.astream(messages):
        chunk_count += 1
        content = chunk.content
        full_content += content
        elapsed = time.time() - start_time
        print(f"[Chunk {chunk_count:03d} @ {elapsed:.2f}s]: {repr(content)}")

    print(f"\nTotal chunks: {chunk_count}")
    print(f"Total time: {time.time() - start_time:.2f}s")
    print(f"Full content length: {len(full_content)}")
    print(f"Average chunk size: {len(full_content) / chunk_count:.1f} chars")


async def test_langgraph_streaming():
    """Test LangGraph streaming."""
    print("\n\n=== Testing LangGraph Streaming ===")

    agent = LangGraphAgent()
    messages = [{"role": "user", "content": "Count from 1 to 10 slowly, one number per line."}]

    chunk_count = 0
    start_time = time.time()
    full_content = ""

    print("Streaming response:")
    async for chunk in agent.get_stream_response(messages, "test-session-123"):
        chunk_count += 1
        full_content += chunk
        elapsed = time.time() - start_time
        print(f"[Chunk {chunk_count:03d} @ {elapsed:.2f}s]: {repr(chunk)}")

    print(f"\nTotal chunks: {chunk_count}")
    print(f"Total time: {time.time() - start_time:.2f}s")
    print(f"Full content length: {len(full_content)}")
    if chunk_count > 0:
        print(f"Average chunk size: {len(full_content) / chunk_count:.1f} chars")


async def test_langgraph_with_thinking():
    """Test LangGraph streaming with thinking tags."""
    print("\n\n=== Testing LangGraph Streaming with Thinking ===")

    agent = LangGraphAgent()
    messages = [{"role": "user", "content": "用 python 写一个 quick sort"}]

    chunk_count = 0
    start_time = time.time()
    full_content = ""
    chunk_sizes = []

    print("Streaming response:")
    async for chunk in agent.get_stream_response(messages, "test-session-456"):
        chunk_count += 1
        full_content += chunk
        chunk_sizes.append(len(chunk))
        elapsed = time.time() - start_time

        # Show first 100 chars of chunk
        display_chunk = chunk[:100] + "..." if len(chunk) > 100 else chunk
        print(f"[Chunk {chunk_count:03d} @ {elapsed:.2f}s, size={len(chunk):4d}]: {repr(display_chunk)}")

    print(f"\nTotal chunks: {chunk_count}")
    print(f"Total time: {time.time() - start_time:.2f}s")
    print(f"Full content length: {len(full_content)}")
    if chunk_count > 0:
        print(f"Average chunk size: {len(full_content) / chunk_count:.1f} chars")
        print(f"Min chunk size: {min(chunk_sizes)}")
        print(f"Max chunk size: {max(chunk_sizes)}")
        print(f"Chunk size distribution: {chunk_sizes[:10]}...")  # Show first 10


async def main():
    """Run all streaming tests."""
    try:
        await test_direct_llm_streaming()
        await test_langgraph_streaming()
        await test_langgraph_with_thinking()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
