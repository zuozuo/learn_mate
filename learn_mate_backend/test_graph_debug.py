#!/usr/bin/env python3
"""Debug LangGraph streaming issue."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.langgraph.graph import LangGraphAgent
from app.utils import dump_messages


async def test_langgraph_streaming():
    """Test different streaming approaches with LangGraph."""
    print("=== Testing LangGraph Streaming Debug ===\n")

    agent = LangGraphAgent()

    # Ensure graph is created
    if agent._graph is None:
        agent._graph = await agent.create_graph()

    messages = [{"role": "user", "content": "Say hello"}]
    config = {"configurable": {"thread_id": "test-debug"}}

    # Test 1: Check what methods are available
    print("1. Available streaming methods:")
    stream_methods = [m for m in dir(agent._graph) if "stream" in m.lower()]
    for method in stream_methods:
        print(f"   - {method}")

    # Test 2: Try the original stream_mode="messages"
    print("\n2. Testing stream_mode='messages':")
    chunk_count = 0
    try:
        async for chunk in agent._graph.astream(
            {"messages": dump_messages(messages), "session_id": "test-debug"}, config, stream_mode="messages"
        ):
            chunk_count += 1
            if chunk_count <= 3:
                print(f"   Chunk {chunk_count}: type={type(chunk)}, content={str(chunk)[:100]}...")
        print(f"   Total chunks: {chunk_count}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Try without stream_mode
    print("\n3. Testing default stream (no stream_mode):")
    chunk_count = 0
    try:
        async for chunk in agent._graph.astream(
            {"messages": dump_messages(messages), "session_id": "test-debug2"}, config
        ):
            chunk_count += 1
            if chunk_count <= 3:
                print(
                    f"   Chunk {chunk_count}: type={type(chunk)}, keys={list(chunk.keys()) if isinstance(chunk, dict) else 'N/A'}"
                )
        print(f"   Total chunks: {chunk_count}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 4: Check if astream_events exists and test it
    print("\n4. Testing astream_events:")
    if hasattr(agent._graph, "astream_events"):
        event_count = 0
        model_stream_count = 0
        try:
            async for event in agent._graph.astream_events(
                {"messages": dump_messages(messages), "session_id": "test-debug3"}, config, version="v2"
            ):
                event_count += 1
                if event["event"] == "on_chat_model_stream":
                    model_stream_count += 1
                    if model_stream_count <= 3:
                        print(f"   Stream event {model_stream_count}: {event.get('data', {}).get('chunk', '')}")

            print(f"   Total events: {event_count}")
            print(f"   Model stream events: {model_stream_count}")
        except Exception as e:
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("   astream_events method NOT found!")

    # Test 5: Direct LLM streaming through agent
    print("\n5. Testing direct LLM streaming:")
    chunk_count = 0
    try:
        from app.core.prompts import SYSTEM_PROMPT
        from app.utils import prepare_messages

        prepared_messages = prepare_messages(messages, agent.llm, SYSTEM_PROMPT)
        async for chunk in agent.llm.astream(prepared_messages):
            chunk_count += 1
            if chunk_count <= 3 and chunk.content:
                print(f"   Chunk {chunk_count}: {repr(chunk.content)}")
        print(f"   Total chunks: {chunk_count}")
    except Exception as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_langgraph_streaming())
