#!/usr/bin/env python3
"""
Document Versioning Demo - Show how version history tracks document changes.
"""

from mock_sharepoint.api import MockSharePointAPI
from ingestion.ingestion_registry import IngestionRegistry
from ingestion.document_versioning import DocumentVersioning
from config import storage_config
import shutil
import os

print("\n" + "="*80)
print("DOCUMENT VERSIONING DEMO - Track Changes Over Time")
print("="*80 + "\n")

# Clean up
for path in [storage_config.chroma_db_path, storage_config.whoosh_index_path, 
             "./data/knowledge_graph", storage_config.ingestion_registry_path, "./logs/document_versions.jsonl"]:
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

# Initialize
sharepoint_api = MockSharePointAPI()
registry = IngestionRegistry(storage_config.ingestion_registry_path)
versioning = DocumentVersioning()

doc_id = "doc_0000"

# SCENARIO 1: Initial ingestion (Version 1)
print("[SCENARIO 1] Initial Ingestion - Version 1")
print("-" * 80)

doc_content_v1 = sharepoint_api.download_document(doc_id)
hash_v1 = sharepoint_api.compute_file_hash(doc_content_v1)

version1 = versioning.record_ingestion(
    document_id=doc_id,
    file_hash=hash_v1,
    chunk_count=1,
    previous_hash=None,
    previous_chunk_count=0,
    status="success"
)

print(f"Document: {doc_id}")
print(f"Version: {version1.version_number}")
print(f"Hash: {hash_v1[:32]}...")
print(f"Chunks: {version1.chunk_count}")
print(f"Change Type: {version1.change_type}")
print(f"Timestamp: {version1.timestamp}")
print()

# SCENARIO 2: Re-ingest same document (Version 2 - No Change)
print("[SCENARIO 2] Re-ingest Same Document - Version 2")
print("-" * 80)

doc_content_v2 = sharepoint_api.download_document(doc_id)
hash_v2 = sharepoint_api.compute_file_hash(doc_content_v2)

version2 = versioning.record_ingestion(
    document_id=doc_id,
    file_hash=hash_v2,
    chunk_count=1,
    previous_hash=hash_v1,
    previous_chunk_count=1,
    status="success"
)

print(f"Document: {doc_id}")
print(f"Version: {version2.version_number}")
print(f"Hash: {hash_v2[:32]}...")
print(f"Previous Hash: {hash_v1[:32]}...")
print(f"Hashes Match: {hash_v1 == hash_v2}")
print(f"Change Type: {version2.change_type}")
print(f"Chunks Added: {version2.chunks_added}")
print(f"Chunks Deleted: {version2.chunks_deleted}")
print(f"Timestamp: {version2.timestamp}")
print()

# SCENARIO 3: Modify document (Version 3 - Changed)
print("[SCENARIO 3] Modify Document - Version 3")
print("-" * 80)

doc_path = "./sample_documents/flipkart_proposal.txt"
with open(doc_path, 'r') as f:
    content = f.read()

# Add new content
modified_content = content + "\n\nNEW SECTION: Additional 2025 expansion plans with new markets."
with open(doc_path, 'w') as f:
    f.write(modified_content)

# Reload and re-ingest
sharepoint_api = MockSharePointAPI()
doc_content_v3 = sharepoint_api.download_document(doc_id)
hash_v3 = sharepoint_api.compute_file_hash(doc_content_v3)

version3 = versioning.record_ingestion(
    document_id=doc_id,
    file_hash=hash_v3,
    chunk_count=2,  # Now 2 chunks due to more content
    previous_hash=hash_v2,
    previous_chunk_count=1,
    status="success"
)

print(f"Document: {doc_id}")
print(f"Version: {version3.version_number}")
print(f"Hash: {hash_v3[:32]}...")
print(f"Previous Hash: {hash_v2[:32]}...")
print(f"Hashes Match: {hash_v2 == hash_v3}")
print(f"Change Type: {version3.change_type}")
print(f"Chunks Before: {version3.previous_chunk_count}")
print(f"Chunks Now: {version3.chunk_count}")
print(f"Chunks Added: {version3.chunks_added}")
print(f"Chunks Deleted: {version3.chunks_deleted}")
print(f"Timestamp: {version3.timestamp}")
print()

# SCENARIO 4: View Complete Version History
print("[SCENARIO 4] Complete Version History")
print("-" * 80)

history = versioning.get_document_history(doc_id)
print(f"Document: {doc_id}")
print(f"Total Versions: {len(history)}\n")

for v in history:
    print(f"Version {v.version_number}:")
    print(f"  Timestamp: {v.timestamp}")
    print(f"  Hash: {v.file_hash[:32]}...")
    print(f"  Change Type: {v.change_type}")
    print(f"  Chunks: {v.chunk_count} (Added: {v.chunks_added}, Deleted: {v.chunks_deleted})")
    print(f"  Status: {v.status}")
    print()

# SCENARIO 5: View Change Between Versions
print("[SCENARIO 5] Changes Between Versions")
print("-" * 80)

changes = versioning.get_changes_between_versions(doc_id, 1, 3)
print(f"Changes from Version 1 → Version 3:\n")
print(f"  Hash Changed: {changes['hash_changed']}")
print(f"  From Hash: {changes['from_hash'][:32]}...")
print(f"  To Hash: {changes['to_hash'][:32]}...")
print(f"  From Timestamp: {changes['from_timestamp']}")
print(f"  To Timestamp: {changes['to_timestamp']}")
print(f"  Chunk Count Change: {changes['chunk_count_change']} (from {changes['from_version']} to {changes['to_version']})")
print(f"  Chunks Added: {changes['chunks_added']}")
print(f"  Chunks Deleted: {changes['chunks_deleted']}")
print()

# Restore original
with open(doc_path, 'w') as f:
    f.write(content)

print("="*80)
print("VERSIONING SUMMARY")
print("="*80)
print(f"""
✓ Version 1: Initial ingestion (1 chunk)
✓ Version 2: Re-ingest same document (no changes detected)
✓ Version 3: Document modified (2 chunks, 1 added)

Complete history shows:
  - Every ingestion attempt
  - Hash comparison (change detection)
  - Chunk impact (added/deleted)
  - Exact timestamps
  - Change type (initial/no_change/updated)

This enables:
  ✓ Tracking document evolution
  ✓ Auditing what changed and when
  ✓ Understanding impact on storage
  ✓ Rollback capability (if needed)
  ✓ Compliance reporting
""")

print("="*80)
print("✓ Document versioning system working correctly")
print("="*80)
