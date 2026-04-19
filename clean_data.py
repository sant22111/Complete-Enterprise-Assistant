#!/usr/bin/env python3
"""
Clean all existing data to start fresh.
Deletes: chunks, embeddings, logs, documents
"""

import os
import shutil

def clean_directory(path, description):
    """Remove directory and recreate empty."""
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"✓ Deleted {description}: {path}")
    os.makedirs(path, exist_ok=True)
    print(f"✓ Created fresh {description}: {path}")

def clean_file(path, description):
    """Remove file if exists."""
    if os.path.exists(path):
        os.remove(path)
        print(f"✓ Deleted {description}: {path}")

print("=" * 80)
print("CLEANING ALL DATA - FRESH START")
print("=" * 80)
print()

# Clean storage systems
clean_directory("data/chroma_db", "Vector Store (ChromaDB)")
clean_directory("data/whoosh_index", "Keyword Index (Whoosh)")
clean_directory("data/graph_data", "Knowledge Graph")

# Clean logs
clean_file("logs/audit_logs.jsonl", "Audit Logs")
clean_file("logs/ingestion_registry.jsonl", "Ingestion Registry")
clean_file("logs/document_versions.jsonl", "Document Versions")

# Clean old sample documents
if os.path.exists("sample_documents"):
    for file in os.listdir("sample_documents"):
        file_path = os.path.join("sample_documents", file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    print(f"✓ Deleted old sample documents")
else:
    os.makedirs("sample_documents", exist_ok=True)
    print(f"✓ Created sample_documents directory")

print()
print("=" * 80)
print("✓ CLEANUP COMPLETE - Ready for fresh ingestion")
print("=" * 80)
print()
print("Next steps:")
print("1. Generate new documents: python generate_sample_docs.py")
print("2. Start server: python -m uvicorn main:app --reload --port 8000")
print()
