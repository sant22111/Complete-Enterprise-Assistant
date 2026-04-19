from typing import List, Dict, Optional
from dataclasses import dataclass
from retrieval.hybrid_retriever import HybridSearchResult

@dataclass
class EvidencePack:
    query: str
    chunks: List[Dict]
    total_confidence: float
    sources: List[Dict]
    related_entities: List[str]
    debug_info: Dict

class EvidencePackBuilder:
    """
    Constructs structured evidence packs before sending to LLM.
    Ensures traceability to original documents and maintains governance.
    """
    
    def build_evidence_pack(
        self,
        query: str,
        retrieved_chunks: List[HybridSearchResult],
        debug_info: Dict,
        confidence_threshold: float = 0.3
    ) -> EvidencePack:
        """
        Build structured evidence pack from retrieved chunks.
        
        Returns:
            EvidencePack with chunks, sources, entities, and confidence scores
        """
        chunks = []
        sources = {}
        entities = set()
        
        for chunk in retrieved_chunks:
            if chunk.final_score >= confidence_threshold:
                chunk_data = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "text": chunk.text,
                    "page": chunk.metadata.get("page_number", 1),
                    "confidence_score": chunk.final_score,
                    "source_type": chunk.source_type,
                    "metadata": chunk.metadata
                }
                chunks.append(chunk_data)
                
                source_key = chunk.document_id
                if source_key not in sources:
                    sources[source_key] = {
                        "document_id": chunk.document_id,
                        "client": chunk.metadata.get("client"),
                        "service_line": chunk.metadata.get("service_line"),
                        "document_type": chunk.metadata.get("document_type"),
                        "sensitivity_level": chunk.metadata.get("sensitivity_level"),
                        "source_file": chunk.metadata.get("source_file"),
                        "last_modified": chunk.metadata.get("last_modified"),
                        "chunk_count": 0
                    }
                sources[source_key]["chunk_count"] += 1
                
                if chunk.metadata.get("client"):
                    entities.add(chunk.metadata.get("client"))
                if chunk.metadata.get("service_line"):
                    entities.add(chunk.metadata.get("service_line"))
        
        total_confidence = sum(c["confidence_score"] for c in chunks) / len(chunks) if chunks else 0.0
        
        evidence_pack = EvidencePack(
            query=query,
            chunks=chunks,
            total_confidence=total_confidence,
            sources=list(sources.values()),
            related_entities=list(entities),
            debug_info=debug_info
        )
        
        return evidence_pack
    
    def format_evidence_for_llm(self, evidence_pack: EvidencePack) -> str:
        """
        Format evidence pack into readable text for LLM.
        """
        formatted = f"Query: {evidence_pack.query}\n\n"
        formatted += "Evidence:\n"
        formatted += "=" * 80 + "\n\n"
        
        for idx, chunk in enumerate(evidence_pack.chunks, 1):
            formatted += f"[Chunk {idx}] (Confidence: {chunk['confidence_score']:.2f})\n"
            formatted += f"Source: {chunk['document_id']} | Page: {chunk['page']}\n"
            formatted += f"Client: {chunk['metadata'].get('client')} | Service Line: {chunk['metadata'].get('service_line')}\n"
            formatted += f"Text: {chunk['text']}\n"
            formatted += "-" * 80 + "\n\n"
        
        formatted += f"\nTotal Confidence: {evidence_pack.total_confidence:.2f}\n"
        formatted += f"Related Entities: {', '.join(evidence_pack.related_entities)}\n"
        
        return formatted
    
    def get_evidence_summary(self, evidence_pack: EvidencePack) -> Dict:
        """Get summary of evidence pack."""
        return {
            "query": evidence_pack.query,
            "chunk_count": len(evidence_pack.chunks),
            "source_count": len(evidence_pack.sources),
            "total_confidence": evidence_pack.total_confidence,
            "related_entities": evidence_pack.related_entities,
            "sources": evidence_pack.sources,
            "debug_info": evidence_pack.debug_info
        }
