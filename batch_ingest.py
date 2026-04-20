"""
Batch Ingestion Script
Ingest documents in batches of 50 to avoid overwhelming the system
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import storage_config
from mock_sharepoint.api import MockSharePointAPI
from crm.mock_crm_api import MockCRMAPI
from staging.staging_pipeline import StagingPipeline
from storage.vector_store import VectorStore
from storage.keyword_index import KeywordIndex
from storage.knowledge_graph import KnowledgeGraph
from ingestion.ingestion_registry import IngestionRegistry
from ingestion.ingestion_service import IngestionService
from ingestion.document_versioning import DocumentVersioning

def ingest_batch(start_idx=0, batch_size=50):
    """
    Ingest a batch of documents.
    
    Args:
        start_idx: Starting index (0-based)
        batch_size: Number of documents to ingest
    """
    print("=" * 80)
    print(f"BATCH INGESTION: Documents {start_idx} to {start_idx + batch_size - 1}")
    print("=" * 80)
    print()
    
    # Initialize services
    sharepoint_api = MockSharePointAPI()
    crm_api = MockCRMAPI()
    staging_pipeline = StagingPipeline(storage_config.audit_log_path)
    vector_store = VectorStore(storage_config.chroma_db_path)
    keyword_index = KeywordIndex(storage_config.whoosh_index_path)
    knowledge_graph = KnowledgeGraph()
    ingestion_registry = IngestionRegistry(storage_config.ingestion_registry_path)
    document_versioning = DocumentVersioning()
    
    ingestion_service = IngestionService(
        sharepoint_api=sharepoint_api,
        staging_pipeline=staging_pipeline,
        vector_store=vector_store,
        keyword_index=keyword_index,
        knowledge_graph=knowledge_graph,
        ingestion_registry=ingestion_registry,
        crm_api=crm_api,
        document_versioning=document_versioning
    )
    
    # Get all documents
    all_docs = sharepoint_api.list_documents()
    print(f"Total documents available: {len(all_docs)}")
    
    # Get documents to ingest in this batch
    batch_docs = all_docs[start_idx:start_idx + batch_size]
    print(f"Batch size: {len(batch_docs)}")
    print()
    
    # Ingest each document one by one (no parallel to avoid issues)
    success_count = 0
    fail_count = 0
    
    for idx, doc in enumerate(batch_docs, start=start_idx + 1):
        doc_id = doc["document_id"]
        print(f"[{idx}/{len(all_docs)}] Ingesting {doc_id}... ", end="", flush=True)
        
        try:
            result = ingestion_service.ingest_document(doc_id, auto_approve=True)
            
            if result["success"]:
                print(f"✓ ({result.get('chunk_count', 0)} chunks)")
                success_count += 1
            else:
                print(f"✗ ({result.get('error', 'Unknown error')})")
                fail_count += 1
        except Exception as e:
            print(f"✗ (Exception: {str(e)[:50]})")
            fail_count += 1
    
    # Save to disk
    print()
    print("Saving to disk...")
    vector_store.save_to_disk()
    keyword_index.save_to_disk()
    knowledge_graph.save_to_disk()
    
    print()
    print("=" * 80)
    print(f"BATCH COMPLETE: {success_count} succeeded, {fail_count} failed")
    print("=" * 80)
    print()
    
    return success_count, fail_count

def show_status():
    """Show current ingestion status."""
    ingestion_registry = IngestionRegistry(storage_config.ingestion_registry_path)
    sharepoint_api = MockSharePointAPI()
    
    all_docs = sharepoint_api.list_documents()
    ingested = []
    not_ingested = []
    
    for doc in all_docs:
        doc_id = doc["document_id"]
        record = ingestion_registry.get_record(doc_id)
        if record and record.status == "success":
            ingested.append(doc_id)
        else:
            not_ingested.append(doc_id)
    
    print("=" * 80)
    print("INGESTION STATUS")
    print("=" * 80)
    print(f"Total documents: {len(all_docs)}")
    print(f"Ingested: {len(ingested)}")
    print(f"Not ingested: {len(not_ingested)}")
    print()
    
    if not_ingested:
        print("Not ingested documents:")
        for idx, doc_id in enumerate(not_ingested[:20], 1):
            print(f"  {idx}. {doc_id}")
        if len(not_ingested) > 20:
            print(f"  ... and {len(not_ingested) - 20} more")
    print("=" * 80)
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            show_status()
        elif sys.argv[1] == "batch":
            start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            size = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            ingest_batch(start, size)
        else:
            print("Usage:")
            print("  python batch_ingest.py status              # Show current status")
            print("  python batch_ingest.py batch <start> <size>  # Ingest batch")
            print()
            print("Examples:")
            print("  python batch_ingest.py status")
            print("  python batch_ingest.py batch 0 50    # Ingest docs 0-49")
            print("  python batch_ingest.py batch 50 50   # Ingest docs 50-99")
    else:
        print("Usage:")
        print("  python batch_ingest.py status              # Show current status")
        print("  python batch_ingest.py batch <start> <size>  # Ingest batch")
        print()
        print("Examples:")
        print("  python batch_ingest.py status")
        print("  python batch_ingest.py batch 0 50    # Ingest docs 0-49")
        print("  python batch_ingest.py batch 50 50   # Ingest docs 50-99")
