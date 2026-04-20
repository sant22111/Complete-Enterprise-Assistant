"""
Download pre-ingested storage from cloud storage on first startup.
This allows us to deploy with all 171 documents already ingested.
"""

import os
import urllib.request
import zipfile
import sys

# URL to your storage backup (you'll need to replace this)
STORAGE_URL = os.getenv('STORAGE_BACKUP_URL', '')

def download_and_extract_storage():
    """Download storage backup and extract if not already present."""
    
    # Check if storage already exists
    if os.path.exists('data/chroma_db/chunks.pkl') and os.path.exists('logs/ingestion_registry.jsonl'):
        print("✓ Storage already exists, skipping download")
        return True
    
    if not STORAGE_URL:
        print("⚠️  No STORAGE_BACKUP_URL set, skipping storage download")
        print("   Set STORAGE_BACKUP_URL environment variable with direct download link")
        return False
    
    print("=" * 80)
    print("DOWNLOADING PRE-INGESTED STORAGE")
    print("=" * 80)
    
    try:
        # Download the zip file
        print(f"Downloading from: {STORAGE_URL[:50]}...")
        zip_path = 'storage_backup.zip'
        
        urllib.request.urlretrieve(STORAGE_URL, zip_path)
        file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"✓ Downloaded {file_size_mb:.2f} MB")
        
        # Extract the zip file
        print("Extracting storage files...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall('.')
        
        print("✓ Storage extracted successfully")
        
        # Clean up zip file
        os.remove(zip_path)
        
        # Verify extraction
        if os.path.exists('data/chroma_db/chunks.pkl'):
            print("✓ Vector store found")
        if os.path.exists('data/whoosh_index/index.pkl'):
            print("✓ Keyword index found")
        if os.path.exists('logs/ingestion_registry.jsonl'):
            print("✓ Ingestion registry found")
        
        print("=" * 80)
        print("✅ STORAGE READY - 171 documents pre-ingested!")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"❌ Failed to download/extract storage: {e}")
        print("   Server will start without pre-ingested data")
        return False

if __name__ == "__main__":
    download_and_extract_storage()
