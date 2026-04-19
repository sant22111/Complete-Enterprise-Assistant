import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class VersionEntry:
    version_number: int
    document_id: str
    file_hash: str
    previous_hash: Optional[str]
    timestamp: str
    chunk_count: int
    previous_chunk_count: int
    chunks_added: int
    chunks_deleted: int
    status: str
    change_type: str

class DocumentVersioning:
    """
    Tracks document versions and changes over time.
    Shows complete history of document updates and their impact.
    """
    
    def __init__(self, version_log_path: str = "./logs/document_versions.jsonl"):
        self.version_log_path = version_log_path
        os.makedirs(os.path.dirname(version_log_path), exist_ok=True)
        self.versions = {}
        self._load_versions()
    
    def record_ingestion(
        self,
        document_id: str,
        file_hash: str,
        chunk_count: int,
        previous_hash: Optional[str] = None,
        previous_chunk_count: int = 0,
        status: str = "success"
    ) -> VersionEntry:
        """Record a document ingestion as a new version."""
        
        # Determine change type
        if previous_hash is None:
            change_type = "initial"
        elif file_hash == previous_hash:
            change_type = "no_change"
        else:
            change_type = "updated"
        
        # Calculate chunk changes
        chunks_added = max(0, chunk_count - previous_chunk_count)
        chunks_deleted = max(0, previous_chunk_count - chunk_count)
        
        # Get next version number
        version_number = self._get_next_version(document_id)
        
        version_entry = VersionEntry(
            version_number=version_number,
            document_id=document_id,
            file_hash=file_hash,
            previous_hash=previous_hash,
            timestamp=datetime.now().isoformat(),
            chunk_count=chunk_count,
            previous_chunk_count=previous_chunk_count,
            chunks_added=chunks_added,
            chunks_deleted=chunks_deleted,
            status=status,
            change_type=change_type
        )
        
        # Store in memory
        if document_id not in self.versions:
            self.versions[document_id] = []
        self.versions[document_id].append(version_entry)
        
        # Write to file
        self._write_version(version_entry)
        
        return version_entry
    
    def get_document_history(self, document_id: str) -> List[VersionEntry]:
        """Get complete version history for a document."""
        return self.versions.get(document_id, [])
    
    def get_latest_version(self, document_id: str) -> Optional[VersionEntry]:
        """Get the latest version of a document."""
        history = self.get_document_history(document_id)
        return history[-1] if history else None
    
    def get_version(self, document_id: str, version_number: int) -> Optional[VersionEntry]:
        """Get a specific version of a document."""
        history = self.get_document_history(document_id)
        for version in history:
            if version.version_number == version_number:
                return version
        return None
    
    def get_changes_between_versions(
        self,
        document_id: str,
        from_version: int,
        to_version: int
    ) -> Dict:
        """Get changes between two versions."""
        from_v = self.get_version(document_id, from_version)
        to_v = self.get_version(document_id, to_version)
        
        if not from_v or not to_v:
            return {}
        
        return {
            "document_id": document_id,
            "from_version": from_version,
            "to_version": to_version,
            "from_hash": from_v.file_hash,
            "to_hash": to_v.file_hash,
            "from_timestamp": from_v.timestamp,
            "to_timestamp": to_v.timestamp,
            "hash_changed": from_v.file_hash != to_v.file_hash,
            "chunk_count_change": to_v.chunk_count - from_v.chunk_count,
            "chunks_added": to_v.chunks_added,
            "chunks_deleted": to_v.chunks_deleted
        }
    
    def get_all_versions(self) -> Dict[str, List[VersionEntry]]:
        """Get all versions for all documents."""
        return self.versions
    
    def _get_next_version(self, document_id: str) -> int:
        """Get next version number for a document."""
        history = self.get_document_history(document_id)
        if not history:
            return 1
        return max(v.version_number for v in history) + 1
    
    def _write_version(self, version_entry: VersionEntry):
        """Write version entry to file."""
        with open(self.version_log_path, 'a') as f:
            f.write(json.dumps(asdict(version_entry)) + '\n')
    
    def _load_versions(self):
        """Load existing versions from file."""
        if not os.path.exists(self.version_log_path):
            return
        
        with open(self.version_log_path, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    doc_id = data['document_id']
                    version = VersionEntry(
                        version_number=data['version_number'],
                        document_id=data['document_id'],
                        file_hash=data['file_hash'],
                        previous_hash=data['previous_hash'],
                        timestamp=data['timestamp'],
                        chunk_count=data['chunk_count'],
                        previous_chunk_count=data['previous_chunk_count'],
                        chunks_added=data['chunks_added'],
                        chunks_deleted=data['chunks_deleted'],
                        status=data['status'],
                        change_type=data['change_type']
                    )
                    if doc_id not in self.versions:
                        self.versions[doc_id] = []
                    self.versions[doc_id].append(version)
