from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math
import pickle
import os

@dataclass
class VectorSearchResult:
    chunk_id: str
    document_id: str
    text: str
    similarity_score: float
    metadata: Dict

class VectorStore:
    """
    Simulates a vector database (ChromaDB) for semantic search.
    Stores embeddings + chunk text + metadata.
    Persists to disk via pickle.
    """
    
    def __init__(self, db_path: str = "./data/chroma_db"):
        self.db_path = db_path
        self.chunks_store = {}
        self.embeddings_store = {}
        os.makedirs(db_path, exist_ok=True)
        self.load_from_disk()
    
    def add_chunk(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        embedding: List[float],
        metadata: Dict
    ) -> bool:
        """Add a chunk with embedding to vector store."""
        self.chunks_store[chunk_id] = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "text": text,
            "metadata": metadata
        }
        self.embeddings_store[chunk_id] = embedding
        return True
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar chunks using cosine similarity.
        """
        results = []
        
        for chunk_id, embedding in self.embeddings_store.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            
            chunk_data = self.chunks_store.get(chunk_id, {})
            
            if metadata_filter:
                if not self._matches_filter(chunk_data.get("metadata", {}), metadata_filter):
                    continue
            
            result = VectorSearchResult(
                chunk_id=chunk_id,
                document_id=chunk_data.get("document_id"),
                text=chunk_data.get("text"),
                metadata=chunk_data.get("metadata", {}),
                similarity_score=similarity
            )
            results.append(result)
        
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a ** 2 for a in vec1) ** 0.5
        magnitude2 = sum(b ** 2 for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _matches_filter(self, metadata: Dict, filter_dict: Dict) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if metadata.get(key) != value:
                return False
        return True
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """Retrieve a specific chunk."""
        return self.chunks_store.get(chunk_id)
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk from vector store."""
        if chunk_id in self.chunks_store:
            del self.chunks_store[chunk_id]
        if chunk_id in self.embeddings_store:
            del self.embeddings_store[chunk_id]
        return True
    
    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        return {
            "total_chunks": len(self.chunks_store),
            "total_embeddings": len(self.embeddings_store),
            "db_path": self.db_path
        }
    
    def load_from_disk(self):
        """Load chunks and embeddings from disk."""
        chunks_file = f"{self.db_path}/chunks.pkl"
        embeddings_file = f"{self.db_path}/embeddings.pkl"
        
        if os.path.exists(chunks_file):
            try:
                with open(chunks_file, 'rb') as f:
                    self.chunks_store = pickle.load(f)
            except:
                self.chunks_store = {}
        
        if os.path.exists(embeddings_file):
            try:
                with open(embeddings_file, 'rb') as f:
                    self.embeddings_store = pickle.load(f)
            except:
                self.embeddings_store = {}
    
    def save_to_disk(self):
        """Save chunks and embeddings to disk."""
        os.makedirs(self.db_path, exist_ok=True)
        with open(f"{self.db_path}/chunks.pkl", 'wb') as f:
            pickle.dump(self.chunks_store, f)
        with open(f"{self.db_path}/embeddings.pkl", 'wb') as f:
            pickle.dump(self.embeddings_store, f)
