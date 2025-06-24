#!/usr/bin/env python3
"""Simple test to verify streaming behavior."""

import requests
import time
import json

# Test URL
url = "http://localhost:8000/api/v1/chatbot/chat/stream"

# Auth token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkMjkxN2ZjMC0yMjY1LTQxOWMtYTY4Ny01MDUwZjYzYjY3NGQiLCJleHAiOjE3NTMyNTM2MzMsImlhdCI6MTc1MDY2MTYzMywianRpIjoiZDI5MTdmYzAtMjI2NS00MTljLWE2ODctNTA1MGY2M2I2NzRkLTE3NTA2NjE2MzMuNjc4NzA2In0.005ZGx-dxEXlfFDf1FciYWXzke5Qmr_PnlpRfBGXyyw"

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

data = {"messages": [{"role": "user", "content": "Say 'hello world'"}]}

print("Testing streaming response...")
print("-" * 50)

# Make streaming request
response = requests.post(url, headers=headers, json=data, stream=True)

chunk_count = 0
start_time = time.time()
total_content = ""

for line in response.iter_lines():
    if line:
        chunk_count += 1
        elapsed = time.time() - start_time
        line_str = line.decode("utf-8")

        if line_str.startswith("data: "):
            try:
                json_data = json.loads(line_str[6:])
                content = json_data.get("content", "")
                done = json_data.get("done", False)

                total_content += content

                print(f"[Chunk {chunk_count:03d} @ {elapsed:.2f}s] Size: {len(content):4d} chars, Done: {done}")

                if content and len(content) < 100:
                    print(f"  Content: {repr(content)}")
                elif content:
                    print(f"  Content: {repr(content[:100])}...")

            except json.JSONDecodeError as e:
                print(f"[Chunk {chunk_count:03d}] JSON decode error: {e}")

print("-" * 50)
print(f"\nTotal chunks: {chunk_count}")
print(f"Total time: {time.time() - start_time:.2f}s")
print(f"Total content length: {len(total_content)}")

# Check if response was actually streamed
if chunk_count <= 2:
    print("\n⚠️  WARNING: Response was sent as large chunks, not true streaming!")
else:
    print("\n✅ Response appears to be properly streamed")
