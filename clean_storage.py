#!/usr/bin/env python3
"""
Clean only storage systems (for re-ingestion).
Keeps: sample documents
Deletes: chunks, embeddings, indexes, graphs, logs
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
print("CLEANING STORAGE SYSTEMS - KEEPING DOCUMENTS")
print("=" * 80)
print()

# Clean all 3 storage systems
clean_directory("data/chroma_db", "Vector Store (ChromaDB)")
clean_directory("data/whoosh_index", "Keyword Index (Whoosh)")
clean_directory("data/graph_data", "Knowledge Graph")

# Also clean data root if it has pickle files
if os.path.exists("data"):
    for file in os.listdir("data"):
        if file.endswith('.pkl'):
            file_path = os.path.join("data", file)
            os.remove(file_path)
            print(f"✓ Deleted pickle file: {file}")

# Clean logs
clean_file("logs/audit_logs.jsonl", "Audit Logs")
clean_file("logs/ingestion_registry.jsonl", "Ingestion Registry")
clean_file("logs/document_versions.jsonl", "Document Versions")

# Count existing documents (don't delete them)
doc_count = 0
if os.path.exists("sample_documents"):
    doc_count = len([f for f in os.listdir("sample_documents") 
                     if f.endswith(('.txt', '.pdf', '.pptx', '.docx'))])

print()
print("=" * 80)
print(f"✓ STORAGE CLEANED - {doc_count} documents preserved")
print("=" * 80)
print()
print("Next step:")
print("  Start server to re-ingest existing documents")
print("  python -m uvicorn main:app --reload --port 8000")
print()
