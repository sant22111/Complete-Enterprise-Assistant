from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from config import retrieval_config
from storage.vector_store import VectorStore, VectorSearchResult
from storage.keyword_index import KeywordIndex, KeywordSearchResult
from storage.knowledge_graph import KnowledgeGraph

@dataclass
class HybridSearchResult:
    chunk_id: str
    document_id: str
    text: str
    metadata: Dict
    vector_score: float
    keyword_score: float
    graph_score: float
    final_score: float
    source_type: str

class HybridRetriever:
    """
    Orchestrates hybrid retrieval across multiple storage systems.
    Combines vector search, keyword search, and graph-based retrieval.
    Uses weighted scoring to rank results.
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        keyword_index: KeywordIndex,
        knowledge_graph: KnowledgeGraph,
        vector_weight: float = retrieval_config.vector_weight,
        keyword_weight: float = retrieval_config.keyword_weight,
        graph_weight: float = retrieval_config.graph_weight
    ):
        self.vector_store = vector_store
        self.keyword_index = keyword_index
        self.knowledge_graph = knowledge_graph
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.graph_weight = graph_weight
    
    def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = retrieval_config.top_k,
        metadata_filter: Optional[Dict] = None
    ) -> Tuple[List[HybridSearchResult], Dict]:
        """
        Perform hybrid retrieval across all storage systems.
        
        Returns:
            - List of ranked results
            - Debug info with retrieval statistics
        """
        debug_info = {
            "vector_results_count": 0,
            "keyword_results_count": 0,
            "graph_hits": 0,
            "selected_chunks": [],
            "rejected_chunks": [],
            "guardrail_flags": []
        }
        
        vector_results = self._vector_search(query_embedding, top_k, metadata_filter)
        debug_info["vector_results_count"] = len(vector_results)
        
        keyword_results = self._keyword_search(query, top_k, metadata_filter)
        debug_info["keyword_results_count"] = len(keyword_results)
        
        graph_results = self._graph_search(query, metadata_filter)
        debug_info["graph_hits"] = len(graph_results)
        
        combined_results = self._combine_results(
            vector_results,
            keyword_results,
            graph_results,
            top_k
        )
        
        debug_info["selected_chunks"] = [r.chunk_id for r in combined_results]
        
        return combined_results, debug_info
    
    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int,
        metadata_filter: Optional[Dict] = None
    ) -> List[VectorSearchResult]:
        """Perform vector similarity search."""
        return self.vector_store.search(query_embedding, top_k, metadata_filter)
    
    def _keyword_search(
        self,
        query: str,
        top_k: int,
        metadata_filter: Optional[Dict] = None
    ) -> List[KeywordSearchResult]:
        """Perform keyword/BM25 search."""
        return self.keyword_index.search(query, top_k, metadata_filter)
    
    def _graph_search(
        self,
        query: str,
        metadata_filter: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """Perform entity/relationship search on knowledge graph."""
        graph_results = []
        
        words = query.split()
        for word in words:
            if len(word) > 3:
                graph_result = self.knowledge_graph.search_by_entity(word)
                if graph_result.related_chunk_ids:
                    for chunk_id in graph_result.related_chunk_ids:
                        graph_results.append((chunk_id, graph_result.relevance_score))
        
        return graph_results
    
    def _combine_results(
        self,
        vector_results: List[VectorSearchResult],
        keyword_results: List[KeywordSearchResult],
        graph_results: List[Tuple[str, float]],
        top_k: int
    ) -> List[HybridSearchResult]:
        """
        Combine results from all retrieval methods using weighted scoring.
        final_score = 0.5*vector + 0.3*keyword + 0.2*graph
        """
        combined = {}
        
        for result in vector_results:
            if result.chunk_id not in combined:
                combined[result.chunk_id] = {
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "text": result.text,
                    "metadata": result.metadata,
                    "vector_score": result.similarity_score,
                    "keyword_score": 0.0,
                    "graph_score": 0.0,
                    "source_type": "vector"
                }
            else:
                combined[result.chunk_id]["vector_score"] = result.similarity_score
        
        for result in keyword_results:
            if result.chunk_id not in combined:
                combined[result.chunk_id] = {
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "text": result.text,
                    "metadata": result.metadata,
                    "vector_score": 0.0,
                    "keyword_score": self._normalize_score(result.bm25_score),
                    "graph_score": 0.0,
                    "source_type": "keyword"
                }
            else:
                combined[result.chunk_id]["keyword_score"] = self._normalize_score(result.bm25_score)
        
        for chunk_id, graph_score in graph_results:
            if chunk_id in combined:
                combined[chunk_id]["graph_score"] = max(combined[chunk_id]["graph_score"], graph_score)
                combined[chunk_id]["source_type"] = "hybrid"
        
        hybrid_results = []
        for chunk_data in combined.values():
            final_score = (
                self.vector_weight * chunk_data["vector_score"] +
                self.keyword_weight * chunk_data["keyword_score"] +
                self.graph_weight * chunk_data["graph_score"]
            )
            
            result = HybridSearchResult(
                chunk_id=chunk_data["chunk_id"],
                document_id=chunk_data["document_id"],
                text=chunk_data["text"],
                metadata=chunk_data["metadata"],
                vector_score=chunk_data["vector_score"],
                keyword_score=chunk_data["keyword_score"],
                graph_score=chunk_data["graph_score"],
                final_score=final_score,
                source_type=chunk_data["source_type"]
            )
            hybrid_results.append(result)
        
        hybrid_results.sort(key=lambda x: x.final_score, reverse=True)
        return hybrid_results[:top_k]
    
    def _normalize_score(self, score: float, max_score: float = 10.0) -> float:
        """Normalize scores to 0-1 range."""
        return min(1.0, score / max_score)
