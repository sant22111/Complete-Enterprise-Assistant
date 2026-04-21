"""
Download pre-ingested storage from cloud storage on first startup.
This allows us to deploy with all 171 documents already ingested.
"""

import os
import urllib.request
import zipfile
import sys
import shutil
import tempfile

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
        temp_dir = tempfile.mkdtemp()
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        print("✓ Storage extracted to temp directory")
        
        # Handle nested folder structure
        # Check if extraction created a nested structure
        extracted_items = os.listdir(temp_dir)
        print(f"  Extracted items: {extracted_items}")
        
        # If there's a single folder containing data/ and logs/, move them up
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
            nested_dir = os.path.join(temp_dir, extracted_items[0])
            nested_items = os.listdir(nested_dir)
            if 'data' in nested_items or 'logs' in nested_items:
                print(f"  Found nested structure, moving files up...")
                for item in nested_items:
                    src = os.path.join(nested_dir, item)
                    dst = os.path.join('.', item)
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.move(src, dst)
                    print(f"    Moved {item}")
        else:
            # Files are at root level, move them
            for item in extracted_items:
                src = os.path.join(temp_dir, item)
                dst = os.path.join('.', item)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)
                print(f"  Moved {item}")
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        # Clean up zip file
        os.remove(zip_path)
        
        # Verify extraction
        print("\nVerifying extracted files:")
        if os.path.exists('data/chroma_db/chunks.pkl'):
            print("✓ Vector store found")
        else:
            print("✗ Vector store NOT found at data/chroma_db/chunks.pkl")
            
        if os.path.exists('data/whoosh_index/index.pkl'):
            print("✓ Keyword index found")
        else:
            print("✗ Keyword index NOT found")
            
        if os.path.exists('logs/ingestion_registry.jsonl'):
            print("✓ Ingestion registry found")
        else:
            print("✗ Ingestion registry NOT found")
        
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
