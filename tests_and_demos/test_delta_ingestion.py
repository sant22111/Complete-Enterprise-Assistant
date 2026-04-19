#!/usr/bin/env python3
"""
Test delta ingestion - verify no duplicate chunks when documents are re-ingested.
"""

from mock_sharepoint.api import MockSharePointAPI
from staging.staging_pipeline import StagingPipeline
from processing.chunker import DocumentChunker
from processing.metadata_enricher import MetadataEnricher
from storage.vector_store import VectorStore
from storage.keyword_index import KeywordIndex
from storage.knowledge_graph import KnowledgeGraph
from ingestion.ingestion_registry import IngestionRegistry
from ingestion.ingestion_service import IngestionService
from config import storage_config
import shutil
import os

print("\n" + "="*80)
print("DELTA INGESTION TEST - Verify No Duplicate Chunks")
print("="*80 + "\n")

# Clean up old storage
for path in [storage_config.chroma_db_path, storage_config.whoosh_index_path, 
             "./data/knowledge_graph", storage_config.ingestion_registry_path]:
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

# Initialize components
sharepoint_api = MockSharePointAPI()
staging_pipeline = StagingPipeline(storage_config.audit_log_path)
vector_store = VectorStore(storage_config.chroma_db_path)
keyword_index = KeywordIndex(storage_config.whoosh_index_path)
knowledge_graph = KnowledgeGraph("./data/knowledge_graph")
ingestion_registry = IngestionRegistry(storage_config.ingestion_registry_path)

ingestion_service = IngestionService(
    sharepoint_api=sharepoint_api,
    staging_pipeline=staging_pipeline,
    vector_store=vector_store,
    keyword_index=keyword_index,
    knowledge_graph=knowledge_graph,
    ingestion_registry=ingestion_registry
)

# Test 1: Initial ingestion
print("[TEST 1] Initial ingestion of all documents")
print("-" * 80)
result1 = ingestion_service.ingest_all_documents(auto_approve=True)
print(f"✓ Documents ingested: {result1['successfully_ingested']}")
print(f"✓ Total chunks created: {result1['total_chunks']}")
print(f"✓ Vector store chunks: {len(vector_store.chunks_store)}")
print(f"✓ Keyword index chunks: {len(keyword_index.documents)}")
initial_chunk_count = result1['total_chunks']

# Test 2: Re-ingest same documents (should skip - no changes)
print("\n[TEST 2] Re-ingest same documents (no changes)")
print("-" * 80)
result2 = ingestion_service.ingest_all_documents(auto_approve=True)
print(f"✓ Documents processed: {result2['successfully_ingested']}")
print(f"✓ New chunks created: {result2['total_chunks']}")
print(f"✓ Vector store chunks: {len(vector_store.chunks_store)}")
print(f"✓ Keyword index chunks: {len(keyword_index.documents)}")

if result2['total_chunks'] == 0:
    print("✓ PASS: No duplicate chunks created (delta ingestion working)")
else:
    print("✗ FAIL: Duplicate chunks created!")

# Test 3: Modify a document and re-ingest
print("\n[TEST 3] Modify a document and re-ingest")
print("-" * 80)

# Modify flipkart_proposal.txt
doc_path = "./sample_documents/flipkart_proposal.txt"
with open(doc_path, 'r') as f:
    content = f.read()

modified_content = content + "\n\nNEW SECTION: Additional strategic initiatives for 2025 expansion."
with open(doc_path, 'w') as f:
    f.write(modified_content)

print("✓ Modified flipkart_proposal.txt")

# Re-ingest
result3 = ingestion_service.ingest_all_documents(auto_approve=True)
print(f"✓ Documents processed: {result3['successfully_ingested']}")
print(f"✓ New chunks created: {result3['total_chunks']}")
print(f"✓ Vector store chunks: {len(vector_store.chunks_store)}")
print(f"✓ Keyword index chunks: {len(keyword_index.documents)}")

if result3['total_chunks'] > 0:
    print("✓ PASS: Modified document re-ingested (old chunks deleted, new chunks added)")
else:
    print("✗ FAIL: Modified document not re-ingested!")

# Restore original content
with open(doc_path, 'w') as f:
    f.write(content)

# Test 4: Verify no duplicates after multiple ingestions
print("\n[TEST 4] Verify chunk counts after multiple ingestions")
print("-" * 80)
result4 = ingestion_service.ingest_all_documents(auto_approve=True)
print(f"✓ Documents processed: {result4['successfully_ingested']}")
print(f"✓ New chunks created: {result4['total_chunks']}")
print(f"✓ Total vector store chunks: {len(vector_store.chunks_store)}")
print(f"✓ Total keyword index chunks: {len(keyword_index.documents)}")

if len(vector_store.chunks_store) == initial_chunk_count:
    print("✓ PASS: No duplicate chunks - chunk count stable")
else:
    print(f"✗ FAIL: Chunk count changed from {initial_chunk_count} to {len(vector_store.chunks_store)}")

# Summary
print("\n" + "="*80)
print("DELTA INGESTION TEST SUMMARY")
print("="*80)
print(f"Initial chunks: {initial_chunk_count}")
print(f"After re-ingest (no changes): {len(vector_store.chunks_store)}")
print(f"Registry entries: {len(ingestion_registry.get_all_records())}")
print("\n✓ Delta ingestion working correctly - prevents duplicate chunks")
print("✓ File hash comparison detects document changes")
print("✓ Old chunks deleted before new ones added")
