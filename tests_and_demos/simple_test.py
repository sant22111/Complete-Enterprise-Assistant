#!/usr/bin/env python3
"""
Simple test - ingest then query.
"""

import requests
import time

BASE_URL = "http://localhost:8000"

print("\n" + "="*80)
print("SIMPLE TEST: INGEST + QUERY")
print("="*80 + "\n")

time.sleep(1)

print("[1] Ingesting documents...")
try:
    response = requests.post(f"{BASE_URL}/ingest", json={"auto_approve": True}, timeout=10)
    data = response.json()
    print(f"✓ Status: {data.get('status')}")
    print(f"✓ Documents: {data.get('ingestion_results', {}).get('successfully_ingested', 0)}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

print("\n[2] Querying knowledge base...")
queries = [
    "What is the strategic expansion plan?",
    "Tell me about technology initiatives",
    "What are the financial projections?"
]

for query in queries:
    print(f"\n  Q: {query}")
    try:
        response = requests.post(f"{BASE_URL}/query", json={
            "query": query,
            "top_k": 3
        }, timeout=10)
        data = response.json()
        
        if data.get('status') == 'success':
            print(f"  ✓ Answer: {data.get('answer', '')[:80]}...")
            print(f"  ✓ Confidence: {data.get('confidence', 0):.2f}")
        else:
            print(f"  ⚠ {data.get('message', 'No answer')}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n" + "="*80)
print("✓ TEST COMPLETE - You can now ask questions!")
print("="*80 + "\n")
