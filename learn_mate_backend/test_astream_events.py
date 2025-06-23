#!/usr/bin/env python3
"""Test if astream_events is available and working."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.langgraph.graph import LangGraphAgent
from app.utils import dump_messages

async def test_astream_events():
    """Test astream_events availability."""
    print("Testing astream_events...")
    
    agent = LangGraphAgent()
    
    # Ensure graph is created
    if agent._graph is None:
        agent._graph = await agent.create_graph()
    
    # Check if astream_events method exists
    if not hasattr(agent._graph, 'astream_events'):
        print("❌ ERROR: astream_events method not found!")
        print(f"Available methods: {[m for m in dir(agent._graph) if 'stream' in m]}")
        return
    
    print("✅ astream_events method found")
    
    # Test simple streaming
    messages = [{"role": "user", "content": "Say hello"}]
    config = {"configurable": {"thread_id": "test-events"}}
    
    event_count = 0
    
    try:
        print("\nTesting event stream...")
        async for event in agent._graph.astream_events(
            {"messages": dump_messages(messages), "session_id": "test-events"}, 
            config, 
            version="v2"
        ):
            event_count += 1
            event_type = event.get("event", "unknown")
            
            # Only show first few events
            if event_count <= 10:
                print(f"Event {event_count}: {event_type}")
                if event_type == "on_chat_model_stream":
                    data = event.get("data", {})
                    chunk = data.get("chunk", None)
                    if chunk and hasattr(chunk, "content"):
                        print(f"  Content: {repr(chunk.content)}")
            elif event_count == 11:
                print("... (more events)")
                
        print(f"\nTotal events: {event_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_astream_events())