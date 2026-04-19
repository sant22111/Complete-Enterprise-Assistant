from typing import List, Dict
from dataclasses import dataclass
import re
from pathlib import Path

@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    page_number: int
    cleaned_text: str
    token_count: int
    position_in_document: int
    chunk_type: str  # 'paragraph', 'slide', 'section'

class SmartChunker:
    """
    Document-type aware chunker with semantic boundaries.
    
    Supports:
    - PDF: Semantic chunking (400-600 tokens, paragraph-aware)
    - PPT: Slide-level chunking (200-400 tokens per slide)
    - Word: Structural chunking (400-700 tokens, heading-aware)
    """
    
    def __init__(self):
        self.pdf_config = {
            'target_tokens': 512,
            'min_tokens': 400,
            'max_tokens': 600,
            'overlap': 50
        }
        self.ppt_config = {
            'target_tokens': 300,
            'min_tokens': 200,
            'max_tokens': 400,
            'overlap': 0  # Slides are self-contained
        }
        self.word_config = {
            'target_tokens': 512,
            'min_tokens': 400,
            'max_tokens': 700,
            'overlap': 50
        }
    
    def chunk_document(
        self,
        document_id: str,
        text: str,
        file_path: str = None
    ) -> List[DocumentChunk]:
        """
        Chunk document based on file type.
        
        Args:
            document_id: Unique document identifier
            text: Full document text
            file_path: Path to file (for type detection)
        
        Returns:
            List of DocumentChunk objects
        """
        doc_type = self._detect_document_type(file_path)
        
        if doc_type == 'pdf':
            return self._chunk_pdf(document_id, text)
        elif doc_type == 'pptx':
            return self._chunk_ppt(document_id, text)
        elif doc_type == 'docx':
            return self._chunk_word(document_id, text)
        else:
            # Fallback to PDF strategy for unknown types
            return self._chunk_pdf(document_id, text)
    
    def _detect_document_type(self, file_path: str) -> str:
        """Detect document type from file extension."""
        if not file_path:
            return 'pdf'  # Default
        
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.pdf']:
            return 'pdf'
        elif ext in ['.pptx', '.ppt']:
            return 'pptx'
        elif ext in ['.docx', '.doc']:
            return 'docx'
        else:
            return 'pdf'  # Default fallback
    
    def _chunk_pdf(self, document_id: str, text: str) -> List[DocumentChunk]:
        """
        Semantic chunking for PDFs.
        
        Strategy:
        - Respect paragraph boundaries
        - Preserve sections
        - 400-600 tokens per chunk
        - 50 token overlap
        """
        chunks = []
        
        # Split into paragraphs (double newline or section markers)
        paragraphs = self._split_into_paragraphs(text)
        
        current_chunk = []
        current_tokens = 0
        chunk_idx = 0
        
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            
            # If adding this paragraph exceeds max, save current chunk
            if current_tokens + para_tokens > self.pdf_config['max_tokens'] and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    document_id, chunk_text, chunk_idx, 'paragraph'
                ))
                
                # Keep overlap: last paragraph for context
                overlap_text = current_chunk[-1] if current_chunk else ''
                overlap_tokens = self._estimate_tokens(overlap_text)
                
                if overlap_tokens <= self.pdf_config['overlap']:
                    current_chunk = [overlap_text, para]
                    current_tokens = overlap_tokens + para_tokens
                else:
                    current_chunk = [para]
                    current_tokens = para_tokens
                
                chunk_idx += 1
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
            
            # If current chunk is large enough, save it
            if current_tokens >= self.pdf_config['target_tokens']:
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    document_id, chunk_text, chunk_idx, 'paragraph'
                ))
                
                # Keep overlap
                overlap_text = current_chunk[-1] if current_chunk else ''
                overlap_tokens = self._estimate_tokens(overlap_text)
                
                if overlap_tokens <= self.pdf_config['overlap']:
                    current_chunk = [overlap_text]
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0
                
                chunk_idx += 1
        
        # Save remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if self._estimate_tokens(chunk_text) >= self.pdf_config['min_tokens']:
                chunks.append(self._create_chunk(
                    document_id, chunk_text, chunk_idx, 'paragraph'
                ))
        
        return chunks if chunks else [self._create_chunk(document_id, text, 0, 'paragraph')]
    
    def _chunk_ppt(self, document_id: str, text: str) -> List[DocumentChunk]:
        """
        Slide-level chunking for PowerPoint.
        
        Strategy:
        - One slide = one chunk (or combine 2-3 small slides)
        - 200-400 tokens per chunk
        - No overlap (slides are self-contained)
        """
        chunks = []
        
        # Split by slide markers (assume slides separated by specific patterns)
        # For now, use paragraph splits as proxy for slides
        slides = self._split_into_slides(text)
        
        current_slides = []
        current_tokens = 0
        chunk_idx = 0
        
        for slide in slides:
            slide_tokens = self._estimate_tokens(slide)
            
            # If slide is too large, chunk it
            if slide_tokens > self.ppt_config['max_tokens']:
                # Save current accumulated slides first
                if current_slides:
                    chunk_text = '\n\n'.join(current_slides)
                    chunks.append(self._create_chunk(
                        document_id, chunk_text, chunk_idx, 'slide'
                    ))
                    chunk_idx += 1
                    current_slides = []
                    current_tokens = 0
                
                # Chunk large slide
                slide_chunks = self._chunk_large_slide(slide)
                for sc in slide_chunks:
                    chunks.append(self._create_chunk(
                        document_id, sc, chunk_idx, 'slide'
                    ))
                    chunk_idx += 1
            
            # If adding this slide exceeds target, save current
            elif current_tokens + slide_tokens > self.ppt_config['target_tokens'] and current_slides:
                chunk_text = '\n\n'.join(current_slides)
                chunks.append(self._create_chunk(
                    document_id, chunk_text, chunk_idx, 'slide'
                ))
                chunk_idx += 1
                current_slides = [slide]
                current_tokens = slide_tokens
            
            else:
                current_slides.append(slide)
                current_tokens += slide_tokens
        
        # Save remaining slides
        if current_slides:
            chunk_text = '\n\n'.join(current_slides)
            chunks.append(self._create_chunk(
                document_id, chunk_text, chunk_idx, 'slide'
            ))
        
        return chunks if chunks else [self._create_chunk(document_id, text, 0, 'slide')]
    
    def _chunk_word(self, document_id: str, text: str) -> List[DocumentChunk]:
        """
        Structural chunking for Word documents.
        
        Strategy:
        - Respect headings (H1, H2, H3)
        - Paragraph-aware
        - 400-700 tokens per chunk
        - 50 token overlap
        """
        chunks = []
        
        # Split by sections (headings or paragraphs)
        sections = self._split_into_sections(text)
        
        current_chunk = []
        current_tokens = 0
        chunk_idx = 0
        
        for section in sections:
            section_tokens = self._estimate_tokens(section)
            
            # If section is too large, split it
            if section_tokens > self.word_config['max_tokens']:
                # Save current chunk first
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(self._create_chunk(
                        document_id, chunk_text, chunk_idx, 'section'
                    ))
                    chunk_idx += 1
                    current_chunk = []
                    current_tokens = 0
                
                # Split large section into paragraphs
                paragraphs = self._split_into_paragraphs(section)
                for para in paragraphs:
                    para_tokens = self._estimate_tokens(para)
                    
                    if current_tokens + para_tokens > self.word_config['max_tokens'] and current_chunk:
                        chunk_text = ' '.join(current_chunk)
                        chunks.append(self._create_chunk(
                            document_id, chunk_text, chunk_idx, 'section'
                        ))
                        
                        # Keep overlap
                        overlap_text = current_chunk[-1] if current_chunk else ''
                        current_chunk = [overlap_text, para]
                        current_tokens = self._estimate_tokens(overlap_text) + para_tokens
                        chunk_idx += 1
                    else:
                        current_chunk.append(para)
                        current_tokens += para_tokens
            
            # If adding this section exceeds max, save current chunk
            elif current_tokens + section_tokens > self.word_config['max_tokens'] and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    document_id, chunk_text, chunk_idx, 'section'
                ))
                
                # Keep overlap
                overlap_text = current_chunk[-1] if current_chunk else ''
                overlap_tokens = self._estimate_tokens(overlap_text)
                
                if overlap_tokens <= self.word_config['overlap']:
                    current_chunk = [overlap_text, section]
                    current_tokens = overlap_tokens + section_tokens
                else:
                    current_chunk = [section]
                    current_tokens = section_tokens
                
                chunk_idx += 1
            else:
                current_chunk.append(section)
                current_tokens += section_tokens
        
        # Save remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if self._estimate_tokens(chunk_text) >= self.word_config['min_tokens']:
                chunks.append(self._create_chunk(
                    document_id, chunk_text, chunk_idx, 'section'
                ))
        
        return chunks if chunks else [self._create_chunk(document_id, text, 0, 'section')]
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs (double newline or section breaks)."""
        # Split by double newline or multiple spaces
        paragraphs = re.split(r'\n\s*\n+', text)
        # Clean and filter empty
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_into_slides(self, text: str) -> List[str]:
        """Split text into slides (for PPT, use paragraph splits as proxy)."""
        # In real implementation, would parse PPT structure
        # For now, treat large paragraphs as slides
        paragraphs = self._split_into_paragraphs(text)
        return paragraphs
    
    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into sections (for Word, detect headings)."""
        # Split by headings (lines that are short and followed by content)
        # Or use paragraph splits as fallback
        sections = []
        current_section = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect potential heading (short line, all caps or title case)
            if len(line) < 100 and (line.isupper() or line.istitle()):
                if current_section:
                    sections.append(' '.join(current_section))
                    current_section = [line]
                else:
                    current_section.append(line)
            else:
                current_section.append(line)
        
        if current_section:
            sections.append(' '.join(current_section))
        
        return sections if sections else self._split_into_paragraphs(text)
    
    def _chunk_large_slide(self, slide: str) -> List[str]:
        """Chunk a large slide into smaller pieces."""
        paragraphs = self._split_into_paragraphs(slide)
        chunks = []
        current = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            if current_tokens + para_tokens > self.ppt_config['max_tokens'] and current:
                chunks.append(' '.join(current))
                current = [para]
                current_tokens = para_tokens
            else:
                current.append(para)
                current_tokens += para_tokens
        
        if current:
            chunks.append(' '.join(current))
        
        return chunks
    
    def _create_chunk(
        self,
        document_id: str,
        text: str,
        chunk_idx: int,
        chunk_type: str
    ) -> DocumentChunk:
        """Create a DocumentChunk object."""
        chunk_id = f"{document_id}_chunk_{chunk_idx:04d}"
        token_count = self._estimate_tokens(text)
        
        return DocumentChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            page_number=1,
            cleaned_text=text,
            token_count=token_count,
            position_in_document=chunk_idx,
            chunk_type=chunk_type
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.
        
        Rough approximation: 1 token ≈ 0.75 words
        More accurate than word count for LLM compatibility.
        """
        words = len(text.split())
        # Average: 1 token = 0.75 words, so tokens = words / 0.75
        return int(words / 0.75)
