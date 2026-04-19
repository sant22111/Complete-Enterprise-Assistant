#!/usr/bin/env python3
"""
Quick-start script for Enterprise RAG System.
Demonstrates full pipeline: ingestion → retrieval → reasoning → guardrails.
"""

import sys
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

def main():
    print("\n" + "="*80)
    print("  ENTERPRISE RAG SYSTEM - QUICK START")
    print("="*80 + "\n")
    
    try:
        print("[1/5] Initializing components...")
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
        
        print("✓ Components initialized\n")
        
        print("[2/5] Ingesting documents from mock SharePoint...")
        results = ingestion_service.ingest_all_documents(auto_approve=True)
        print(f"✓ Ingested {results['successfully_ingested']} documents, {results['total_chunks']} chunks\n")
        
        print("[3/5] Setting up retrieval and reasoning...")
        hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            keyword_index=keyword_index,
            knowledge_graph=knowledge_graph
        )
        evidence_builder = EvidencePackBuilder()
        llm_pipeline = LLMPipeline()
        guardrails = Guardrails()
        embedding_service = EmbeddingService()
        print("✓ Retrieval and reasoning ready\n")
        
        print("[4/5] Running sample queries...\n")
        
        queries = [
            "What is the strategic expansion plan?",
            "Tell me about technology initiatives",
            "What are the financial projections?"
        ]
        
        for idx, query in enumerate(queries, 1):
            print(f"Query {idx}: {query}")
            
            pre_guard = guardrails.pre_generation_check(query)
            if not pre_guard.passed:
                print(f"  ❌ Blocked by guardrails: {pre_guard.flags}\n")
                continue
            
            query_embedding = embedding_service.embed_query(query)
            retrieved_chunks, debug_info = hybrid_retriever.retrieve(
                query=query,
                query_embedding=query_embedding,
                top_k=3
            )
            
            evidence_pack = evidence_builder.build_evidence_pack(
                query=query,
                retrieved_chunks=retrieved_chunks,
                debug_info=debug_info
            )
            
            judge_output, maker_output, checker_output = llm_pipeline.process(
                query=query,
                evidence_pack=evidence_pack
            )
            
            if judge_output.approved:
                post_guard = guardrails.post_generation_check(judge_output.final_answer)
                if post_guard.passed:
                    print(f"  ✓ Answer: {judge_output.final_answer[:80]}...")
                    print(f"  ✓ Confidence: {judge_output.confidence:.2f}")
                    print(f"  ✓ Sources: {len(evidence_pack.sources)} document(s)")
                else:
                    sanitized = guardrails.sanitize_response(judge_output.final_answer)
                    print(f"  ⚠ Sanitized: {sanitized[:80]}...")
            else:
                print(f"  ⚠ Insufficient evidence: {judge_output.reason}")
            
            print()
        
        print("[5/5] System statistics...\n")
        stats = ingestion_service.get_ingestion_stats()
        print(f"Vector Store: {stats['vector_store_stats']['total_chunks']} chunks")
        print(f"Keyword Index: {stats['keyword_index_stats']['total_chunks']} chunks")
        print(f"Knowledge Graph: {stats['knowledge_graph_stats']['total_entities']} entities")
        print(f"Audit Logs: {len(staging_pipeline.get_audit_logs())} entries\n")
        
        print("="*80)
        print("✓ SYSTEM READY FOR PRODUCTION")
        print("="*80)
        print("\nTo start the FastAPI server:")
        print("  python main.py")
        print("\nAPI Documentation:")
        print("  http://localhost:8000/docs")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
