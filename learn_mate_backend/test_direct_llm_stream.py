#!/usr/bin/env python3
"""Test direct LLM streaming without LangGraph."""

import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

async def test_direct_streaming():
    """Test streaming directly from the LLM."""
    print("=== Testing Direct LLM Streaming ===")
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return
    
    # Create LLM with streaming enabled
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=api_key,
        streaming=True,
    )
    
    # Test messages
    messages = [
        SystemMessage(content="You are a helpful assistant. Use <think> tags to show your reasoning."),
        HumanMessage(content="Count from 1 to 5")
    ]
    
    print("\nStreaming response:")
    print("-" * 50)
    
    chunk_count = 0
    total_content = ""
    
    try:
        async for chunk in llm.astream(messages):
            chunk_count += 1
            content = chunk.content
            total_content += content
            
            # Show each chunk
            if content:
                print(content, end='', flush=True)
                
            # Debug info to stderr
            if chunk_count % 10 == 0:
                print(f"\n[DEBUG] Chunk {chunk_count}", file=sys.stderr)
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "-" * 50)
    print(f"\nStatistics:")
    print(f"- Total chunks: {chunk_count}")
    print(f"- Total characters: {len(total_content)}")
    print(f"- Average chunk size: {len(total_content)/chunk_count:.1f} chars")
    
    if chunk_count < 10:
        print("\n⚠️  WARNING: Very few chunks. Streaming might not be working properly.")
    else:
        print("\n✅ Streaming appears to be working!")

if __name__ == "__main__":
    import sys
    asyncio.run(test_direct_streaming())