#!/usr/bin/env python3
"""
Redaction Demo - Show PII detection and redaction in action.
Demonstrates the staging pipeline processing real documents.
"""

from mock_sharepoint.api import MockSharePointAPI
from staging.staging_pipeline import StagingPipeline
from config import storage_config
import json

print("\n" + "="*80)
print("PII REDACTION DEMO - Real Documents from Disk")
print("="*80 + "\n")

sharepoint_api = MockSharePointAPI()
staging_pipeline = StagingPipeline(storage_config.audit_log_path)

documents = sharepoint_api.list_documents()

print(f"Found {len(documents)} documents from disk\n")

for doc_meta in documents:
    doc_id = doc_meta["document_id"]
    client = doc_meta["client"]
    doc_type = doc_meta["document_type"]
    
    print("="*80)
    print(f"DOCUMENT: {doc_id} ({client} - {doc_type})")
    print("="*80)
    
    doc_content = sharepoint_api.download_document(doc_id)
    
    print("\n[ORIGINAL CONTENT - WITH PII]")
    print("-" * 80)
    print(doc_content[:500] + "...\n" if len(doc_content) > 500 else doc_content + "\n")
    
    staged_doc = staging_pipeline.process_document(
        document_id=doc_id,
        raw_content=doc_content,
        file_format=".txt",
        auto_approve=True
    )
    
    print("[REDACTED CONTENT - PII REMOVED]")
    print("-" * 80)
    print(staged_doc.redacted_text[:500] + "...\n" if len(staged_doc.redacted_text) > 500 else staged_doc.redacted_text + "\n")
    
    print("[REDACTION SUMMARY]")
    print("-" * 80)
    print(f"Original text length: {len(doc_content)} characters")
    print(f"Redacted text length: {len(staged_doc.redacted_text)} characters")
    print(f"Total redactions applied: {len(staged_doc.redactions_applied)}")
    
    if staged_doc.redactions_applied:
        print("\nRedactions by type:")
        redaction_types = {}
        for redaction in staged_doc.redactions_applied:
            pii_type = redaction["pii_type"]
            redaction_types[pii_type] = redaction_types.get(pii_type, 0) + 1
        
        for pii_type, count in redaction_types.items():
            print(f"  - {pii_type}: {count} redacted")
        
        print("\nExample redactions:")
        for i, redaction in enumerate(staged_doc.redactions_applied[:3]):
            print(f"  {i+1}. Type: {redaction['pii_type']}")
            print(f"     Original: {redaction['original_text']}")
            print(f"     Replaced: {redaction['replacement']}")
    
    print(f"\nApproval Status: {staged_doc.approval_status}")
    print()

print("\n" + "="*80)
print("AUDIT LOG SUMMARY")
print("="*80 + "\n")

audit_logs = staging_pipeline.get_audit_logs()
print(f"Total audit entries: {len(audit_logs)}\n")

for log in audit_logs:
    print(f"Document: {log.document_id}")
    print(f"  Status: {log.approval_status}")
    print(f"  Redactions: {len(log.redactions_applied)}")
    print(f"  Timestamp: {log.timestamp}")
    print()

print("="*80)
print("✓ REDACTION DEMO COMPLETE")
print("="*80)
print("\nKey Observations:")
print("1. Real documents loaded from ./sample_documents/ folder")
print("2. PII automatically detected (emails, phones, SSN, credit cards)")
print("3. PII replaced with [REDACTED_*] placeholders")
print("4. Complete audit trail maintained")
print("5. Documents approved and ready for ingestion")
