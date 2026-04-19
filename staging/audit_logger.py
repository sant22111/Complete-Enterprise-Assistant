import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class AuditLog:
    document_id: str
    original_text: str
    redacted_text: str
    redactions_applied: List[Dict]
    timestamp: str
    approval_status: str = "pending"
    approved_by: Optional[str] = None
    approval_timestamp: Optional[str] = None

class AuditLogger:
    """
    Maintains comprehensive audit trail of all document processing.
    Tracks: original text, redactions, approvals, timestamps.
    """
    
    def __init__(self, log_path: str = "./logs/audit_logs.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    def log_redaction(
        self,
        document_id: str,
        original_text: str,
        redacted_text: str,
        redactions_applied: List[Dict]
    ) -> AuditLog:
        """Log a redaction event."""
        audit_log = AuditLog(
            document_id=document_id,
            original_text=original_text,
            redacted_text=redacted_text,
            redactions_applied=redactions_applied,
            timestamp=datetime.now().isoformat(),
            approval_status="pending"
        )
        
        self._write_log(audit_log)
        return audit_log
    
    def approve_document(
        self,
        document_id: str,
        approved_by: str = "system"
    ) -> bool:
        """Approve a document for downstream processing."""
        logs = self.get_logs_by_document(document_id)
        
        if not logs:
            return False
        
        latest_log = logs[-1]
        latest_log.approval_status = "approved"
        latest_log.approved_by = approved_by
        latest_log.approval_timestamp = datetime.now().isoformat()
        
        self._update_log(latest_log)
        return True
    
    def reject_document(
        self,
        document_id: str,
        reason: str = "Manual rejection"
    ) -> bool:
        """Reject a document."""
        logs = self.get_logs_by_document(document_id)
        
        if not logs:
            return False
        
        latest_log = logs[-1]
        latest_log.approval_status = "rejected"
        latest_log.approval_timestamp = datetime.now().isoformat()
        
        self._update_log(latest_log)
        return True
    
    def get_logs_by_document(self, document_id: str) -> List[AuditLog]:
        """Retrieve all audit logs for a document."""
        logs = []
        
        if not os.path.exists(self.log_path):
            return logs
        
        with open(self.log_path, 'r') as f:
            for line in f:
                if line.strip():
                    log_dict = json.loads(line)
                    if log_dict.get("document_id") == document_id:
                        logs.append(self._dict_to_audit_log(log_dict))
        
        return logs
    
    def get_all_logs(self) -> List[AuditLog]:
        """Retrieve all audit logs."""
        logs = []
        
        if not os.path.exists(self.log_path):
            return logs
        
        with open(self.log_path, 'r') as f:
            for line in f:
                if line.strip():
                    log_dict = json.loads(line)
                    logs.append(self._dict_to_audit_log(log_dict))
        
        return logs
    
    def get_pending_approvals(self) -> List[AuditLog]:
        """Get all documents pending approval."""
        all_logs = self.get_all_logs()
        return [log for log in all_logs if log.approval_status == "pending"]
    
    def _write_log(self, audit_log: AuditLog):
        """Write audit log to file."""
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(asdict(audit_log)) + '\n')
    
    def _update_log(self, audit_log: AuditLog):
        """Update an existing audit log (by rewriting the file)."""
        all_logs = self.get_all_logs()
        
        updated_logs = []
        for log in all_logs:
            if log.document_id == audit_log.document_id and log.timestamp == audit_log.timestamp:
                updated_logs.append(audit_log)
            else:
                updated_logs.append(log)
        
        with open(self.log_path, 'w') as f:
            for log in updated_logs:
                f.write(json.dumps(asdict(log)) + '\n')
    
    @staticmethod
    def _dict_to_audit_log(log_dict: Dict) -> AuditLog:
        """Convert dictionary to AuditLog object."""
        return AuditLog(
            document_id=log_dict.get("document_id"),
            original_text=log_dict.get("original_text"),
            redacted_text=log_dict.get("redacted_text"),
            redactions_applied=log_dict.get("redactions_applied", []),
            timestamp=log_dict.get("timestamp"),
            approval_status=log_dict.get("approval_status", "pending"),
            approved_by=log_dict.get("approved_by"),
            approval_timestamp=log_dict.get("approval_timestamp")
        )
