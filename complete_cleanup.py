"""
Complete Cleanup Script
Clears ALL data: storage, logs, reports, registry
Use this for a fresh start
"""

import os
import shutil

def complete_cleanup():
    """Clear all system data for fresh start."""
    
    print("=" * 80)
    print("🧹 COMPLETE SYSTEM CLEANUP")
    print("=" * 80)
    print()
    
    items_cleaned = []
    
    # 1. Clear Vector Store
    if os.path.exists('data/chroma_db'):
        try:
            shutil.rmtree('data/chroma_db')
            os.makedirs('data/chroma_db', exist_ok=True)
            items_cleaned.append("✓ Vector Store (ChromaDB)")
        except Exception as e:
            print(f"⚠️ Warning: Could not clear vector store: {e}")
    
    # 2. Clear Keyword Index
    if os.path.exists('data/whoosh_index'):
        try:
            shutil.rmtree('data/whoosh_index')
            os.makedirs('data/whoosh_index', exist_ok=True)
            items_cleaned.append("✓ Keyword Index (Whoosh)")
        except Exception as e:
            print(f"⚠️ Warning: Could not clear keyword index: {e}")
    
    # 3. Clear Knowledge Graph
    if os.path.exists('data/graph_data'):
        try:
            shutil.rmtree('data/graph_data')
            os.makedirs('data/graph_data', exist_ok=True)
            items_cleaned.append("✓ Knowledge Graph")
        except Exception as e:
            print(f"⚠️ Warning: Could not clear knowledge graph: {e}")
    
    # 4. Clear Audit Logs
    if os.path.exists('logs/audit_logs.jsonl'):
        try:
            os.remove('logs/audit_logs.jsonl')
            items_cleaned.append("✓ Audit Logs")
        except Exception as e:
            print(f"⚠️ Warning: Could not clear audit logs: {e}")
    
    # 5. Clear Ingestion Registry
    if os.path.exists('logs/ingestion_registry.jsonl'):
        try:
            os.remove('logs/ingestion_registry.jsonl')
            items_cleaned.append("✓ Ingestion Registry")
        except Exception as e:
            print(f"⚠️ Warning: Could not clear ingestion registry: {e}")
    
    # 6. Clear Reports
    if os.path.exists('reports'):
        try:
            report_files = [f for f in os.listdir('reports') if f.startswith('ingestion_report_')]
            for report_file in report_files:
                os.remove(os.path.join('reports', report_file))
            if report_files:
                items_cleaned.append(f"✓ Reports ({len(report_files)} files)")
        except Exception as e:
            print(f"⚠️ Warning: Could not clear reports: {e}")
    
    # Print summary
    print("Cleaned Items:")
    for item in items_cleaned:
        print(f"  {item}")
    
    print()
    print("=" * 80)
    print("✅ CLEANUP COMPLETE")
    print("=" * 80)
    print()
    print("📝 Note: Sample documents in 'sample_documents/' were NOT deleted")
    print("🚀 You can now restart the server for fresh ingestion")
    print()

if __name__ == "__main__":
    response = input("⚠️  This will delete ALL data (storage, logs, reports). Continue? (yes/no): ")
    if response.lower() == 'yes':
        complete_cleanup()
    else:
        print("Cleanup cancelled.")
