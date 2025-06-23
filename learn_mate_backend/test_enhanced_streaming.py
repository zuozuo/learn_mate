#!/usr/bin/env python3
"""Test enhanced streaming implementation."""

import asyncio
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.langgraph.graph import LangGraphAgent
from app.utils import dump_messages


async def test_message_structure():
    """Test to understand the actual structure of messages in stream_mode='messages'."""
    print("=== Testing Message Structure ===\n")
    
    agent = LangGraphAgent()
    if agent._graph is None:
        agent._graph = await agent.create_graph()
    
    messages = [{"role": "user", "content": "Count from 1 to 5"}]
    config = {"configurable": {"thread_id": "test-structure"}}
    
    print("Analyzing first 5 chunks:")
    chunk_count = 0
    
    async for msg, metadata in agent._graph.astream(
        {"messages": dump_messages(messages), "session_id": "test-structure"}, 
        config, 
        stream_mode="messages"
    ):
        chunk_count += 1
        
        print(f"\n--- Chunk {chunk_count} ---")
        print(f"Message type: {type(msg)}")
        print(f"Message attrs: {[attr for attr in dir(msg) if not attr.startswith('_')][:10]}")
        
        if hasattr(msg, 'content'):
            content = str(msg.content)
            print(f"Content length: {len(content)}")
            print(f"Content preview: {repr(content[:100])}...")
            
        print(f"Metadata: {metadata}")
        
        if chunk_count >= 5:
            break
            
    print(f"\nTotal chunks received: {chunk_count}")


async def test_token_streaming():
    """Test if we can achieve true token-level streaming."""
    print("\n\n=== Testing Token-Level Streaming ===\n")
    
    agent = LangGraphAgent()
    if agent._graph is None:
        agent._graph = await agent.create_graph()
    
    # Use a prompt that should generate streaming output
    messages = [{"role": "user", "content": "Write the word 'hello' letter by letter"}]
    config = {"configurable": {"thread_id": "test-tokens"}}
    
    token_count = 0
    tokens = []
    start_time = time.time()
    
    print("Streaming tokens:")
    async for msg, metadata in agent._graph.astream(
        {"messages": dump_messages(messages), "session_id": "test-tokens"}, 
        config, 
        stream_mode="messages"
    ):
        if metadata.get("langgraph_node") == "chat" and hasattr(msg, 'content') and msg.content:
            token_count += 1
            token = msg.content
            tokens.append(token)
            elapsed = time.time() - start_time
            
            print(f"[{elapsed:.2f}s] Token {token_count}: {repr(token)}")
            
    print(f"\nTotal tokens: {token_count}")
    print(f"Token sizes: {[len(t) for t in tokens]}")
    print(f"Average token size: {sum(len(t) for t in tokens) / len(tokens):.1f} chars" if tokens else "N/A")


async def test_multiple_modes():
    """Test streaming with multiple modes."""
    print("\n\n=== Testing Multiple Stream Modes ===\n")
    
    agent = LangGraphAgent()
    if agent._graph is None:
        agent._graph = await agent.create_graph()
    
    messages = [{"role": "user", "content": "Say hello"}]
    config = {"configurable": {"thread_id": "test-multi"}}
    
    mode_counts = {"messages": 0, "updates": 0}
    
    async for mode, data in agent._graph.astream(
        {"messages": dump_messages(messages), "session_id": "test-multi"}, 
        config, 
        stream_mode=["messages", "updates"]
    ):
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        
        if mode_counts[mode] <= 2:  # Show first 2 of each type
            print(f"\n[{mode}] Chunk {mode_counts[mode]}:")
            if mode == "messages":
                msg, metadata = data
                print(f"  Content: {getattr(msg, 'content', 'N/A')}")
                print(f"  Node: {metadata.get('langgraph_node', 'N/A')}")
            else:
                print(f"  Data: {str(data)[:100]}...")
    
    print(f"\nTotal chunks by mode: {mode_counts}")


async def main():
    """Run all tests."""
    try:
        await test_message_structure()
        await test_token_streaming()
        await test_multiple_modes()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())