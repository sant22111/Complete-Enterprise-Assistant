"""
Ingestion Report Generator
Generates detailed reports of ingestion runs
"""

import os
from datetime import datetime
from typing import Dict, List

class IngestionReportGenerator:
    """Generate detailed ingestion reports."""
    
    def __init__(self, reports_dir: str = "./reports"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
    
    def generate_report(
        self,
        ingestion_results: Dict,
        audit_logs: List[Dict] = None,
        storage_stats: Dict = None,
        crm_stats: Dict = None
    ) -> str:
        """
        Generate comprehensive ingestion report.
        
        Args:
            ingestion_results: Results from ingestion service
            audit_logs: PII redaction audit logs
            storage_stats: Storage system statistics
            crm_stats: CRM enrichment statistics
            
        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.reports_dir, f"ingestion_report_{timestamp}.txt")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write("INGESTION REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Documents: {ingestion_results.get('total_documents', 0)}\n")
            f.write(f"Successfully Ingested: {ingestion_results.get('successfully_ingested', 0)}\n")
            f.write(f"Failed: {ingestion_results.get('failed_ingestions', 0)}\n")
            f.write(f"Total Chunks Created: {ingestion_results.get('total_chunks', 0)}\n")
            
            if 'processing_time_seconds' in ingestion_results:
                f.write(f"Processing Time: {ingestion_results['processing_time_seconds']:.2f} seconds\n")
            f.write("\n")
            
            # Storage Stats
            if storage_stats:
                f.write("STORAGE STATISTICS\n")
                f.write("-" * 80 + "\n")
                
                if 'vector_store' in storage_stats:
                    vs = storage_stats['vector_store']
                    f.write(f"Vector Store: {vs.get('total_chunks', 0)} chunks\n")
                
                if 'keyword_index' in storage_stats:
                    ki = storage_stats['keyword_index']
                    f.write(f"Keyword Index: {ki.get('total_chunks', 0)} chunks\n")
                
                if 'knowledge_graph' in storage_stats:
                    kg = storage_stats['knowledge_graph']
                    f.write(f"Knowledge Graph: {kg.get('total_entities', 0)} entities, ")
                    f.write(f"{kg.get('total_relationships', 0)} relationships\n")
                f.write("\n")
            
            # CRM Stats
            if crm_stats:
                f.write("CRM ENRICHMENT\n")
                f.write("-" * 80 + "\n")
                f.write(f"Total Documents: {crm_stats.get('total_documents', 0)}\n")
                f.write(f"Matched with CRM: {crm_stats.get('matched_documents', 0)}\n")
                f.write(f"Match Rate: {crm_stats.get('match_rate', 0):.1f}%\n")
                f.write("\n")
            
            # Successful Documents
            if ingestion_results.get('ingested_documents'):
                f.write("SUCCESSFULLY INGESTED DOCUMENTS\n")
                f.write("-" * 80 + "\n")
                for doc in ingestion_results['ingested_documents'][:20]:  # First 20
                    f.write(f"  - {doc['document_id']}: {doc['chunk_count']} chunks\n")
                
                if len(ingestion_results['ingested_documents']) > 20:
                    remaining = len(ingestion_results['ingested_documents']) - 20
                    f.write(f"  ... and {remaining} more\n")
                f.write("\n")
            
            # Failed Documents
            if ingestion_results.get('failed_documents'):
                f.write("FAILED DOCUMENTS\n")
                f.write("-" * 80 + "\n")
                for doc in ingestion_results['failed_documents']:
                    f.write(f"  - {doc['document_id']}: {doc.get('error', 'Unknown error')}\n")
                f.write("\n")
            
            # PII Redactions
            if audit_logs:
                f.write("PII REDACTIONS\n")
                f.write("-" * 80 + "\n")
                redaction_count = sum(1 for log in audit_logs if log.get('event_type') == 'pii_redacted')
                f.write(f"Total Redactions: {redaction_count}\n")
                f.write("\n")
            
            # Footer
            f.write("=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")
        
        return report_path
