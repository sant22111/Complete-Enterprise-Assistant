import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import random

@dataclass
class SharePointDocument:
    document_id: str
    file_path: str
    client: str
    service_line: str
    document_type: str
    year: int
    sensitivity_level: str
    last_modified: str
    source_system: str = "sharepoint"
    file_content: str = ""

class MockSharePointAPI:
    """
    Simulates a SharePoint API for document retrieval.
    Provides endpoints for listing, fetching metadata, downloading, and delta sync.
    """
    
    def __init__(self):
        self.documents = self._load_documents_from_disk()
        self.last_sync_timestamp = datetime.now() - timedelta(days=30)
    
    def _load_documents_from_disk(self) -> Dict[str, SharePointDocument]:
        """Load all PDF/PPT/Word documents from sample_documents folder."""
        documents = {}
        docs_folder = "./sample_documents"
        
        if not os.path.exists(docs_folder):
            return self._generate_sample_documents()
        
        # Get all document files
        supported_extensions = ('.pdf', '.ppt', '.pptx', '.doc', '.docx', '.txt')
        files = [f for f in os.listdir(docs_folder) if f.endswith(supported_extensions)]
        
        if not files:
            return self._generate_sample_documents()
        
        # Parse each filename to extract metadata
        # Expected format: {client}_{service_line}_{doc_type}_{number}.{ext}
        for idx, filename in enumerate(files):
            filepath = os.path.join(docs_folder, filename)
            
            # Extract metadata from filename
            name_parts = filename.rsplit('.', 1)[0].split('_')
            
            # Try to parse filename
            if len(name_parts) >= 3:
                client = name_parts[0].replace('_', ' ').title()
                service_line = name_parts[1].title() if len(name_parts) > 1 else "General"
                doc_type = name_parts[2].title() if len(name_parts) > 2 else "Document"
            else:
                client = "Unknown"
                service_line = "General"
                doc_type = "Document"
            
            # Assign sensitivity randomly
            sensitivity = random.choice(["Internal", "Confidential", "Restricted"])
            year = random.choice([2023, 2024])
            
            doc_id = f"doc_{idx:04d}"
            doc = SharePointDocument(
                document_id=doc_id,
                file_path=filepath,  # Use actual file path
                client=client,
                service_line=service_line,
                document_type=doc_type,
                year=year,
                sensitivity_level=sensitivity,
                last_modified=(datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                file_content=""  # Will be loaded by text extractor
            )
            documents[doc_id] = doc
        
        return documents
    
    def _generate_sample_documents(self) -> Dict[str, SharePointDocument]:
        """Fallback - should not be used if sample_documents folder exists."""
        return {}
    
    def list_documents(self) -> List[Dict]:
        """GET /documents - List all documents with metadata."""
        return [
            {
                "document_id": doc.document_id,
                "file_path": doc.file_path,
                "client": doc.client,
                "service_line": doc.service_line,
                "document_type": doc.document_type,
                "year": doc.year,
                "sensitivity_level": doc.sensitivity_level,
                "last_modified": doc.last_modified,
                "source_system": doc.source_system
            }
            for doc in self.documents.values()
        ]
    
    def get_document_metadata(self, document_id: str) -> Optional[Dict]:
        """GET /documents/{id} - Get document metadata."""
        if document_id not in self.documents:
            return None
        
        doc = self.documents[document_id]
        return {
            "document_id": doc.document_id,
            "file_path": doc.file_path,
            "client": doc.client,
            "service_line": doc.service_line,
            "document_type": doc.document_type,
            "year": doc.year,
            "sensitivity_level": doc.sensitivity_level,
            "last_modified": doc.last_modified,
            "source_system": doc.source_system
        }
    
    def download_document(self, document_id: str) -> Optional[str]:
        """GET /download/{id} - Download document content."""
        if document_id not in self.documents:
            return None
        
        return self.documents[document_id].file_content
    
    def get_changes(self, since: Optional[str] = None) -> List[Dict]:
        """GET /changes?since=timestamp - Get delta updates (documents modified since timestamp)."""
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
            except ValueError:
                since_dt = datetime.now() - timedelta(days=7)
        else:
            since_dt = self.last_sync_timestamp
        
        changed_docs = []
        for doc in self.documents.values():
            doc_modified = datetime.fromisoformat(doc.last_modified)
            if doc_modified >= since_dt:
                changed_docs.append({
                    "document_id": doc.document_id,
                    "file_path": doc.file_path,
                    "client": doc.client,
                    "service_line": doc.service_line,
                    "document_type": doc.document_type,
                    "year": doc.year,
                    "sensitivity_level": doc.sensitivity_level,
                    "last_modified": doc.last_modified,
                    "source_system": doc.source_system,
                    "change_type": "modified"
                })
        
        return changed_docs
    
    def compute_file_hash(self, content: str) -> str:
        """Compute SHA256 hash of file content."""
        return hashlib.sha256(content.encode()).hexdigest()
