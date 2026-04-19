import sys
import json
from datetime import datetime

from mock_sharepoint.api import MockSharePointAPI
from staging.staging_pipeline import StagingPipeline
from storage.vector_store import VectorStore
from storage.keyword_index import KeywordIndex
from storage.knowledge_graph import KnowledgeGraph
from ingestion.ingestion_registry import IngestionRegistry
from ingestion.ingestion_service import IngestionService
from retrieval.hybrid_retriever import HybridRetriever
from reasoning.evidence_builder import EvidencePackBuilder
from reasoning.llm_pipeline import LLMPipeline
from guardrails.guardrails import Guardrails
from utils.embeddings import EmbeddingService
from config import storage_config

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_subsection(title):
    print(f"\n{title}")
    print("-" * 80)

def demo_sharepoint_api():
    print_section("1. MOCK SHAREPOINT API")
    
    api = MockSharePointAPI()
    
    print_subsection("Available Documents in SharePoint")
    documents = api.list_documents()
    for doc in documents[:3]:
        print(f"  • {doc['document_id']}: {doc['client']} - {doc['document_type']}")
    print(f"  ... and {len(documents) - 3} more documents")
    
    print_subsection("Document Metadata Example")
    sample_doc = api.get_document_metadata(documents[0]['document_id'])
    print(json.dumps(sample_doc, indent=2))
    
    print_subsection("Delta Sync (Changed Documents)")
    changes = api.get_changes()
    print(f"  Documents changed in last 30 days: {len(changes)}")

def demo_staging_pipeline():
    print_section("2. STAGING LAYER (PII Detection & Redaction)")
    
    api = MockSharePointAPI()
    staging = StagingPipeline(storage_config.audit_log_path)
    
    doc_id = "doc_0000"
    doc_content = api.download_document(doc_id)
    
    print_subsection("Original Document Content")
    print(f"  {doc_content[:150]}...")
    
    staged_doc = staging.process_document(
        document_id=doc_id,
        raw_content=doc_content,
        file_format=".pdf",
        auto_approve=True
    )
    
    print_subsection("After PII Redaction")
    print(f"  {staged_doc.redacted_text[:150]}...")
    
    print_subsection("PII Detected & Redacted")
    print(f"  Total PII instances found: {staged_doc.pii_detected_count}")
    for redaction in staged_doc.redactions_applied[:3]:
        print(f"    • {redaction['pii_type']}: {redaction['original_text']} → {redaction['replacement']}")
    
    print_subsection("Audit Log Entry")
    audit_logs = staging.get_audit_logs(doc_id)
    if audit_logs:
        log = audit_logs[0]
        print(f"  Document ID: {log.document_id}")
        print(f"  Approval Status: {log.approval_status}")
        print(f"  Redactions Applied: {len(log.redactions_applied)}")
        print(f"  Timestamp: {log.timestamp}")

def demo_ingestion_pipeline():
    print_section("3. FULL INGESTION PIPELINE")
    
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
    
    print_subsection("Ingesting All Documents")
    results = ingestion_service.ingest_all_documents(auto_approve=True)
    
    print(f"  Total Documents: {results['total_documents']}")
    print(f"  Successfully Ingested: {results['successfully_ingested']}")
    print(f"  Failed Ingestions: {results['failed_ingestions']}")
    print(f"  Total Chunks Created: {results['total_chunks']}")
    
    print_subsection("Storage System Statistics")
    stats = ingestion_service.get_ingestion_stats()
    print(f"  Vector Store: {stats['vector_store_stats']['total_chunks']} chunks")
    print(f"  Keyword Index: {stats['keyword_index_stats']['total_chunks']} chunks")
    print(f"  Knowledge Graph: {stats['knowledge_graph_stats']['total_entities']} entities")
    
    return ingestion_service

def demo_hybrid_retrieval(ingestion_service):
    print_section("4. HYBRID RETRIEVAL ENGINE")
    
    hybrid_retriever = HybridRetriever(
        vector_store=ingestion_service.vector_store,
        keyword_index=ingestion_service.keyword_index,
        knowledge_graph=ingestion_service.knowledge_graph
    )
    
    embedding_service = EmbeddingService()
    
    queries = [
        "What is the strategic expansion plan for Flipkart?",
        "Tell me about technology initiatives",
        "What are the financial projections?"
    ]
    
    for query in queries:
        print_subsection(f"Query: {query}")
        
        query_embedding = embedding_service.embed_query(query)
        retrieved_chunks, debug_info = hybrid_retriever.retrieve(
            query=query,
            query_embedding=query_embedding,
            top_k=3
        )
        
        print(f"  Vector Results: {debug_info['vector_results_count']}")
        print(f"  Keyword Results: {debug_info['keyword_results_count']}")
        print(f"  Graph Hits: {debug_info['graph_hits']}")
        print(f"  Selected Chunks: {len(debug_info['selected_chunks'])}")
        
        if retrieved_chunks:
            top_result = retrieved_chunks[0]
            print(f"\n  Top Result (Score: {top_result.final_score:.3f}):")
            print(f"    Text: {top_result.text[:100]}...")
            print(f"    Source: {top_result.document_id}")
            print(f"    Client: {top_result.metadata.get('client')}")

