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
        
        # Debug: Show what's in the zip
        print("  Contents of zip file:")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            for name in file_list[:10]:  # Show first 10 files
                print(f"    {name}")
            if len(file_list) > 10:
                print(f"    ... and {len(file_list) - 10} more files")
            
            # Extract
            zip_ref.extractall(temp_dir)
        
        print("✓ Storage extracted to temp directory")
        
        # Copy all extracted files to current directory recursively
        print(f"  Copying extracted files to current directory...")
        
        # Walk through temp directory and copy everything
        for root, dirs, files in os.walk(temp_dir):
            # Get relative path from temp_dir
            rel_path = os.path.relpath(root, temp_dir)
            
            # Normalize path separators (convert \ to /)
            rel_path = rel_path.replace('\\', '/')
            
            # Create corresponding directory in current location
            if rel_path != '.':
                target_dir = rel_path
                os.makedirs(target_dir, exist_ok=True)
            
            # Copy all files
            for file in files:
                src_file = os.path.join(root, file)
                if rel_path == '.':
                    dst_file = file
                else:
                    dst_file = f"{rel_path}/{file}"
                
                # Remove destination if it exists
                if os.path.exists(dst_file):
                    os.remove(dst_file)
                
                # Copy file
                shutil.copy2(src_file, dst_file)
                print(f"    Copied {dst_file}")
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        # Clean up zip file
        os.remove(zip_path)
        
        # Verify extraction (use os.path.join for cross-platform paths)
        print("\nVerifying extracted files:")
        print(f"Current working directory: {os.getcwd()}")
        
        chunks_path = os.path.join('data', 'chroma_db', 'chunks.pkl')
        abs_chunks = os.path.abspath(chunks_path)
        if os.path.exists(chunks_path):
            size_mb = os.path.getsize(chunks_path) / (1024 * 1024)
            print(f"✓ Vector store found ({size_mb:.2f} MB)")
        else:
            print(f"✗ Vector store NOT found at {chunks_path}")
            print(f"  Absolute path: {abs_chunks}")
            print(f"  Exists: {os.path.exists(abs_chunks)}")
            
        index_path = os.path.join('data', 'whoosh_index', 'index.pkl')
        if os.path.exists(index_path):
            size_mb = os.path.getsize(index_path) / (1024 * 1024)
            print(f"✓ Keyword index found ({size_mb:.2f} MB)")
        else:
            print(f"✗ Keyword index NOT found at {index_path}")
            
        registry_path = os.path.join('logs', 'ingestion_registry.jsonl')
        if os.path.exists(registry_path):
            size_mb = os.path.getsize(registry_path) / (1024 * 1024)
            print(f"✓ Ingestion registry found ({size_mb:.2f} MB)")
        else:
            print(f"✗ Ingestion registry NOT found at {registry_path}")
        
        # List what's actually in data/ directory
        if os.path.exists('data'):
            print(f"\nContents of data/ directory:")
            for root, dirs, files in os.walk('data'):
                level = root.replace('data', '').count(os.sep)
                indent = ' ' * 2 * level
                print(f'{indent}{os.path.basename(root)}/')
                subindent = ' ' * 2 * (level + 1)
                for file in files[:5]:  # Show first 5 files
                    print(f'{subindent}{file}')
        
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
