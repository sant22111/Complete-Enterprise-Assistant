from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from mock_sharepoint.api import MockSharePointAPI
from crm.mock_crm_api import MockCRMAPI
from staging.staging_pipeline import StagingPipeline
from processing.chunker import DocumentChunker
from processing.metadata_enricher import MetadataEnricher
from storage.vector_store import VectorStore
from storage.keyword_index import KeywordIndex
from storage.knowledge_graph import KnowledgeGraph
from ingestion.ingestion_registry import IngestionRegistry
from ingestion.ingestion_service import IngestionService
from ingestion.document_versioning import DocumentVersioning
from retrieval.hybrid_retriever import HybridRetriever
from reasoning.evidence_builder import EvidencePackBuilder
from reasoning.llm_pipeline import LLMPipeline
from reasoning.grok_llm import GrokLLMPipeline
from reasoning.openai_llm import OpenAILLMPipeline
from reasoning.consultant_llm import ConsultantLLMPipeline
from reasoning.agent import Agent
from reasoning.agent_orchestrator import AgentOrchestrator, QueryMode
from guardrails.guardrails import Guardrails
from utils.embeddings import EmbeddingService
from config import storage_config

app = FastAPI(
    title="Enterprise RAG System",
    description="Multi-layered Retrieval-Augmented Generation platform with data governance",
    version="1.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

sharepoint_api = MockSharePointAPI()
crm_api = MockCRMAPI()
staging_pipeline = StagingPipeline(storage_config.audit_log_path)
vector_store = VectorStore(storage_config.chroma_db_path)
keyword_index = KeywordIndex(storage_config.whoosh_index_path)
knowledge_graph = KnowledgeGraph()
ingestion_registry = IngestionRegistry(storage_config.ingestion_registry_path)
document_versioning = DocumentVersioning()

print(f"✓ CRM API initialized with {len(crm_api.opportunities)} opportunities")

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

hybrid_retriever = HybridRetriever(
    vector_store=vector_store,
    keyword_index=keyword_index,
    knowledge_graph=knowledge_graph
)

evidence_builder = EvidencePackBuilder()
llm_pipeline = LLMPipeline()
guardrails = Guardrails()
embedding_service = EmbeddingService()

# Initialize OpenAI LLM pipeline (GPT-4 Turbo - better reasoning than Grok)
OPENAI_API_KEY = os.getenv('OPEN_AI_KEY')
GROK_API_KEY = os.getenv('GROK_API_KEY')

if OPENAI_API_KEY:
    grok_pipeline = OpenAILLMPipeline(api_key=OPENAI_API_KEY, similarity_threshold=0.6)
    consultant_pipeline = ConsultantLLMPipeline(api_key=OPENAI_API_KEY, similarity_threshold=0.6)
    print("✓ Using OpenAI GPT-4 Turbo (128K context)")
    # Agent also uses OpenAI
    agent_api_key = OPENAI_API_KEY
    agent_input_cost = 5.00  # GPT-4 Turbo pricing
    agent_output_cost = 15.00
elif GROK_API_KEY:
    grok_pipeline = GrokLLMPipeline(api_key=GROK_API_KEY, similarity_threshold=0.6)
    consultant_pipeline = GrokLLMPipeline(api_key=GROK_API_KEY, similarity_threshold=0.6)  # Fallback
    print("✓ Using Grok LLM (fallback)")
    agent_api_key = GROK_API_KEY
    agent_input_cost = 2.00  # Grok pricing
    agent_output_cost = 6.00
else:
    raise ValueError("Either OPEN_AI_KEY or GROK_API_KEY must be set in .env file")

# Initialize Agent for agentic reasoning
agent = Agent(
    api_key=agent_api_key,
    hybrid_retriever=hybrid_retriever,
    vector_store=vector_store,
    knowledge_graph=knowledge_graph,
    embedding_service=embedding_service,
    max_iterations=5,
    input_cost_per_1m=agent_input_cost,
    output_cost_per_1m=agent_output_cost
)

# Initialize Agent Orchestrator (manages RAG vs Agentic modes)
agent_orchestrator = AgentOrchestrator(
    grok_pipeline=grok_pipeline,
    agent=agent,
    complexity_threshold=0.6
)

@app.on_event("startup")
async def startup_event():
    """Generate sample documents and ingest on server startup."""
    try:
        # Check if sample documents exist
        sample_dir = "sample_documents"
        if not os.path.exists(sample_dir) or len(os.listdir(sample_dir)) == 0:
            print("\n📄 No sample documents found. Generating 100 documents...")
            print("=" * 80)
            
            # Import and run document generator
            # NOTE: This may fail on cloud platforms like Render - that's OK, docs are in repo
            try:
                import subprocess
                result = subprocess.run(
                    ["python", "generate_sample_docs.py"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print(result.stdout)
                    print("✓ Sample documents generated successfully!")
                else:
                    print(f"⚠️ Document generation skipped (cloud deployment)")
                    print(f"   Sample documents should already be in repo")
            except Exception as gen_error:
                print(f"⚠️ Document generation skipped: {gen_error}")
                print(f"   Sample documents should already be in repo")
        else:
            doc_count = len([f for f in os.listdir(sample_dir) if f.endswith(('.txt', '.pdf', '.ppt', '.pptx', '.doc', '.docx'))])
            print(f"\n✓ Found {doc_count} existing documents in sample_documents/")
        
        # Check if documents need ingestion
        registry_stats = ingestion_service.ingestion_registry.get_ingestion_stats()
        existing_docs = registry_stats.get('total_documents', 0)
        
        if existing_docs > 0:
            print(f"\n✓ Loaded {existing_docs} documents from storage")
        else:
            print(f"\n⚠️  No documents ingested yet - starting auto-ingestion...")
            print(f"=" * 80)
            
            # Auto-ingest all documents on startup
            try:
                results = ingestion_service.ingest_all_documents(auto_approve=True)
                print(f"\n✅ Auto-ingestion complete!")
                print(f"   Successfully ingested: {results.get('successfully_ingested', 0)} documents")
                print(f"   Total chunks: {results.get('total_chunks', 0)}")
            except Exception as e:
                print(f"\n❌ Auto-ingestion failed: {e}")
                print(f"   You can manually trigger via: POST /ingest")
    except Exception as e:
        print(f"\n⚠ Startup failed: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Save storage to disk on shutdown."""
    try:
        vector_store.save_to_disk()
        keyword_index.save_to_disk()
        knowledge_graph.save_to_disk()
        print("\n✓ Storage saved to disk")
    except Exception as e:
        print(f"\n⚠ Failed to save storage: {str(e)}")

class IngestRequest(BaseModel):
    auto_approve: bool = True

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    client_filter: Optional[str] = None
    sensitivity_filter: Optional[str] = None

class ApprovalRequest(BaseModel):
    document_id: str
    approve: bool

@app.post("/ingest")
async def ingest_documents(request: IngestRequest):
    """
    Ingest all documents from mock SharePoint.
    Runs full pipeline: staging → processing → multi-storage.
    """
    try:
        results = ingestion_service.ingest_all_documents(
            auto_approve=request.auto_approve
        )
        
        try:
            stats = ingestion_service.get_ingestion_stats()
            storage_stats = {
                "vector_chunks": stats['vector_store_stats']['total_chunks'],
                "keyword_chunks": stats['keyword_index_stats']['total_chunks'],
                "graph_entities": stats['knowledge_graph_stats']['total_entities']
            }
        except:
            storage_stats = {"vector_chunks": 0, "keyword_chunks": 0, "graph_entities": 0}
        
        return {
            "status": "success",
            "ingestion_results": results,
            "storage_stats": storage_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/single/{document_id}")
async def ingest_single_document(document_id: str):
    """
    Ingest a single specific document by ID.
    Useful for testing and debugging.
    """
    try:
        print(f"\n📄 INGESTING SINGLE DOCUMENT: {document_id}")
        print("=" * 80)
        
        # Ingest the document
        result = ingestion_service.ingest_document(
            document_id=document_id,
            auto_approve=True
        )
        
        # Save storage immediately
        print("\nSaving to disk...")
        vector_store.save_to_disk()
        keyword_index.save_to_disk()
        knowledge_graph.save_to_disk()
        print("✓ Storage saved")
        
        # Get updated stats
        stats = ingestion_service.get_ingestion_stats()
        
        return {
            "status": "success",
            "document_id": document_id,
            "result": result,
            "storage_stats": {
                "vector_chunks": stats['vector_store_stats']['total_chunks'],
                "keyword_chunks": stats['keyword_index_stats']['total_chunks'],
                "kg_chunks": stats['knowledge_graph_stats']['total_chunks_indexed'],
                "total_documents": stats['total_documents']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/batch")
async def ingest_batch(start: int = 0, count: int = 20):
    """
    Ingest documents sequentially in batches to avoid memory issues.
    
    Args:
        start: Starting document index
        count: Number of documents to ingest (default 20)
    """
    try:
        print(f"\n📦 BATCH INGESTION: Documents {start} to {start + count - 1}")
        print("=" * 80)
        
        # Get all documents
        all_docs = ingestion_service.sharepoint_api.list_documents()
        batch_docs = all_docs[start:start + count]
        
        if not batch_docs:
            return {
                "status": "error",
                "message": f"No documents found at index {start}",
                "total_documents": len(all_docs)
            }
        
        # Ingest sequentially
        results = []
        for i, doc in enumerate(batch_docs, 1):
            doc_id = doc['document_id']
            print(f"  [{i}/{len(batch_docs)}] Ingesting {doc_id}...", end=" ")
            
            try:
                result = ingestion_service.ingest_document(
                    document_id=doc_id,
                    auto_approve=True
                )
                chunks = result.get('chunk_count', 0)
                print(f"✓ ({chunks} chunks)")
                results.append({"doc_id": doc_id, "chunks": chunks, "success": True})
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
                results.append({"doc_id": doc_id, "error": str(e), "success": False})
        
        # Save storage
        print("\nSaving to disk...")
        vector_store.save_to_disk()
        keyword_index.save_to_disk()
        knowledge_graph.save_to_disk()
        print("✓ Storage saved")
        
        # Get stats
        stats = ingestion_service.get_ingestion_stats()
        
        return {
            "status": "success",
            "batch_range": f"{start}-{start + count - 1}",
            "total_in_batch": len(batch_docs),
            "successful": sum(1 for r in results if r.get('success')),
            "failed": sum(1 for r in results if not r.get('success')),
            "results": results,
            "storage_stats": {
                "total_chunks": stats['vector_store_stats']['total_chunks'],
                "total_documents": stats['total_documents']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/retry-failed")
async def retry_failed_documents():
    """
    Retry ingestion for only failed or missing documents.
    Does NOT clear existing successfully ingested documents.
    """
    try:
        print("\n🔄 RETRYING FAILED DOCUMENTS")
        print("=" * 80)
        
        results = ingestion_service.ingest_failed_documents(auto_approve=True)
        
        # Get updated stats
        stats = ingestion_service.get_ingestion_stats()
        storage_stats = {
            "vector_chunks": stats['vector_store_stats']['total_chunks'],
            "keyword_chunks": stats['keyword_index_stats']['total_chunks'],
            "graph_entities": stats['knowledge_graph_stats']['total_entities']
        }
        
        print(f"✓ Retry complete: {results['successfully_ingested']}/{results['total_documents']} documents ingested")
        print("=" * 80)
        
        return {
            "status": "success",
            "message": f"Retried {results['total_documents']} failed/missing documents",
            "ingestion_results": results,
            "storage_stats": storage_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/reingest")
async def reingest_all():
    """
    Clear all storage systems and re-ingest all documents.
    Perfect for demos - shows the full pipeline in action!
    """
    try:
        print("\n🔄 RE-INGESTION STARTED")
        print("=" * 80)
        
        # Clear all storage systems
        print("Clearing Vector Store...")
        vector_store.chunks_store.clear()
        vector_store.embeddings_store.clear()
        
        print("Clearing Keyword Index...")
        keyword_index.clear_index()
        
        print("Clearing Knowledge Graph...")
        knowledge_graph.clear_graph()
        
        print("Clearing Ingestion Registry...")
        ingestion_service.ingestion_registry.records.clear()
        
        print("✓ All storage systems cleared")
        print()
        
        # Re-ingest all documents
        print("📥 Starting re-ingestion...")
        results = ingestion_service.ingest_all_documents(auto_approve=True)
        
        # Get updated stats
        stats = ingestion_service.get_ingestion_stats()
        storage_stats = {
            "vector_chunks": stats['vector_store_stats']['total_chunks'],
            "keyword_chunks": stats['keyword_index_stats']['total_chunks'],
            "graph_entities": stats['knowledge_graph_stats']['total_entities']
        }
        
        print(f"✓ Re-ingestion complete: {results['successfully_ingested']} documents, {results['total_chunks']} chunks")
        print("=" * 80)
        
        return {
            "status": "success",
            "message": "Re-ingestion completed successfully",
            "ingestion_results": results,
            "storage_stats": storage_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"⚠️ Re-ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/generate-report")
async def generate_ingestion_report():
    """
    Generate a detailed ingestion report.
    """
    try:
        from reports.ingestion_report_generator import IngestionReportGenerator
        
        # Get current stats
        stats = ingestion_service.get_ingestion_stats()
        audit_logs = staging_pipeline.get_audit_logs()
        
        storage_stats = {
            "vector_store": stats['vector_store_stats'],
            "keyword_index": stats['keyword_index_stats'],
            "knowledge_graph": stats['knowledge_graph_stats']
        }
        
        ingestion_results = {
            "successfully_ingested": stats['successfully_ingested'],
            "total_chunks": stats['total_chunks']
        }
        
        # Generate report
        report_gen = IngestionReportGenerator()
        report_file = report_gen.generate_report(
            ingestion_results=ingestion_results,
            audit_logs=audit_logs,
            storage_stats=storage_stats
        )
        
        return {
            "status": "success",
            "message": "Report generated successfully",
            "report_file": report_file,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/delta")
async def ingest_delta(since: Optional[str] = None):
    """
    Ingest only changed documents since last sync.
    Supports delta ingestion for efficiency.
    """
    try:
        results = ingestion_service.ingest_delta(since)
        
        return {
            "status": "success",
            "delta_results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_knowledge_base(request: QueryRequest):
    """
    Query the knowledge base with hybrid retrieval.
    Returns: answer, sources, confidence, evidence, debug info.
    """
    try:
        pre_guard = guardrails.pre_generation_check(request.query)
        if not pre_guard.passed:
            return {
                "status": "blocked",
                "reason": "Query blocked by guardrails",
                "guardrail_flags": pre_guard.flags,
                "timestamp": datetime.now().isoformat()
            }
        
        metadata_filter = None
        if request.client_filter or request.sensitivity_filter:
            metadata_filter = {}
            if request.client_filter:
                metadata_filter["client"] = request.client_filter
            if request.sensitivity_filter:
                metadata_filter["sensitivity_level"] = request.sensitivity_filter
        
        query_embedding = embedding_service.embed_query(request.query)
        
        retrieved_chunks, debug_info = hybrid_retriever.retrieve(
            query=request.query,
            query_embedding=query_embedding,
            top_k=request.top_k,
            metadata_filter=metadata_filter
        )
        
        evidence_pack = evidence_builder.build_evidence_pack(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            debug_info=debug_info
        )
        
        # Use Grok LLM pipeline for answer generation
        judge_output, maker_output, checker_output = grok_pipeline.process(
            query=request.query,
            evidence_pack=evidence_pack
        )
        
        if not judge_output.approved:
            return {
                "status": "insufficient_evidence",
                "message": judge_output.reason,
                "confidence": judge_output.confidence,
                "evidence_summary": evidence_builder.get_evidence_summary(evidence_pack),
                "debug_info": debug_info,
                "timestamp": datetime.now().isoformat()
            }
        
        post_guard = guardrails.post_generation_check(judge_output.final_answer)
        if not post_guard.passed:
            sanitized_answer = guardrails.sanitize_response(judge_output.final_answer)
            return {
                "status": "success_with_sanitization",
                "answer": sanitized_answer,
                "original_flags": post_guard.flags,
                "sources": evidence_pack.sources,
                "confidence": judge_output.confidence,
                "evidence": evidence_builder.get_evidence_summary(evidence_pack),
                "retrieval_debug_info": debug_info,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "answer": judge_output.final_answer,
            "sources": evidence_pack.sources,
            "confidence": judge_output.confidence,
            "evidence": evidence_builder.get_evidence_summary(evidence_pack),
            "retrieval_debug_info": debug_info,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/consultant")
async def query_consultant(request: QueryRequest):
    """
    Query using consultant mode - strategic recommendations and analysis.
    Acts like a management consultant providing insights and recommendations.
    """
    try:
        pre_guard = guardrails.pre_generation_check(request.query)
        if not pre_guard.passed:
            return {
                "status": "blocked",
                "reason": "Query blocked by guardrails",
                "guardrail_flags": pre_guard.flags,
                "timestamp": datetime.now().isoformat()
            }
        
        metadata_filter = None
        if request.client_filter or request.sensitivity_filter:
            metadata_filter = {}
            if request.client_filter:
                metadata_filter["client"] = request.client_filter
            if request.sensitivity_filter:
                metadata_filter["sensitivity_level"] = request.sensitivity_filter
        
        query_embedding = embedding_service.embed_query(request.query)
        
        retrieved_chunks, debug_info = hybrid_retriever.retrieve(
            query=request.query,
            query_embedding=query_embedding,
            top_k=request.top_k,
            metadata_filter=metadata_filter
        )
        
        evidence_pack = evidence_builder.build_evidence_pack(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            debug_info=debug_info
        )
        
        # Use Consultant LLM pipeline for strategic recommendations
        judge_output, maker_output, checker_output = consultant_pipeline.process(
            query=request.query,
            evidence_pack=evidence_pack
        )
        
        token_usage = consultant_pipeline.get_token_usage()
        
        post_guard = guardrails.post_generation_check(judge_output.final_answer)
        if not post_guard.passed:
            sanitized_answer = guardrails.sanitize_response(judge_output.final_answer)
            return {
                "status": "success_with_sanitization",
                "mode": "CONSULTANT",
                "answer": sanitized_answer,
                "original_flags": post_guard.flags,
                "sources": evidence_pack.sources,
                "confidence": judge_output.confidence,
                "input_tokens": token_usage["input_tokens"],
                "output_tokens": token_usage["output_tokens"],
                "total_tokens": token_usage["total_tokens"],
                "cost_estimate": token_usage["total_cost"],
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "mode": "CONSULTANT",
            "answer": judge_output.final_answer,
            "sources": evidence_pack.sources,
            "confidence": judge_output.confidence,
            "input_tokens": token_usage["input_tokens"],
            "output_tokens": token_usage["output_tokens"],
            "total_tokens": token_usage["total_tokens"],
            "cost_estimate": token_usage["total_cost"],
            "api_calls": 1,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/agentic")
async def query_agentic(request: QueryRequest):
    """
    Query using agentic reasoning (powerful, more expensive).
    Agent breaks down complex queries into steps and reasons through them.
    """
    try:
        pre_guard = guardrails.pre_generation_check(request.query)
        if not pre_guard.passed:
            return {
                "status": "blocked",
                "reason": "Query blocked by guardrails",
                "guardrail_flags": pre_guard.flags,
                "timestamp": datetime.now().isoformat()
            }
        
        metadata_filter = None
        if request.client_filter or request.sensitivity_filter:
            metadata_filter = {}
            if request.client_filter:
                metadata_filter["client"] = request.client_filter
            if request.sensitivity_filter:
                metadata_filter["sensitivity_level"] = request.sensitivity_filter
        
        query_embedding = embedding_service.embed_query(request.query)
        
        retrieved_chunks, debug_info = hybrid_retriever.retrieve(
            query=request.query,
            query_embedding=query_embedding,
            top_k=request.top_k,
            metadata_filter=metadata_filter
        )
        
        evidence_pack = evidence_builder.build_evidence_pack(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            debug_info=debug_info
        )
        
        # Use agentic reasoning
        orchestrator_response = agent_orchestrator.process_query(
            query=request.query,
            evidence_pack=evidence_pack,
            mode=QueryMode.AGENTIC
        )
        
        post_guard = guardrails.post_generation_check(orchestrator_response.answer)
        
        if not post_guard.passed:
            sanitized_answer = guardrails.sanitize_response(orchestrator_response.answer)
            return {
                "status": "success_with_sanitization",
                "mode": "AGENTIC",
                "answer": sanitized_answer,
                "original_flags": post_guard.flags,
                "sources": orchestrator_response.sources,
                "confidence": orchestrator_response.confidence,
                "api_calls": orchestrator_response.api_calls,
                "cost_estimate": orchestrator_response.cost_estimate,
                "reasoning_steps": orchestrator_response.reasoning_steps,
                "retrieval_debug_info": debug_info,
                "input_tokens": orchestrator_response.input_tokens,
                "output_tokens": orchestrator_response.output_tokens,
                "total_tokens": orchestrator_response.total_tokens,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "mode": "AGENTIC",
            "answer": orchestrator_response.answer,
            "sources": orchestrator_response.sources,
            "confidence": orchestrator_response.confidence,
            "api_calls": orchestrator_response.api_calls,
            "cost_estimate": orchestrator_response.cost_estimate,
            "input_tokens": orchestrator_response.input_tokens,
            "output_tokens": orchestrator_response.output_tokens,
            "total_tokens": orchestrator_response.total_tokens,
            "reasoning_steps": orchestrator_response.reasoning_steps,
            "retrieval_debug_info": debug_info,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/auto")
async def query_auto(request: QueryRequest):
    """
    Query with automatic mode selection (RAG or AGENTIC).
    System analyzes query complexity and chooses the best mode.
    """
    try:
        pre_guard = guardrails.pre_generation_check(request.query)
        if not pre_guard.passed:
            return {
                "status": "blocked",
                "reason": "Query blocked by guardrails",
                "guardrail_flags": pre_guard.flags,
                "timestamp": datetime.now().isoformat()
            }
        
        metadata_filter = None
        if request.client_filter or request.sensitivity_filter:
            metadata_filter = {}
            if request.client_filter:
                metadata_filter["client"] = request.client_filter
            if request.sensitivity_filter:
                metadata_filter["sensitivity_level"] = request.sensitivity_filter
        
        query_embedding = embedding_service.embed_query(request.query)
        
        retrieved_chunks, debug_info = hybrid_retriever.retrieve(
            query=request.query,
            query_embedding=query_embedding,
            top_k=request.top_k,
            metadata_filter=metadata_filter
        )
        
        evidence_pack = evidence_builder.build_evidence_pack(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            debug_info=debug_info
        )
        
        # Get cost comparison
        cost_comparison = agent_orchestrator.get_cost_comparison(request.query, evidence_pack)
        
        # Use AUTO mode (system decides)
        orchestrator_response = agent_orchestrator.process_query(
            query=request.query,
            evidence_pack=evidence_pack,
            mode=QueryMode.AUTO
        )
        
        post_guard = guardrails.post_generation_check(orchestrator_response.answer)
        
        if not post_guard.passed:
            sanitized_answer = guardrails.sanitize_response(orchestrator_response.answer)
            return {
                "status": "success_with_sanitization",
                "mode": orchestrator_response.mode_used,
                "answer": sanitized_answer,
                "original_flags": post_guard.flags,
                "sources": orchestrator_response.sources,
                "confidence": orchestrator_response.confidence,
                "api_calls": orchestrator_response.api_calls,
                "cost_estimate": orchestrator_response.cost_estimate,
                "cost_comparison": cost_comparison,
                "reasoning_steps": orchestrator_response.reasoning_steps,
                "retrieval_debug_info": debug_info,
                "input_tokens": orchestrator_response.input_tokens,
                "output_tokens": orchestrator_response.output_tokens,
                "total_tokens": orchestrator_response.total_tokens,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "mode": orchestrator_response.mode_used,
            "answer": orchestrator_response.answer,
            "sources": orchestrator_response.sources,
            "confidence": orchestrator_response.confidence,
            "api_calls": orchestrator_response.api_calls,
            "cost_estimate": orchestrator_response.cost_estimate,
            "cost_comparison": cost_comparison,
            "reasoning_steps": orchestrator_response.reasoning_steps,
            "retrieval_debug_info": debug_info,
            "input_tokens": orchestrator_response.input_tokens,
            "output_tokens": orchestrator_response.output_tokens,
            "total_tokens": orchestrator_response.total_tokens,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/ingestion")
async def get_ingestion_logs():
    """
    Get ingestion logs and statistics.
    Shows: documents ingested, chunks created, registry status.
    """
    try:
        stats = ingestion_service.get_ingestion_stats()
        
        return {
            "status": "success",
            "ingestion_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/audit")
async def get_audit_logs(document_id: Optional[str] = None):
    """
    Get redaction audit logs.
    Shows: original text, redacted text, redactions applied, approval status.
    """
    try:
        audit_logs = staging_pipeline.get_audit_logs(document_id)
        
        formatted_logs = []
        for log in audit_logs:
            formatted_logs.append({
                "document_id": log.document_id,
                "timestamp": log.timestamp,
                "approval_status": log.approval_status,
                "redactions_count": len(log.redactions_applied),
                "redactions_applied": log.redactions_applied,
                "approved_by": log.approved_by,
                "approval_timestamp": log.approval_timestamp
            })
        
        return {
            "status": "success",
            "audit_logs": formatted_logs,
            "total_logs": len(formatted_logs),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/debug/approve-document")
async def approve_document(request: ApprovalRequest):
    """
    Approve or reject a staged document for downstream processing.
    """
    try:
        if request.approve:
            success = staging_pipeline.approve_document(request.document_id)
            action = "approved"
        else:
            success = staging_pipeline.reject_document(request.document_id)
            action = "rejected"
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found")
        
        return {
            "status": "success",
            "document_id": request.document_id,
            "action": action,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/storage-stats")
async def get_storage_stats():
    """
    Get statistics for all storage systems.
    Shows: vector store, keyword index, knowledge graph status.
    """
    try:
        stats = {
            "vector_store": vector_store.get_stats(),
            "keyword_index": keyword_index.get_stats(),
            "knowledge_graph": knowledge_graph.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "storage_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/versions/{document_id}")
async def get_document_versions(document_id: str):
    """Get complete version history for a document."""
    try:
        history = document_versioning.get_document_history(document_id)
        if not history:
            raise HTTPException(status_code=404, detail=f"No versions found for {document_id}")
        
        return {
            "status": "success",
            "document_id": document_id,
            "total_versions": len(history),
            "versions": [
                {
                    "version": v.version_number,
                    "timestamp": v.timestamp,
                    "hash": v.file_hash[:16] + "...",
                    "change_type": v.change_type,
                    "chunk_count": v.chunk_count,
                    "chunks_added": v.chunks_added,
                    "chunks_deleted": v.chunks_deleted,
                    "status": v.status
                }
                for v in history
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/all-versions")
async def get_all_versions():
    """Get version history for all documents."""
    try:
        all_versions = document_versioning.get_all_versions()
        
        summary = {}
        for doc_id, versions in all_versions.items():
            summary[doc_id] = {
                "total_versions": len(versions),
                "latest_version": versions[-1].version_number if versions else 0,
                "latest_hash": versions[-1].file_hash[:16] + "..." if versions else None,
                "latest_timestamp": versions[-1].timestamp if versions else None,
                "change_type": versions[-1].change_type if versions else None
            }
        
        return {
            "status": "success",
            "total_documents": len(summary),
            "documents": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/crm")
async def get_crm_data():
    """Get CRM opportunities data."""
    try:
        stats = crm_api.get_stats()
        opportunities = crm_api.list_all_opportunities()
        
        return {
            "status": "success",
            "stats": stats,
            "opportunities": opportunities[:10]  # Return first 10 for preview
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/crm/client/{client_name}")
async def get_crm_by_client(client_name: str):
    """Get CRM opportunities for a specific client."""
    try:
        opportunities = crm_api.search_by_client(client_name)
        return {
            "status": "success",
            "client": client_name,
            "opportunities": opportunities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/download-report")
async def download_latest_report():
    """Download the latest ingestion report as a text file."""
    try:
        reports_dir = "./reports"
        if not os.path.exists(reports_dir):
            raise HTTPException(status_code=404, detail="No reports directory found")
        
        # Get all report files
        report_files = [f for f in os.listdir(reports_dir) if f.startswith("ingestion_report_") and f.endswith(".txt")]
        
        if not report_files:
            raise HTTPException(status_code=404, detail="No ingestion reports found")
        
        # Sort by filename (contains timestamp) and get the latest
        latest_report = sorted(report_files)[-1]
        report_path = os.path.join(reports_dir, latest_report)
        
        return FileResponse(
            path=report_path,
            media_type="text/plain",
            filename=latest_report
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "system": "Enterprise RAG Platform",
        "version": "1.0.0",
        "description": "Multi-layered Retrieval-Augmented Generation with data governance",
        "endpoints": {
            "ingest": "POST /ingest - Ingest all documents from SharePoint",
            "ingest_delta": "POST /ingest/delta - Delta ingestion (changed documents only)",
            "query": "POST /query - Query knowledge base with hybrid retrieval",
            "audit_logs": "GET /debug/audit - View redaction audit logs",
            "ingestion_logs": "GET /debug/ingestion - View ingestion statistics",
            "download_report": "GET /debug/download-report - Download latest ingestion report",
            "approve_document": "POST /debug/approve-document - Approve/reject staged documents",
            "storage_stats": "GET /debug/storage-stats - View storage system statistics",
            "health": "GET /health - Health check"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