def demo_evidence_and_reasoning(ingestion_service):
    print_section("5. EVIDENCE PACK & 3-STAGE LLM PIPELINE")
    
    hybrid_retriever = HybridRetriever(
        vector_store=ingestion_service.vector_store,
        keyword_index=ingestion_service.keyword_index,
        knowledge_graph=ingestion_service.knowledge_graph
    )
    
    evidence_builder = EvidencePackBuilder()
    llm_pipeline = LLMPipeline()
    embedding_service = EmbeddingService()
    
    query = "What is the strategic direction for digital transformation?"
    
    print_subsection("Retrieving Evidence")
    query_embedding = embedding_service.embed_query(query)
    retrieved_chunks, debug_info = hybrid_retriever.retrieve(
        query=query,
        query_embedding=query_embedding,
        top_k=5
    )
    
    print(f"  Retrieved {len(retrieved_chunks)} chunks")
    
    print_subsection("Building Evidence Pack")
    evidence_pack = evidence_builder.build_evidence_pack(
        query=query,
        retrieved_chunks=retrieved_chunks,
        debug_info=debug_info
    )
    
    print(f"  Evidence Chunks: {len(evidence_pack.chunks)}")
    print(f"  Source Documents: {len(evidence_pack.sources)}")
    print(f"  Related Entities: {evidence_pack.related_entities}")
    print(f"  Total Confidence: {evidence_pack.total_confidence:.3f}")
    
    print_subsection("3-Stage LLM Pipeline")
    judge_output, maker_output, checker_output = llm_pipeline.process(
        query=query,
        evidence_pack=evidence_pack
    )
    
    print(f"  MAKER Stage:")
    print(f"    Answer: {maker_output.answer[:100]}...")
    print(f"    Confidence: {maker_output.confidence:.3f}")
    print(f"    Citations: {len(maker_output.citations)}")
    
    print(f"\n  CHECKER Stage:")
    print(f"    Grounded: {checker_output.is_grounded}")
    print(f"    Semantic Similarity: {checker_output.semantic_similarity:.3f}")
    print(f"    Unsupported Claims: {checker_output.has_unsupported_claims}")
    print(f"    Issues: {checker_output.issues if checker_output.issues else 'None'}")
    
    print(f"\n  JUDGE Stage:")
    print(f"    Approved: {judge_output.approved}")
    print(f"    Confidence: {judge_output.confidence:.3f}")
    print(f"    Reason: {judge_output.reason}")
    if judge_output.final_answer:
        print(f"    Final Answer: {judge_output.final_answer[:100]}...")

def demo_guardrails():
    print_section("6. GUARDRAILS (Pre & Post-Generation)")
    
    guardrails = Guardrails()
    
    print_subsection("Pre-Generation Checks")
    
    safe_query = "What are the operational efficiency improvements?"
    unsafe_query = "What is the credit card number for this account?"
    
    safe_result = guardrails.pre_generation_check(safe_query)
    unsafe_result = guardrails.pre_generation_check(unsafe_query)
    
    print(f"  Safe Query: '{safe_query}'")
    print(f"    Passed: {safe_result.passed}")
    print(f"    PII Score: {safe_result.pii_score:.3f}")
    
    print(f"\n  Unsafe Query: '{unsafe_query}'")
    print(f"    Passed: {unsafe_result.passed}")
    print(f"    Flags: {unsafe_result.flags}")
    
    print_subsection("Post-Generation Checks")
    
    clean_answer = "Based on the evidence, the strategic initiative focuses on market expansion."
    pii_answer = "The customer email is john.doe@company.com and phone is +91-9876543210."
    
    clean_result = guardrails.post_generation_check(clean_answer)
    pii_result = guardrails.post_generation_check(pii_answer)
    
    print(f"  Clean Answer: '{clean_answer}'")
    print(f"    Passed: {clean_result.passed}")
    print(f"    PII Score: {clean_result.pii_score:.3f}")
    
    print(f"\n  PII-Containing Answer: '{pii_answer}'")
    print(f"    Passed: {pii_result.passed}")
    print(f"    Flags: {pii_result.flags}")
    print(f"    Sanitized: {guardrails.sanitize_response(pii_answer)}")

def demo_audit_logs(ingestion_service):
    print_section("7. AUDIT LOGGING & GOVERNANCE")
    
    print_subsection("Audit Log Summary")
    
    all_logs = ingestion_service.staging_pipeline.get_audit_logs()
    print(f"  Total Audit Entries: {len(all_logs)}")
    
    if all_logs:
        print(f"\n  Sample Audit Entry:")
        log = all_logs[0]
        print(f"    Document ID: {log.document_id}")
        print(f"    Approval Status: {log.approval_status}")
        print(f"    Redactions Applied: {len(log.redactions_applied)}")
        print(f"    Timestamp: {log.timestamp}")
        
        if log.redactions_applied:
            print(f"\n    Redaction Details:")
            for redaction in log.redactions_applied[:2]:
                print(f"      • {redaction['pii_type']}: {redaction['original_text']}")

def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  ENTERPRISE RAG SYSTEM - COMPREHENSIVE DEMO".center(78) + "║")
    print("║" + "  Multi-Layered Architecture with Data Governance".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        demo_sharepoint_api()
        demo_staging_pipeline()
        ingestion_service = demo_ingestion_pipeline()
        demo_hybrid_retrieval(ingestion_service)
        demo_evidence_and_reasoning(ingestion_service)
        demo_guardrails()
        demo_audit_logs(ingestion_service)
        
        print_section("DEMO COMPLETE")
        print("\nThe Enterprise RAG System has been successfully demonstrated with:")
        print("  ✓ Mock SharePoint ingestion")
        print("  ✓ PII detection and redaction")
        print("  ✓ Multi-storage (vector, keyword, graph)")
        print("  ✓ Hybrid retrieval with weighted scoring")
        print("  ✓ Evidence-based reasoning with 3-stage LLM pipeline")
        print("  ✓ Pre/post-generation guardrails")
        print("  ✓ Comprehensive audit logging")
        print("\nTo start the FastAPI server, run:")
        print("  python main.py")
        print("\nThen access the API at: http://localhost:8000")
        print("API Documentation: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
