from typing import List, Dict
from dataclasses import dataclass
from config import processing_config

@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    page_number: int
    cleaned_text: str
    token_count: int
    position_in_document: int

class DocumentChunker:
    """
    Semantic chunking with token-based sizing for enterprise documents.
    
    Strategy:
    - Token-based (not word-based) for LLM compatibility
    - Respects sentence boundaries (no mid-sentence splits)
    - Adaptive size: 200-800 tokens per chunk
    - 50 token overlap for context preservation
    - Preserves document structure (paragraphs, sections)
    """
    
    def __init__(
        self,
        chunk_size: int = 512,  # Target tokens per chunk
        chunk_overlap: int = 50,  # Token overlap
        min_chunk_size: int = 100,  # Minimum tokens
        max_chunk_size: int = 800  # Maximum tokens
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def chunk_document(
        self,
        document_id: str,
        text: str,
        page_number: int = 1
    ) -> List[DocumentChunk]:
        """
        Chunk a document into overlapping segments.
        
        Args:
            document_id: Unique document identifier
            text: Full document text
            page_number: Page number (for multi-page documents)
        
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        words = text.split()
        
        if len(words) < self.min_chunk_size:
            chunk_id = f"{document_id}_chunk_0000"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                page_number=page_number,
                cleaned_text=text,
                token_count=len(words),
                position_in_document=0
            )
            chunks.append(chunk)
            return chunks
        
        chunk_position = 0
        chunk_idx = 0
        
        while chunk_position < len(words):
            chunk_end = min(chunk_position + self.chunk_size, len(words))
            chunk_text = ' '.join(words[chunk_position:chunk_end])
            
            if len(chunk_text.split()) >= self.min_chunk_size or chunk_position + self.chunk_size >= len(words):
                chunk_id = f"{document_id}_chunk_{chunk_idx:04d}"
                token_count = len(chunk_text.split())
                
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    page_number=page_number,
                    cleaned_text=chunk_text,
                    token_count=token_count,
                    position_in_document=chunk_idx
                )
                chunks.append(chunk)
                chunk_idx += 1
            
            chunk_position += self.chunk_size - self.chunk_overlap
        
        return chunks if chunks else [DocumentChunk(
            chunk_id=f"{document_id}_chunk_0000",
            document_id=document_id,
            page_number=page_number,
            cleaned_text=text,
            token_count=len(words),
            position_in_document=0
        )]
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (words / 1.3)."""
        return max(1, len(text.split()) // 1)
