#!/usr/bin/env python3
"""Test the new token-level streaming implementation."""

import asyncio
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.langgraph.graph import LangGraphAgent

async def test_token_streaming():
    """Test the new token-level streaming implementation."""
    print("=== Testing Token-Level Streaming ===")
    
    agent = LangGraphAgent()
    
    # Test with a prompt that should generate thinking + response
    messages = [{"role": "user", "content": "用 python 写一个 bubble sort"}]
    
    print("\nStreaming response:")
    print("-" * 50)
    
    chunk_count = 0
    char_count = 0
    start_time = time.time()
    last_chunk_time = start_time
    chunk_intervals = []
    
    try:
        async for chunk in agent.get_stream_response(messages, "test-token-stream"):
            chunk_count += 1
            char_count += len(chunk)
            
            current_time = time.time()
            interval = current_time - last_chunk_time
            chunk_intervals.append(interval)
            last_chunk_time = current_time
            
            # Print chunk inline
            print(chunk, end='', flush=True)
            
            # Log chunk details to stderr for analysis
            print(f"\n[DEBUG] Chunk {chunk_count}: {len(chunk)} chars, interval: {interval:.3f}s", 
                  file=sys.stderr)
        
        print("\n" + "-" * 50)
        
        total_time = time.time() - start_time
        
        print(f"\nStreaming Statistics:")
        print(f"- Total chunks: {chunk_count}")
        print(f"- Total characters: {char_count}")
        print(f"- Total time: {total_time:.2f}s")
        print(f"- Average chunk size: {char_count/chunk_count:.1f} chars")
        print(f"- Average interval: {sum(chunk_intervals)/len(chunk_intervals):.3f}s")
        print(f"- Min interval: {min(chunk_intervals):.3f}s")
        print(f"- Max interval: {max(chunk_intervals):.3f}s")
        
        # Check if streaming is working properly
        if chunk_count < 10:
            print("\n⚠️  WARNING: Very few chunks received. Streaming might not be working properly.")
        else:
            print("\n✅ Token-level streaming appears to be working!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_streaming():
    """Test with a simple prompt that should stream character by character."""
    print("\n\n=== Testing Simple Streaming ===")
    
    agent = LangGraphAgent()
    
    # Simple prompt without thinking tags
    messages = [{"role": "user", "content": "Count from 1 to 10"}]
    
    print("\nStreaming response:")
    print("-" * 50)
    
    chunk_count = 0
    start_time = time.time()
    
    try:
        async for chunk in agent.get_stream_response(messages, "test-simple-stream"):
            chunk_count += 1
            print(chunk, end='', flush=True)
        
        print("\n" + "-" * 50)
        print(f"\nTotal chunks: {chunk_count}")
        print(f"Total time: {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests."""
    await test_token_streaming()
    await test_simple_streaming()

if __name__ == "__main__":
    # Enable debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    asyncio.run(main())