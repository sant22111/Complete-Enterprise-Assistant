#!/usr/bin/env python3
"""
Simple demo: Edit a document and see hash change.
Shows exactly what happens when you modify content.
"""

from mock_sharepoint.api import MockSharePointAPI
import hashlib

print("\n" + "="*80)
print("SIMPLE DOCUMENT CHANGE DEMO")
print("="*80 + "\n")

# Create a simple test document
test_doc = "This is a proposal for expansion."

print("[ORIGINAL DOCUMENT]")
print("-" * 80)
print(f"Content: {test_doc}")
print(f"Length: {len(test_doc)} characters")

# Compute hash
hash1 = hashlib.sha256(test_doc.encode()).hexdigest()
print(f"Hash: {hash1}")
print()

# Now edit - remove just the period
edited_doc = "This is a proposal for expansion"

print("[EDITED DOCUMENT]")
print("-" * 80)
print(f"Content: {edited_doc}")
print(f"Length: {len(edited_doc)} characters")
print(f"Change: Removed 1 period (.)")

# Compute new hash
hash2 = hashlib.sha256(edited_doc.encode()).hexdigest()
print(f"Hash: {hash2}")
print()

# Compare
print("[HASH COMPARISON]")
print("-" * 80)
print(f"Original hash: {hash1}")
print(f"Edited hash:   {hash2}")
print()

if hash1 == hash2:
    print("❌ Hashes are SAME")
else:
    print("✅ Hashes are COMPLETELY DIFFERENT!")
    print()
    print("Even though only 1 character changed:")
    print(f"  - Original: {len(test_doc)} chars")
    print(f"  - Edited:   {len(edited_doc)} chars")
    print(f"  - Difference: 1 character")
    print()
    print("The entire 64-character hash changed!")

print()
print("[WHAT HAPPENS IN THE SYSTEM]")
print("-" * 80)
print("""
When system detects hash changed:

STEP 1: DELETE old chunks
  ✓ Remove from vector_store
  ✓ Remove from keyword_index  
  ✓ Remove from knowledge_graph
  ✓ Delete all entities
  ✓ Delete all relationships

STEP 2: CREATE new chunks
  ✓ Read modified document
  ✓ Redact PII
  ✓ Split into chunks
  ✓ Add to all 3 storage systems
  ✓ Create new entities/relationships

STEP 3: UPDATE registry
  ✓ Store NEW hash
  ✓ Store NEW timestamp
  ✓ Update chunk count

STEP 4: AUDIT TRAIL
  ✓ Log entry created
  ✓ Shows timestamp of change
  ✓ Complete history maintained
""")

print("="*80)
print("✓ This is how the system detects and handles document changes")
print("="*80)
