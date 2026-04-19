from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class EnrichedChunk:
    chunk_id: str
    document_id: str
    page_number: int
    cleaned_text: str
    token_count: int
    position_in_document: int
    metadata: Dict

class MetadataEnricher:
    """
    Attaches structured metadata to document chunks.
    Ensures traceability and governance throughout the system.
    """
    
    def enrich_chunk(
        self,
        chunk_id: str,
        document_id: str,
        page_number: int,
        cleaned_text: str,
        token_count: int,
        position_in_document: int,
        document_metadata: Dict
    ) -> EnrichedChunk:
        """
        Enrich a chunk with structured metadata.
        
        Args:
            chunk_id: Unique chunk identifier
            document_id: Parent document ID
            page_number: Page number in document
            cleaned_text: Chunk text
            token_count: Token count
            position_in_document: Position in document
            document_metadata: Document-level metadata (client, service_line, etc.)
        
        Returns:
            EnrichedChunk with full metadata
        """
        
        metadata = {
            "client": document_metadata.get("client"),
            "service_line": document_metadata.get("service_line"),
            "document_type": document_metadata.get("document_type"),
            "year": document_metadata.get("year"),
            "sensitivity_level": document_metadata.get("sensitivity_level"),
            "source_file": document_metadata.get("source_file"),
            "source_system": document_metadata.get("source_system", "sharepoint"),
            "ingestion_timestamp": document_metadata.get("ingestion_timestamp", datetime.now().isoformat()),
            "file_path": document_metadata.get("file_path"),
            "last_modified": document_metadata.get("last_modified")
        }
        
        return EnrichedChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            page_number=page_number,
            cleaned_text=cleaned_text,
            token_count=token_count,
            position_in_document=position_in_document,
            metadata=metadata
        )
    
    def enrich_chunks(
        self,
        chunks: List[Dict],
        document_metadata: Dict
    ) -> List[EnrichedChunk]:
        """
        Enrich multiple chunks with metadata.
        """
        enriched = []
        for chunk in chunks:
            enriched_chunk = self.enrich_chunk(
                chunk_id=chunk.get("chunk_id"),
                document_id=chunk.get("document_id"),
                page_number=chunk.get("page_number"),
                cleaned_text=chunk.get("cleaned_text"),
                token_count=chunk.get("token_count"),
                position_in_document=chunk.get("position_in_document"),
                document_metadata=document_metadata
            )
            enriched.append(enriched_chunk)
        
        return enriched
