import os
import json
import pickle
from typing import List, Dict, Optional
from dataclasses import dataclass
import re

@dataclass
class KeywordSearchResult:
    chunk_id: str
    document_id: str
    text: str
    metadata: Dict
    bm25_score: float

class KeywordIndex:
    """
    Lexical search index using BM25-style ranking.
    Enables keyword-based retrieval for exact term matching.
    """
    
    def __init__(self, index_path: str = "./data/whoosh_index"):
        self.index_path = index_path
        os.makedirs(index_path, exist_ok=True)
        self.inverted_index = {}
        self.documents = {}
        self.doc_lengths = {}
        self.avg_doc_length = 0
        self.k1 = 1.5
        self.b = 0.75
        self.load_from_disk()
    
    def clear_index(self):
        """Clear all indexed data."""
        self.inverted_index.clear()
        self.documents.clear()
        self.doc_lengths.clear()
        self.avg_doc_length = 0
    
    def add_chunk(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        metadata: Dict
    ) -> bool:
        """Add a chunk to keyword index."""
        self.documents[chunk_id] = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "text": text,
            "metadata": metadata
        }
        
        tokens = self._tokenize(text)
        self.doc_lengths[chunk_id] = len(tokens)
        
        for token in set(tokens):
            if token not in self.inverted_index:
                self.inverted_index[token] = []
            
            if chunk_id not in [doc_id for doc_id, _ in self.inverted_index[token]]:
                self.inverted_index[token].append((chunk_id, tokens.count(token)))
        
        self._update_avg_doc_length()
        return True
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None
    ) -> List[KeywordSearchResult]:
        """
        Search using BM25 ranking.
        """
        query_tokens = self._tokenize(query)
        scores = {}
        
        for token in query_tokens:
            if token in self.inverted_index:
                idf = self._calculate_idf(token)
                
                for chunk_id, term_freq in self.inverted_index[token]:
                    if chunk_id not in scores:
                        scores[chunk_id] = 0
                    
                    bm25_score = self._calculate_bm25(
                        term_freq,
                        self.doc_lengths.get(chunk_id, 0),
                        idf
                    )
                    scores[chunk_id] += bm25_score
        
        results = []
        for chunk_id, score in scores.items():
            doc_data = self.documents.get(chunk_id)
            if not doc_data:
                continue
            
            if metadata_filter:
                if not self._matches_filter(doc_data.get("metadata", {}), metadata_filter):
                    continue
            
            result = KeywordSearchResult(
                chunk_id=chunk_id,
                document_id=doc_data.get("document_id"),
                text=doc_data.get("text"),
                metadata=doc_data.get("metadata", {}),
                bm25_score=score
            )
            results.append(result)
        
        results.sort(key=lambda x: x.bm25_score, reverse=True)
        return results[:top_k]
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return [t for t in tokens if len(t) > 2]
    
    def _calculate_idf(self, token: str) -> float:
        """Calculate IDF (Inverse Document Frequency)."""
        if token not in self.inverted_index:
            return 0.0
        
        doc_freq = len(self.inverted_index[token])
        total_docs = len(self.documents)
        
        if total_docs == 0:
            return 0.0
        
        return (total_docs - doc_freq + 0.5) / (doc_freq + 0.5)
    
    def _calculate_bm25(self, term_freq: int, doc_length: int, idf: float) -> float:
        """Calculate BM25 score."""
        if self.avg_doc_length == 0:
            return 0.0
        
        numerator = term_freq * (self.k1 + 1)
        denominator = term_freq + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
        
        return idf * (numerator / denominator)
    
    def _update_avg_doc_length(self):
        """Update average document length."""
        if len(self.doc_lengths) == 0:
            self.avg_doc_length = 0
        else:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.doc_lengths)
    
    def _matches_filter(self, metadata: Dict, filter_dict: Dict) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if metadata.get(key) != value:
                return False
        return True
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk from keyword index."""
        if chunk_id in self.documents:
            del self.documents[chunk_id]
        if chunk_id in self.doc_lengths:
            del self.doc_lengths[chunk_id]
        
        for token in list(self.inverted_index.keys()):
            self.inverted_index[token] = [
                (cid, freq) for cid, freq in self.inverted_index[token]
                if cid != chunk_id
            ]
            if not self.inverted_index[token]:
                del self.inverted_index[token]
        
        self._update_avg_doc_length()
        return True
    
    def get_stats(self) -> Dict:
        """Get keyword index statistics."""
        return {
            "total_chunks": len(self.documents),
            "total_unique_tokens": len(self.inverted_index),
            "avg_doc_length": self.avg_doc_length,
            "index_path": self.index_path
        }
    
    def load_from_disk(self):
        """Load index from disk."""
        index_file = f"{self.index_path}/index.pkl"
        if os.path.exists(index_file):
            try:
                with open(index_file, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data.get('documents', {})
                    self.inverted_index = data.get('inverted_index', {})
                    self.doc_lengths = data.get('doc_lengths', {})
                    self.avg_doc_length = data.get('avg_doc_length', 0)
            except:
                self.documents = {}
                self.inverted_index = {}
                self.doc_lengths = {}
                self.avg_doc_length = 0
    
    def save_to_disk(self):
        """Save index to disk."""
        os.makedirs(self.index_path, exist_ok=True)
        with open(f"{self.index_path}/index.pkl", 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'inverted_index': self.inverted_index,
                'doc_lengths': self.doc_lengths,
                'avg_doc_length': self.avg_doc_length
            }, f)
