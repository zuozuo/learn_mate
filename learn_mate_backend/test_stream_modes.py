#!/usr/bin/env python3
"""Test different stream modes in LangGraph to understand streaming behavior."""

import asyncio
import time
from app.core.langgraph.graph import LangGraphAgent
from app.utils import dump_messages

async def test_stream_mode(mode: str, description: str):
    """Test a specific stream mode."""
    print(f"\n=== Testing stream_mode='{mode}' - {description} ===")
    
    agent = LangGraphAgent()
    if agent._graph is None:
        agent._graph = await agent.create_graph()
    
    messages = [{"role": "user", "content": "Write the numbers 1 to 5, one per line."}]
    config = {"configurable": {"thread_id": f"test-{mode}"}}
    
    chunk_count = 0
    start_time = time.time()
    
    try:
        print(f"Streaming with mode '{mode}':")
        async for chunk in agent._graph.astream(
            {"messages": dump_messages(messages), "session_id": f"test-{mode}"}, 
            config, 
            stream_mode=mode
        ):
            chunk_count += 1
            elapsed = time.time() - start_time
            
            # Format output based on stream mode
            if mode == "messages":
                # chunk is expected to be (msg, metadata) tuple
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    msg, metadata = chunk
                    content = getattr(msg, 'content', str(msg))
                    node = metadata.get('langgraph_node', 'unknown')
                    print(f"[Chunk {chunk_count:03d} @ {elapsed:.2f}s] Node: {node}, Content: {repr(content[:100])}")
                else:
                    print(f"[Chunk {chunk_count:03d} @ {elapsed:.2f}s] Unexpected format: {type(chunk)}")
            else:
                # For other modes, just print the chunk
                chunk_str = str(chunk)[:200]
                print(f"[Chunk {chunk_count:03d} @ {elapsed:.2f}s]: {repr(chunk_str)}")
        
        print(f"Total chunks: {chunk_count}")
        print(f"Total time: {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"Error with mode '{mode}': {e}")
        import traceback
        traceback.print_exc()

async def test_custom_streaming():
    """Test custom streaming implementation with token-level output."""
    print("\n=== Testing Custom Token-Level Streaming ===")
    
    agent = LangGraphAgent()
    if agent._graph is None:
        agent._graph = await agent.create_graph()
    
    # Modify the prompt to encourage token-by-token output
    messages = [{"role": "user", "content": "Count: 1 2 3 4 5"}]
    config = {"configurable": {"thread_id": "test-custom"}}
    
    chunk_count = 0
    start_time = time.time()
    accumulated_content = ""
    
    try:
        # Try to get more granular streaming
        async for event in agent._graph.astream_events(
            {"messages": dump_messages(messages), "session_id": "test-custom"}, 
            config,
            version="v2"
        ):
            chunk_count += 1
            elapsed = time.time() - start_time
            
            # Check for LLM token events
            if event["event"] == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    accumulated_content += content
                    print(f"[Token {chunk_count:03d} @ {elapsed:.2f}s]: {repr(content)}")
            elif event["event"] == "on_chat_model_end":
                print(f"[End @ {elapsed:.2f}s] Model finished")
        
        print(f"\nTotal events: {chunk_count}")
        print(f"Total time: {time.time() - start_time:.2f}s")
        print(f"Accumulated content: {repr(accumulated_content[:200])}")
        
    except Exception as e:
        print(f"Error with custom streaming: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all streaming mode tests."""
    # Test different stream modes
    await test_stream_mode("values", "Full state values")
    await test_stream_mode("updates", "State updates only")
    await test_stream_mode("messages", "Message updates (current implementation)")
    
    # Test custom streaming
    await test_custom_streaming()

if __name__ == "__main__":
    asyncio.run(main())