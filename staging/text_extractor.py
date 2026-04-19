import re
from typing import Tuple, Optional
from dataclasses import dataclass
from staging.document_parsers import DocumentParser

@dataclass
class ExtractedText:
    raw_text: str
    page_count: int = 1
    extraction_method: str = "text"

class TextExtractor:
    def __init__(self):
        self.parser = DocumentParser()
    
    def extract_text(self, document) -> str:
        """Extract text from document using appropriate parser."""
        # If document has file_path, use parser
        if hasattr(document, 'file_path') and document.file_path:
            result = self.parser.parse_file(document.file_path)
            return result['text']
        
        # Otherwise use existing content
        return document.content if hasattr(document, 'content') else ""
    
    def extract_from_pdf_like(self, content: str) -> ExtractedText:
        """
        Extract text from PDF-like content.
        In production, would use PyMuPDF (fitz).
        """
        cleaned_text = self._clean_text(content)
        
        page_count = max(1, len(cleaned_text) // 3000)
        
        return ExtractedText(
            raw_text=cleaned_text,
            page_count=page_count,
            extraction_method="pdf"
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        return text
    
    def extract(self, content: str, file_format: str = ".txt") -> ExtractedText:
        """Extract text based on file format."""
        import os
        
        # Check if content is a file path (for PDF/PPT/Word files)
        if file_format.lower() in ['.pdf', '.ppt', '.pptx', '.doc', '.docx']:
            # Content is actually a file path - use DocumentParser
            result = self.parser.parse_file(content)
            return ExtractedText(
                raw_text=result['text'],
                page_count=result.get('page_count', 1),
                extraction_method=result.get('format', file_format.replace('.', ''))
            )
        elif file_format.lower() == ".pdf":
            # Content is text that looks like PDF
            return self.extract_from_pdf_like(content)
        else:
            # Content is plain text
            return self.extract_from_text(content)
    
    def extract_from_text(self, content: str) -> ExtractedText:
        """Extract text from plain text content."""
        cleaned_text = self._clean_text(content)
        return ExtractedText(
            raw_text=cleaned_text,
            page_count=1,
            extraction_method="text"
        )
