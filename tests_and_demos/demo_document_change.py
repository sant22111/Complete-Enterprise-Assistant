#!/usr/bin/env python3
"""
Simple demo: Edit a document and see what happens.
Shows hash change, chunk deletion, and re-creation.
"""

from mock_sharepoint.api import MockSharePointAPI
from ingestion.ingestion_registry import IngestionRegistry
from config import storage_config
import shutil
import os

print("\n" + "="*80)
print("DOCUMENT CHANGE DEMO - Simple Example")
print("="*80 + "\n")

# Clean up
for path in [storage_config.chroma_db_path, storage_config.whoosh_index_path, 
             "./data/knowledge_graph", storage_config.ingestion_registry_path]:
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

# Initialize
sharepoint_api = MockSharePointAPI()
registry = IngestionRegistry(storage_config.ingestion_registry_path)

# Get the flipkart document
doc_id = "doc_0000"
doc_content_original = sharepoint_api.download_document(doc_id)

print("[STEP 1] ORIGINAL DOCUMENT")
print("-" * 80)
print("File: flipkart_proposal.txt")
print(f"Content length: {len(doc_content_original)} characters")
print(f"\nFirst 200 characters:")
print(doc_content_original[:200])

# Compute hash
hash_original = sharepoint_api.compute_file_hash(doc_content_original)
print(f"\nHash (SHA256): {hash_original}")
print(f"Hash length: {len(hash_original)} characters")

# Store in registry
registry.register_ingestion(
    document_id=doc_id,
    file_hash=hash_original,
    chunk_count=1,
    status="success"
)
print(f"\n✓ Stored in registry with hash: {hash_original[:16]}...")

# Now edit the document
print("\n" + "="*80)
print("[STEP 2] EDIT THE DOCUMENT")
print("-" * 80)

doc_path = "./sample_documents/flipkart_proposal.txt"
with open(doc_path, 'r') as f:
    content = f.read()

# Make a small edit - remove a period
edited_content = content.replace("Approval:", "Approval")
print("Change made: Removed a period from 'Approval:'")
print("(Just 1 character removed)")

with open(doc_path, 'w') as f:
    f.write(edited_content)

# Reload and check hash
sharepoint_api = MockSharePointAPI()  # Reload to get new content
doc_content_edited = sharepoint_api.download_document(doc_id)
hash_edited = sharepoint_api.compute_file_hash(doc_content_edited)

print(f"\nNew content length: {len(doc_content_edited)} characters")
print(f"Old content length: {len(doc_content_original)} characters")
print(f"Difference: {len(doc_content_original) - len(doc_content_edited)} character(s)")

print(f"\nNew hash (SHA256): {hash_edited}")
print(f"Old hash (SHA256): {hash_original}")

# Compare hashes
print("\n" + "="*80)
print("[STEP 3] COMPARE HASHES")
print("-" * 80)

if hash_original == hash_edited:
    print("❌ Hashes are SAME - Document unchanged")
else:
    print("✅ Hashes are DIFFERENT - Document changed!")
    print(f"\nOld hash: {hash_original[:32]}...")
    print(f"New hash: {hash_edited[:32]}...")
    print("\nEven though only 1 period was removed,")
    print("the entire hash is completely different!")

# What happens next
print("\n" + "="*80)
print("[STEP 4] WHAT HAPPENS NEXT")
print("-" * 80)

print("When system detects hash changed:\n")
print("1. DELETE old chunks:")
print("   ✓ Remove chunk from vector_store")
print("   ✓ Remove chunk from keyword_index")
print("   ✓ Remove chunk from knowledge_graph")
print("   ✓ Delete all entities linked to this chunk")
print("   ✓ Delete all relationships linked to this chunk")
print("\n2. CREATE new chunks:")
print("   ✓ Read modified document")
print("   ✓ Run PII redaction (staging)")
print("   ✓ Split into chunks")
print("   ✓ Add to vector_store (new embeddings)")
print("   ✓ Add to keyword_index (new keywords)")
print("   ✓ Add to knowledge_graph (new entities)")
print("\n3. UPDATE registry:")
print(f"   ✓ Store NEW hash: {hash_edited[:32]}...")
print("   ✓ Store NEW timestamp: 2026-04-17T02:15:30.123456")
print("   ✓ Update chunk count")
print("   ✓ Mark status: success")
print("\n4. AUDIT TRAIL:")
print("   ✓ Log entry created with timestamp")
print("   ✓ Shows what PII was redacted")
print("   ✓ Shows approval status")
print("   ✓ Complete history maintained")

# Restore original
with open(doc_path, 'w') as f:
    f.write(content)

print("="*80)
print("✓ Demo complete - Original file restored")
print("="*80)
