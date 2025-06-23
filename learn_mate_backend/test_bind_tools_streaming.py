#!/usr/bin/env python3
"""Test to verify bind_tools impact on streaming."""

import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from app.core.config import settings

async def test_streaming_without_tools():
    """Test streaming without bind_tools."""
    print("=== Test 1: Streaming WITHOUT bind_tools ===")
    
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.7,
        api_key=settings.LLM_API_KEY,
        streaming=True,
    )
    
    messages = [HumanMessage(content="Count from 1 to 5")]
    chunk_count = 0
    
    print("Streaming response:")
    async for chunk in llm.astream(messages):
        if chunk.content:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {repr(chunk.content)}", flush=True)
    
    print(f"\nTotal chunks: {chunk_count}")
    print("✅ Expected: Many small chunks" if chunk_count > 10 else "❌ Problem: Too few chunks")

async def test_streaming_with_empty_tools():
    """Test streaming with empty bind_tools."""
    print("\n\n=== Test 2: Streaming WITH bind_tools([]) ===")
    
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.7,
        api_key=settings.LLM_API_KEY,
        streaming=True,
    ).bind_tools([])  # Empty tools list
    
    messages = [HumanMessage(content="Count from 1 to 5")]
    chunk_count = 0
    
    print("Streaming response:")
    async for chunk in llm.astream(messages):
        if chunk.content:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {repr(chunk.content)}", flush=True)
    
    print(f"\nTotal chunks: {chunk_count}")
    print("✅ Expected: Many small chunks" if chunk_count > 10 else "❌ Problem: Too few chunks")

async def test_direct_llm_vs_langgraph():
    """Compare direct LLM streaming vs LangGraph streaming."""
    print("\n\n=== Test 3: Direct LLM vs LangGraph ===")
    
    from app.core.langgraph.graph import LangGraphAgent
    
    # Test direct LLM
    print("\n3a. Direct LLM streaming:")
    agent = LangGraphAgent()
    messages = [HumanMessage(content="Say hello")]
    chunk_count = 0
    
    async for chunk in agent.llm.astream(messages):
        if chunk.content:
            chunk_count += 1
            if chunk_count <= 5:
                print(f"  Chunk {chunk_count}: {repr(chunk.content)}")
    
    print(f"  Total chunks: {chunk_count}")
    
    # Test LangGraph streaming
    print("\n3b. LangGraph streaming:")
    chunk_count = 0
    
    async for chunk in agent.get_stream_response(
        [{"role": "user", "content": "Say hello"}], 
        "test-session"
    ):
        chunk_count += 1
        if chunk_count <= 5:
            print(f"  Chunk {chunk_count}: {repr(chunk)}")
    
    print(f"  Total chunks: {chunk_count}")

async def main():
    """Run all tests."""
    try:
        await test_streaming_without_tools()
        await test_streaming_with_empty_tools()
        await test_direct_llm_vs_langgraph()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())