import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class IngestionRecord:
    document_id: str
    last_ingested: str
    file_hash: str
    status: str
    ingestion_timestamp: str
    chunk_count: int = 0
    error_message: Optional[str] = None

class IngestionRegistry:
    """
    Maintains registry of all ingested documents.
    Tracks: document_id, last_ingested, file_hash, status.
    Enables delta ingestion (only new/updated files).
    """
    
    def __init__(self, registry_path: str = "./logs/ingestion_registry.jsonl"):
        self.registry_path = registry_path
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        self.records = {}
        self._load_registry()
    
    def register_ingestion(
        self,
        document_id: str,
        file_hash: str,
        chunk_count: int = 0,
        status: str = "success"
    ) -> IngestionRecord:
        """Register a successfully ingested document."""
        record = IngestionRecord(
            document_id=document_id,
            last_ingested=datetime.now().isoformat(),
            file_hash=file_hash,
            status=status,
            ingestion_timestamp=datetime.now().isoformat(),
            chunk_count=chunk_count
        )
        
        self.records[document_id] = record
        self._write_record(record)
        return record
    
    def mark_failed(
        self,
        document_id: str,
        error_message: str
    ) -> IngestionRecord:
        """Mark a document as failed ingestion."""
        record = IngestionRecord(
            document_id=document_id,
            last_ingested=datetime.now().isoformat(),
            file_hash="",
            status="failed",
            ingestion_timestamp=datetime.now().isoformat(),
            error_message=error_message
        )
        
        self.records[document_id] = record
        self._write_record(record)
        return record
    
    def is_already_ingested(self, document_id: str, file_hash: str) -> bool:
        """Check if document with same hash was already ingested."""
        if document_id not in self.records:
            return False
        
        record = self.records[document_id]
        return record.file_hash == file_hash and record.status == "success"
    
    def get_record(self, document_id: str) -> Optional[IngestionRecord]:
        """Get ingestion record for a document."""
        return self.records.get(document_id)
    
    def get_ingestion_entry(self, document_id: str) -> Optional[Dict]:
        """Get ingestion entry as dict (for delta ingestion checks)."""
        record = self.records.get(document_id)
        if record:
            return {
                "document_id": record.document_id,
                "file_hash": record.file_hash,
                "status": record.status,
                "chunk_count": record.chunk_count
            }
        return None
    
    def get_all_records(self) -> List[IngestionRecord]:
        """Get all ingestion records."""
        return list(self.records.values())
    
    def get_failed_ingestions(self) -> List[IngestionRecord]:
        """Get all failed ingestions."""
        return [r for r in self.records.values() if r.status == "failed"]
    
    def get_ingestion_stats(self) -> Dict:
        """Get ingestion statistics."""
        all_records = self.get_all_records()
        successful = [r for r in all_records if r.status == "success"]
        failed = [r for r in all_records if r.status == "failed"]
        
        return {
            "total_documents": len(all_records),
            "successful_ingestions": len(successful),
            "failed_ingestions": len(failed),
            "total_chunks_ingested": sum(r.chunk_count for r in successful),
            "last_ingestion": max([r.last_ingested for r in all_records]) if all_records else None
        }
    
    def _load_registry(self):
        """Load existing registry from file."""
        if not os.path.exists(self.registry_path):
            return
        
        with open(self.registry_path, 'r') as f:
            for line in f:
                if line.strip():
                    record_dict = json.loads(line)
                    record = IngestionRecord(
                        document_id=record_dict.get("document_id"),
                        last_ingested=record_dict.get("last_ingested"),
                        file_hash=record_dict.get("file_hash"),
                        status=record_dict.get("status"),
                        ingestion_timestamp=record_dict.get("ingestion_timestamp"),
                        chunk_count=record_dict.get("chunk_count", 0),
                        error_message=record_dict.get("error_message")
                    )
                    self.records[record.document_id] = record
    
    def _write_record(self, record: IngestionRecord):
        """Write record to registry file."""
        with open(self.registry_path, 'a') as f:
            f.write(json.dumps(asdict(record)) + '\n')
