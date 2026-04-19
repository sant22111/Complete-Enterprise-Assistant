#!/usr/bin/env python3
"""
Check if chunks are in storage systems.
"""

from storage.vector_store import VectorStore
from storage.keyword_index import KeywordIndex
from storage.knowledge_graph import KnowledgeGraph
from config import storage_config

print("\n" + "="*80)
print("CHECKING STORAGE SYSTEMS")
print("="*80 + "\n")

vector_store = VectorStore(storage_config.chroma_db_path)
keyword_index = KeywordIndex(storage_config.whoosh_index_path)
knowledge_graph = KnowledgeGraph()

print("[Vector Store]")
print(f"  Total chunks: {vector_store.get_stats()['total_chunks']}")
print(f"  Total embeddings: {vector_store.get_stats()['total_embeddings']}")

print("\n[Keyword Index]")
print(f"  Total chunks: {keyword_index.get_stats()['total_chunks']}")
print(f"  Total tokens: {keyword_index.get_stats()['total_unique_tokens']}")

print("\n[Knowledge Graph]")
print(f"  Total entities: {knowledge_graph.get_stats()['total_entities']}")
print(f"  Total relationships: {knowledge_graph.get_stats()['total_relationships']}")

if vector_store.get_stats()['total_chunks'] == 0:
    print("\n❌ No chunks in storage! Need to ingest documents first.")
else:
    print("\n✓ Chunks are in storage. Retrieval should work.")
