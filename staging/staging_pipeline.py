from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from staging.text_extractor import TextExtractor
from staging.pii_detector import PIIDetector
from staging.audit_logger import AuditLogger

@dataclass
class StagedDocument:
    document_id: str
    original_text: str
    redacted_text: str
    redactions_applied: list
    pii_detected_count: int
    approval_status: str
    staging_timestamp: str
    extraction_method: str

class StagingPipeline:
    """
    Orchestrates the staging layer: text extraction, PII detection/redaction, audit logging.
    CRITICAL: All documents must pass through staging before downstream processing.
    """
    
    def __init__(self, audit_log_path: str = "./logs/audit_logs.jsonl"):
        self.text_extractor = TextExtractor()
        self.pii_detector = PIIDetector()
        self.audit_logger = AuditLogger(audit_log_path)
    
    def process_document(
        self,
        document_id: str,
        raw_content: str,
        file_format: str = ".txt",
        auto_approve: bool = False
    ) -> StagedDocument:
        """
        Process a document through the staging pipeline.
        
        Steps:
        1. Extract text
        2. Detect PII
        3. Redact PII
        4. Log to audit trail
        5. Mark for approval
        """
        
        extracted = self.text_extractor.extract(raw_content, file_format)
        
        redacted_text, redaction_log, pii_matches = self.pii_detector.detect_and_redact(
            extracted.raw_text
        )
        
        audit_log = self.audit_logger.log_redaction(
            document_id=document_id,
            original_text=extracted.raw_text,
            redacted_text=redacted_text,
            redactions_applied=redaction_log
        )
        
        if auto_approve:
            self.audit_logger.approve_document(document_id, approved_by="system")
            approval_status = "approved"
        else:
            approval_status = "pending"
        
        staged_doc = StagedDocument(
            document_id=document_id,
            original_text=extracted.raw_text,
            redacted_text=redacted_text,
            redactions_applied=redaction_log,
            pii_detected_count=len(pii_matches),
            approval_status=approval_status,
            staging_timestamp=datetime.now().isoformat(),
            extraction_method=extracted.extraction_method
        )
        
        return staged_doc
    
    def approve_document(self, document_id: str) -> bool:
        """Approve a staged document for downstream processing."""
        return self.audit_logger.approve_document(document_id, approved_by="human_reviewer")
    
    def reject_document(self, document_id: str, reason: str = "") -> bool:
        """Reject a staged document."""
        return self.audit_logger.reject_document(document_id, reason)
    
    def get_pending_documents(self) -> list:
        """Get all documents pending approval."""
        return self.audit_logger.get_pending_approvals()
    
    def get_audit_logs(self, document_id: Optional[str] = None) -> list:
        """Retrieve audit logs."""
        if document_id:
            return self.audit_logger.get_logs_by_document(document_id)
        return self.audit_logger.get_all_logs()
