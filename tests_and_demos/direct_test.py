#!/usr/bin/env python3
"""
Direct test of ingestion without API.
"""

from mock_sharepoint.api import MockSharePointAPI
from staging.staging_pipeline import StagingPipeline
from storage.vector_store import VectorStore
from storage.keyword_index import KeywordIndex
from storage.knowledge_graph import KnowledgeGraph
from ingestion.ingestion_registry import IngestionRegistry
from ingestion.ingestion_service import IngestionService
from config import storage_config

print("\n" + "="*80)
print("DIRECT INGESTION TEST")
print("="*80 + "\n")

sharepoint_api = MockSharePointAPI()
staging_pipeline = StagingPipeline(storage_config.audit_log_path)
vector_store = VectorStore(storage_config.chroma_db_path)
keyword_index = KeywordIndex(storage_config.whoosh_index_path)
knowledge_graph = KnowledgeGraph()
ingestion_registry = IngestionRegistry(storage_config.ingestion_registry_path)

ingestion_service = IngestionService(
    sharepoint_api=sharepoint_api,
    staging_pipeline=staging_pipeline,
    vector_store=vector_store,
    keyword_index=keyword_index,
    knowledge_graph=knowledge_graph,
    ingestion_registry=ingestion_registry
)

print("[1] Ingesting documents...")
results = ingestion_service.ingest_all_documents(auto_approve=True)

print(f"  Documents ingested: {results['successfully_ingested']}")
print(f"  Total chunks created: {results['total_chunks']}")

print("\n[2] Checking storage systems...")
stats = ingestion_service.get_ingestion_stats()

print(f"  Vector Store: {stats['vector_store_stats']['total_chunks']} chunks")
print(f"  Keyword Index: {stats['keyword_index_stats']['total_chunks']} chunks")
print(f"  Knowledge Graph: {stats['knowledge_graph_stats']['total_entities']} entities")

print("\n[3] Checking audit logs...")
audit_logs = staging_pipeline.get_audit_logs()
print(f"  Audit entries: {len(audit_logs)}")

if stats['vector_store_stats']['total_chunks'] > 0:
    print("\n✅ SUCCESS: Chunks are stored! You can now ask questions.")
else:
    print("\n❌ PROBLEM: No chunks stored. Ingestion pipeline issue.")
    
    print("\n[DEBUG] Checking first document ingestion...")
    docs = sharepoint_api.list_documents()
    if docs:
        doc_id = docs[0]['document_id']
        print(f"  Testing with: {doc_id}")
        
        result = ingestion_service.ingest_document(doc_id, auto_approve=True)
        print(f"  Result: {result}")
        
        print(f"\n  Vector store after: {vector_store.get_stats()}")
        print(f"  Keyword index after: {keyword_index.get_stats()}")
