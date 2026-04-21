from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
from mock_sharepoint.api import MockSharePointAPI
from staging.staging_pipeline import StagingPipeline
from processing.chunker import DocumentChunker
from processing.metadata_enricher import MetadataEnricher
from storage.vector_store import VectorStore
from storage.keyword_index import KeywordIndex
from storage.knowledge_graph import KnowledgeGraph
from ingestion.ingestion_registry import IngestionRegistry
from ingestion.document_versioning import DocumentVersioning
from ingestion.metadata_enricher import MetadataEnricher as CRMMetadataEnricher
from reports.ingestion_report_generator import IngestionReportGenerator
from utils.embeddings import EmbeddingService
from concurrent.futures import ThreadPoolExecutor, as_completed

class IngestionService:
    """
    Orchestrates full ingestion pipeline from SharePoint to multi-storage.
    
    Pipeline:
    1. Fetch from mock SharePoint
    2. Staging (text extraction, PII redaction, audit logging)
    3. Document processing (chunking)
    4. Metadata enrichment
    5. Multi-storage (vector, keyword, graph)
    6. Registry update
    """
    
    def __init__(
        self,
        sharepoint_api: MockSharePointAPI,
        staging_pipeline: StagingPipeline,
        vector_store: VectorStore,
        keyword_index: KeywordIndex,
        knowledge_graph: KnowledgeGraph,
        ingestion_registry: IngestionRegistry,
        crm_api=None,
        document_versioning: DocumentVersioning = None
    ):
        self.sharepoint_api = sharepoint_api
        self.staging_pipeline = staging_pipeline
        self.vector_store = vector_store
        self.keyword_index = keyword_index
        self.knowledge_graph = knowledge_graph
        self.ingestion_registry = ingestion_registry
        self.crm_api = crm_api
        self.document_versioning = document_versioning or DocumentVersioning()
        self.chunker = DocumentChunker()
        self.metadata_enricher = MetadataEnricher()
        self.crm_metadata_enricher = CRMMetadataEnricher(crm_api) if crm_api else None
        self.embedding_service = EmbeddingService()
        self.report_generator = IngestionReportGenerator()
    
    def ingest_all_documents(self, auto_approve: bool = True, generate_report: bool = True) -> Dict:
        """Ingest all documents from SharePoint with parallel processing."""
        start_time = time.time()
        
        documents = self.sharepoint_api.list_documents()
        total_docs = len(documents)
        
        print(f"📥 Starting re-ingestion...")
        
        ingestion_results = {
            "total_documents": total_docs,
            "successfully_ingested": 0,
            "failed_ingestions": 0,
            "total_chunks": 0,
            "ingested_documents": [],
            "failed_documents": [],
            "enriched_metadata": []
        }
        
        # Process documents in parallel (4 workers)
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all tasks
            future_to_doc = {
                executor.submit(self.ingest_document, doc["document_id"], auto_approve): (idx, doc["document_id"])
                for idx, doc in enumerate(documents, 1)
            }
            
            # Process results as they complete
            for future in as_completed(future_to_doc):
                idx, doc_id = future_to_doc[future]
                print(f"Processing {idx}/{total_docs}: {doc_id}... ", end="", flush=True)
                
                try:
                    result = future.result()
                    
                    if result["success"]:
                        print(f"✓ ({result['chunk_count']} chunks)")
                        ingestion_results["successfully_ingested"] += 1
                        ingestion_results["total_chunks"] += result["chunk_count"]
                        ingestion_results["ingested_documents"].append({
                            "document_id": doc_id,
                            "chunk_count": result["chunk_count"]
                        })
                        if result.get("enriched_metadata"):
                            ingestion_results["enriched_metadata"].append(result["enriched_metadata"])
                    else:
                        print(f"✗ ({result['error']})")
                        ingestion_results["failed_ingestions"] += 1
                        ingestion_results["failed_documents"].append({
                            "document_id": doc_id,
                            "error": result["error"]
                        })
                except Exception as e:
                    print(f"✗ (Exception: {str(e)})")
                    ingestion_results["failed_ingestions"] += 1
                    ingestion_results["failed_documents"].append({
                        "document_id": doc_id,
                        "error": str(e)
                    })
        
        # Auto-save storage to disk after ingestion
        try:
            self.vector_store.save_to_disk()
            self.keyword_index.save_to_disk()
            self.knowledge_graph.save_to_disk()
        except Exception as e:
            print(f"⚠️ Warning: Failed to save storage to disk: {str(e)}")
        
        # Calculate processing time
        end_time = time.time()
        ingestion_results["processing_time_seconds"] = end_time - start_time
        
        # Generate report if requested
        if generate_report:
            try:
                audit_logs = self.staging_pipeline.get_audit_logs()
                storage_stats = {
                    "vector_store": self.vector_store.get_stats(),
                    "keyword_index": self.keyword_index.get_stats(),
                    "knowledge_graph": self.knowledge_graph.get_stats()
                }
                
                # Calculate CRM matching stats
                crm_stats = None
                if self.crm_metadata_enricher and ingestion_results["enriched_metadata"]:
                    matched_count = sum(1 for meta in ingestion_results["enriched_metadata"] if meta.get("crm_match"))
                    crm_stats = {
                        "total_documents": len(ingestion_results["enriched_metadata"]),
                        "matched_documents": matched_count,
                        "match_rate": (matched_count / len(ingestion_results["enriched_metadata"]) * 100) if ingestion_results["enriched_metadata"] else 0
                    }
                
                report_generator = IngestionReportGenerator()
                report_path = report_generator.generate_report(
                    ingestion_results=ingestion_results,
                    audit_logs=audit_logs,
                    storage_stats=storage_stats,
                    crm_stats=crm_stats
                )
                print(f"📊 Ingestion report generated: {report_path}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to generate report: {str(e)}")
        
        return ingestion_results
    
    def ingest_document(self, document_id: str, auto_approve: bool = True) -> Dict:
        """
        Ingest a single document through full pipeline.
        Supports delta ingestion - only re-ingest if document changed.
        """
        try:
            doc_metadata = self.sharepoint_api.get_document_metadata(document_id)
            if not doc_metadata:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }
            
            # For PDF/PPT/Word files, use file_path; for text files, use content
            file_path = doc_metadata.get("file_path", "")
            file_ext = file_path.rsplit('.', 1)[-1].lower() if file_path else "txt"
            
            if file_ext in ['pdf', 'ppt', 'pptx', 'doc', 'docx']:
                # Binary files - use file path
                doc_content = file_path
            else:
                # Text files - download content
                doc_content = self.sharepoint_api.download_document(document_id)
                if not doc_content:
                    return {
                        "success": False,
                        "error": f"Failed to download document {document_id}"
                    }
            
            file_hash = self.sharepoint_api.compute_file_hash(str(doc_content))
            
            # Check if document already ingested with same hash (no changes)
            registry_entry = self.ingestion_registry.get_ingestion_entry(document_id)
            if registry_entry and registry_entry.get("file_hash") == file_hash:
                return {
                    "success": True,
                    "chunk_count": 0,
                    "document_id": document_id,
                    "status": "skipped_no_changes"
                }
            
            # Document changed or new - delete old chunks first
            if registry_entry:
                self._delete_document_chunks(document_id)
            
            staged_doc = self.staging_pipeline.process_document(
                document_id=document_id,
                raw_content=doc_content,
                file_format=f".{file_ext}",
                auto_approve=auto_approve
            )
            
            if staged_doc.approval_status != "approved":
                self.ingestion_registry.mark_failed(
                    document_id,
                    "Document rejected in staging"
                )
                return {
                    "success": False,
                    "error": "Document rejected in staging"
                }
            
            chunks = self.chunker.chunk_document(
                document_id=document_id,
                text=staged_doc.redacted_text,
                page_number=1
            )
            
            if not chunks:
                chunks = [type('Chunk', (), {
                    'chunk_id': f"{document_id}_chunk_0000",
                    'document_id': document_id,
                    'page_number': 1,
                    'cleaned_text': staged_doc.redacted_text,
                    'token_count': len(staged_doc.redacted_text.split()),
                    'position_in_document': 0
                })()]
            
            # Enrich SharePoint metadata with CRM data
            base_metadata = {
                "client": doc_metadata.get("client"),
                "service_line": doc_metadata.get("service_line"),
                "document_type": doc_metadata.get("document_type"),
                "year": doc_metadata.get("year"),
                "sensitivity_level": doc_metadata.get("sensitivity_level"),
                "source_file": doc_metadata.get("file_path"),
                "source_system": doc_metadata.get("source_system"),
                "ingestion_timestamp": datetime.now().isoformat(),
                "last_modified": doc_metadata.get("last_modified"),
                "page_number": 1
            }
            
            # Add CRM data if CRM API is available
            if self.crm_metadata_enricher:
                base_metadata = self.crm_metadata_enricher.enrich(
                    sharepoint_metadata=base_metadata,
                    document_text=staged_doc.redacted_text
                )
            
            enriched_chunks = self.metadata_enricher.enrich_chunks(
                [
                    {
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "page_number": c.page_number,
                        "cleaned_text": c.cleaned_text,
                        "token_count": c.token_count,
                        "position_in_document": c.position_in_document
                    }
                    for c in chunks
                ],
                base_metadata
            )
            
            # Add synthetic CRM summary chunk if CRM data exists
            if base_metadata.get('crm_id') and base_metadata.get('crm_value'):
                crm_chunk = self._create_crm_summary_chunk(document_id, base_metadata)
                enriched_chunks.append(crm_chunk)
            
            chunk_count = 0
            for i, enriched_chunk in enumerate(enriched_chunks, 1):
                try:
                    print(f"  Processing chunk {i}/{len(enriched_chunks)}: {enriched_chunk.chunk_id[:50]}...")
                    
                    # Generate embedding
                    embedding = self.embedding_service.embed_text(enriched_chunk.cleaned_text)
                    print(f"    ✓ Embedding generated")
                    
                    # Add to vector store
                    self.vector_store.add_chunk(
                        chunk_id=enriched_chunk.chunk_id,
                        document_id=enriched_chunk.document_id,
                        text=enriched_chunk.cleaned_text,
                        embedding=embedding,
                        metadata=enriched_chunk.metadata
                    )
                    print(f"    ✓ Added to vector store")
                    
                    # Add to keyword index
                    self.keyword_index.add_chunk(
                        chunk_id=enriched_chunk.chunk_id,
                        document_id=enriched_chunk.document_id,
                        text=enriched_chunk.cleaned_text,
                        metadata=enriched_chunk.metadata
                    )
                    print(f"    ✓ Added to keyword index")
                    
                    # Extract entities and relationships from metadata (KPMG structure)
                    self.knowledge_graph.extract_entities_from_metadata(
                        enriched_chunk.metadata,
                        enriched_chunk.chunk_id
                    )
                    self.knowledge_graph.extract_relationships_from_metadata(
                        enriched_chunk.metadata,
                        enriched_chunk.chunk_id
                    )
                    
                    # Also extract from text as fallback
                    self.knowledge_graph.extract_entities_from_text(
                        enriched_chunk.cleaned_text,
                        enriched_chunk.chunk_id
                    )
                    self.knowledge_graph.extract_relationships_from_text(
                        enriched_chunk.cleaned_text,
                        enriched_chunk.chunk_id
                    )
                    print(f"    ✓ Added to knowledge graph")
                    
                    chunk_count += 1
                except Exception as chunk_error:
                    print(f"    ✗ Error processing chunk {i}: {str(chunk_error)[:100]}")
                    # Continue with next chunk instead of crashing
                    continue
            
            self.ingestion_registry.register_ingestion(
                document_id=document_id,
                file_hash=file_hash,
                chunk_count=len(enriched_chunks),
                status="success"
            )
            
            # Record version change
            previous_entry = registry_entry
            self.document_versioning.record_ingestion(
                document_id=document_id,
                file_hash=file_hash,
                chunk_count=len(enriched_chunks),
                previous_hash=previous_entry.get("file_hash") if previous_entry else None,
                previous_chunk_count=previous_entry.get("chunk_count", 0) if previous_entry else 0,
                status="success"
            )
            
            return {
                "success": True,
                "chunk_count": len(enriched_chunks),
                "document_id": document_id,
                "enriched_metadata": base_metadata  # Include for CRM stats
            }
        
        except Exception as e:
            self.ingestion_registry.mark_failed(document_id, str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def ingest_failed_documents(self, auto_approve: bool = True, generate_report: bool = True) -> Dict:
        """
        Re-ingest only documents that failed in previous ingestion attempts.
        Uses the ingestion registry to identify failed documents.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        start_time = time.time()
        
        # Get all failed documents from registry
        failed_records = self.ingestion_registry.get_failed_ingestions()
        failed_doc_ids = [record.document_id for record in failed_records]
        
        # Also check for documents that exist in SharePoint but not in registry
        all_docs = self.sharepoint_api.list_documents()
        all_doc_ids = [doc["document_id"] for doc in all_docs]
        
        # Documents not in registry at all
        not_ingested = [doc_id for doc_id in all_doc_ids 
                       if not self.ingestion_registry.get_record(doc_id)]
        
        # Combine failed and not ingested
        docs_to_retry = list(set(failed_doc_ids + not_ingested))
        total_docs = len(docs_to_retry)
        
        if total_docs == 0:
            print("✓ No failed documents to retry")
            return {
                "total_documents": 0,
                "successfully_ingested": 0,
                "failed_ingestions": 0,
                "total_chunks": 0,
                "ingested_documents": [],
                "failed_documents": []
            }
        
        print(f"🔄 Retrying {total_docs} failed/missing documents...")
        
        ingestion_results = {
            "total_documents": total_docs,
            "successfully_ingested": 0,
            "failed_ingestions": 0,
            "total_chunks": 0,
            "ingested_documents": [],
            "failed_documents": [],
            "enriched_metadata": []
        }
        
        # Process documents in parallel (4 workers)
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_doc = {
                executor.submit(self.ingest_document, doc_id, auto_approve): (idx, doc_id)
                for idx, doc_id in enumerate(docs_to_retry, 1)
            }
            
            for future in as_completed(future_to_doc):
                idx, doc_id = future_to_doc[future]
                print(f"Retrying {idx}/{total_docs}: {doc_id}... ", end="", flush=True)
                
                try:
                    result = future.result()
                    
                    if result["success"]:
                        print(f"✓ ({result['chunk_count']} chunks)")
                        ingestion_results["successfully_ingested"] += 1
                        ingestion_results["total_chunks"] += result["chunk_count"]
                        ingestion_results["ingested_documents"].append({
                            "document_id": doc_id,
                            "chunk_count": result["chunk_count"]
                        })
                        if result.get("enriched_metadata"):
                            ingestion_results["enriched_metadata"].append(result["enriched_metadata"])
                    else:
                        print(f"✗ ({result['error']})")
                        ingestion_results["failed_ingestions"] += 1
                        ingestion_results["failed_documents"].append({
                            "document_id": doc_id,
                            "error": result["error"]
                        })
                except Exception as e:
                    print(f"✗ (Exception: {str(e)})")
                    ingestion_results["failed_ingestions"] += 1
                    ingestion_results["failed_documents"].append({
                        "document_id": doc_id,
                        "error": str(e)
                    })
        
        # Auto-save storage to disk
        try:
            self.vector_store.save_to_disk()
            self.keyword_index.save_to_disk()
            self.knowledge_graph.save_to_disk()
        except Exception as e:
            print(f"⚠️ Warning: Failed to save storage to disk: {str(e)}")
        
        end_time = time.time()
        ingestion_results["processing_time_seconds"] = end_time - start_time
        
        # Generate report if requested
        if generate_report:
            try:
                from reports.ingestion_report_generator import IngestionReportGenerator
                audit_logs = self.staging_pipeline.get_audit_logs()
                storage_stats = {
                    "vector_store": self.vector_store.get_stats(),
                    "keyword_index": self.keyword_index.get_stats(),
                    "knowledge_graph": self.knowledge_graph.get_stats()
                }
                
                report_generator = IngestionReportGenerator()
                report_path = report_generator.generate_report(
                    ingestion_results=ingestion_results,
                    audit_logs=audit_logs,
                    storage_stats=storage_stats
                )
                print(f"📊 Retry report generated: {report_path}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to generate report: {str(e)}")
        
        return ingestion_results
    
    def ingest_delta(self, since: Optional[str] = None) -> Dict:
        """
        Ingest only changed documents since last sync.
        """
        changed_docs = self.sharepoint_api.get_changes(since)
        
        delta_results = {
            "changed_documents": len(changed_docs),
            "successfully_ingested": 0,
            "failed_ingestions": 0,
            "total_chunks": 0
        }
        
        for doc in changed_docs:
            result = self.ingest_document(doc["document_id"])
            if result["success"]:
                delta_results["successfully_ingested"] += 1
                delta_results["total_chunks"] += result.get("chunk_count", 0)
            else:
                delta_results["failed_ingestions"] += 1
        
        return delta_results
    
    def _delete_document_chunks(self, document_id: str) -> None:
        """Delete all chunks for a document from all storage systems."""
        # Get all chunks for this document
        all_chunks = self.vector_store.chunks_store
        chunks_to_delete = [
            chunk_id for chunk_id, chunk_data in all_chunks.items()
            if chunk_data.get("document_id") == document_id
        ]
        
        for chunk_id in chunks_to_delete:
            self.vector_store.delete_chunk(chunk_id)
            self.keyword_index.delete_chunk(chunk_id)
            self.knowledge_graph.delete_chunk(chunk_id)
    
    def _create_crm_summary_chunk(self, document_id: str, metadata: Dict) -> type:
        """Create a synthetic chunk containing CRM opportunity summary for searchability."""
        crm_text = f"""
CRM Opportunity Summary:
Client: {metadata.get('client', 'Unknown')}
Opportunity Name: {metadata.get('opportunity_name', 'N/A')}
CRM ID: {metadata.get('crm_id', 'N/A')}
Project ID: {metadata.get('project_id', 'N/A')}
Status: {metadata.get('crm_status', 'Unknown')}
Opportunity Value: ${metadata.get('crm_value', 0):,} USD
Service Line: {metadata.get('service_line', 'N/A')}
Sector: {metadata.get('sector', 'N/A')}
Engagement Partner: {metadata.get('engagement_partner', 'N/A')}
Start Date: {metadata.get('crm_start_date', 'N/A')}
End Date: {metadata.get('crm_end_date', 'N/A')}
Match Method: {metadata.get('crm_match_method', 'N/A')}
Match Confidence: {metadata.get('crm_match_confidence', 0):.0%}

This is CRM data enrichment for the associated document.
""".strip()
        
        # Create chunk object
        crm_chunk = type('Chunk', (), {
            'chunk_id': f"{document_id}_crm_summary",
            'document_id': document_id,
            'page_number': 0,  # Special page number for CRM chunks
            'cleaned_text': crm_text,
            'token_count': len(crm_text.split()),
            'position_in_document': -1,  # Special position for CRM chunks
            'metadata': metadata.copy()
        })()
        
        return crm_chunk
    
    def get_ingestion_stats(self) -> Dict:
        """Get comprehensive ingestion statistics."""
        registry_stats = self.ingestion_registry.get_ingestion_stats()
        vector_stats = self.vector_store.get_stats()
        
        return {
            # Flattened for dashboard
            "successfully_ingested": registry_stats.get("total_documents", 0),
            "total_chunks": vector_stats.get("total_chunks", 0),
            "failed_ingestions": registry_stats.get("failed_documents", 0),
            # Detailed stats
            "registry_stats": registry_stats,
            "vector_store_stats": vector_stats,
            "keyword_index_stats": self.keyword_index.get_stats(),
            "knowledge_graph_stats": self.knowledge_graph.get_stats()
        }
