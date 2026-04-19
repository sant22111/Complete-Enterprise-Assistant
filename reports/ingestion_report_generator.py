"""
Ingestion Report Generator
Creates detailed reports after document ingestion.
"""

from datetime import datetime
from typing import Dict, List
import os

class IngestionReportGenerator:
    """Generates comprehensive ingestion reports."""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(
        self,
        ingestion_results: Dict,
        audit_logs: List[Dict],
        storage_stats: Dict,
        crm_stats: Dict = None
    ) -> str:
        """Generate comprehensive ingestion report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{self.output_dir}/ingestion_report_{timestamp}.txt"
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("ENTERPRISE RAG SYSTEM - INGESTION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Document Processing Summary
        report_lines.append("📄 DOCUMENT PROCESSING SUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Documents Processed: {ingestion_results.get('successfully_ingested', 0)}")
        report_lines.append(f"Total Chunks Created: {ingestion_results.get('total_chunks', 0)}")
        report_lines.append("")
        
        # PII Redaction Summary
        report_lines.append("🔒 PII REDACTION SUMMARY")
        report_lines.append("-" * 80)
        total_pii = sum(len(log.redactions_applied) if hasattr(log, 'redactions_applied') else 0 for log in audit_logs)
        report_lines.append(f"Total PII Items Redacted: {total_pii}")
        report_lines.append("")
        
        # Storage Statistics
        report_lines.append("💾 STORAGE STATISTICS")
        report_lines.append("-" * 80)
        
        vector_stats = storage_stats.get('vector_store', {})
        report_lines.append(f"Vector Store: {vector_stats.get('total_chunks', 0)} chunks")
        
        keyword_stats = storage_stats.get('keyword_index', {})
        report_lines.append(f"Keyword Index: {keyword_stats.get('total_chunks', 0)} chunks")
        
        graph_stats = storage_stats.get('knowledge_graph', {})
        report_lines.append(f"Knowledge Graph: {graph_stats.get('total_entities', 0)} entities, {graph_stats.get('total_relationships', 0)} relationships")
        report_lines.append("")
        
        # CRM Matching Statistics
        if crm_stats:
            report_lines.append("🔗 CRM MATCHING STATISTICS")
            report_lines.append("-" * 80)
            report_lines.append(f"Documents with CRM Match: {crm_stats.get('matched_documents', 0)}")
            report_lines.append(f"Match Rate: {crm_stats.get('match_rate', 0):.1f}%")
            report_lines.append("")
        
        # Footer
        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)
        
        # Write to file
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        # Print to console
        print('\n'.join(report_lines))
        
        return report_file
    
    def generate_crm_matching_stats(self, enriched_metadata_list: List[Dict]) -> Dict:
        """Calculate CRM matching statistics."""
        total_docs = len(enriched_metadata_list)
        matched = sum(1 for m in enriched_metadata_list if m.get('crm_id'))
        
        return {
            'matched_documents': matched,
            'unmatched_documents': total_docs - matched,
            'match_rate': (matched / total_docs * 100) if total_docs > 0 else 0
        }
