#!/usr/bin/env python3
"""
Verify the actual query response.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("\nTesting query endpoint...\n")

response = requests.post(f"{BASE_URL}/query", json={
    "query": "What is the strategic expansion plan?",
    "top_k": 3
}, timeout=10)

data = response.json()

print("Full Response:")
print(json.dumps(data, indent=2))

print("\n" + "="*80)
if data.get('status') == 'success':
    print("✓ SUCCESS: You can ask questions!")
    print(f"Answer: {data.get('answer')}")
    print(f"Confidence: {data.get('confidence')}")
    print(f"Sources: {len(data.get('sources', []))} documents")
else:
    print(f"Status: {data.get('status')}")
    print(f"Message: {data.get('message')}")
