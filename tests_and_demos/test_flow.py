#!/usr/bin/env python3
"""
Test the complete ingestion and query flow.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_ingest():
    print("\n" + "="*80)
    print("STEP 1: INGEST DOCUMENTS")
    print("="*80)
    
    response = requests.post(f"{BASE_URL}/ingest", json={"auto_approve": True})
    data = response.json()
    
    print(f"Status: {data['status']}")
    print(f"Documents ingested: {data['ingestion_results']['successfully_ingested']}")
    print(f"Total chunks created: {data['ingestion_results']['total_chunks']}")
    print(f"Vector store chunks: {data['storage_stats']['vector_chunks']}")
    print(f"Keyword index chunks: {data['storage_stats']['keyword_chunks']}")
    print(f"Graph entities: {data['storage_stats']['graph_entities']}")
    
    return data['storage_stats']['vector_chunks'] > 0

def test_query():
    print("\n" + "="*80)
    print("STEP 2: QUERY KNOWLEDGE BASE")
    print("="*80)
    
    queries = [
        "What is the strategic expansion plan?",
        "Tell me about technology initiatives",
        "What are the financial projections?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        
        response = requests.post(f"{BASE_URL}/query", json={
            "query": query,
            "top_k": 3
        })
        data = response.json()
        
        print(f"Status: {data['status']}")
        
        if data['status'] == 'success':
            print(f"Answer: {data['answer'][:100]}...")
            print(f"Confidence: {data['confidence']:.2f}")
            print(f"Sources: {len(data['sources'])} document(s)")
        else:
            print(f"Message: {data.get('message', 'No answer found')}")

def test_audit():
    print("\n" + "="*80)
    print("STEP 3: VIEW AUDIT LOGS")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/debug/audit")
    data = response.json()
    
    print(f"Total audit entries: {data['total_logs']}")
    
    if data['audit_logs']:
        log = data['audit_logs'][0]
        print(f"\nSample audit entry:")
        print(f"  Document: {log['document_id']}")
        print(f"  Status: {log['approval_status']}")
        print(f"  Redactions: {log['redactions_count']}")
        
        if log['redactions_applied']:
            print(f"  Example redaction:")
            red = log['redactions_applied'][0]
            print(f"    Type: {red['pii_type']}")
            print(f"    Original: {red['original_text']}")
            print(f"    Redacted: {red['replacement']}")

def main():
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  ENTERPRISE RAG - COMPLETE FLOW TEST".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    try:
        time.sleep(1)
        
        chunks_exist = test_ingest()
        
        if chunks_exist:
            test_query()
        else:
            print("\n⚠️  No chunks created. Queries will not work.")
            print("This means the ingestion pipeline needs fixing.")
        
        test_audit()
        
        print("\n" + "="*80)
        print("✓ TEST COMPLETE")
        print("="*80)
        print("\nNext steps:")
        print("1. If chunks exist: You can now ask questions via /query endpoint")
        print("2. If no chunks: The chunking/storage logic needs to be fixed")
        print("3. View full API docs: http://localhost:8000/docs")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Make sure the FastAPI server is running: python main.py")

if __name__ == "__main__":
    main()
