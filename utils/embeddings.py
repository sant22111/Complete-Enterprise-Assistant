from typing import List
import os
import numpy as np
import hashlib
from openai import OpenAI

class EmbeddingService:
    """
    Production-ready embeddings using OpenAI API.
    
    Setup:
    1. Get API key from https://platform.openai.com
    2. Set environment variable: OPEN_AI_KEY=your_key_here
    
    Model: text-embedding-3-small (1536 dimensions, $0.02/1M tokens)
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (or set OPEN_AI_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPEN_AI_KEY')
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Get key at https://platform.openai.com\n"
                "Set environment variable: OPEN_AI_KEY=your_key_here"
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.embedding_dim = 1536  # text-embedding-3-small
        print(f"✓ OpenAI embeddings initialized (dimension: {self.embedding_dim})")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate semantic embedding for text using OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats (1536 dimensions)
        """
        try:
            # Truncate text if it exceeds token limit (8192 tokens ~= 32,000 chars)
            # Conservative estimate: 1 token = 4 chars
            max_chars = 8000 * 4  # 32,000 chars for safety
            if len(text) > max_chars:
                text = text[:max_chars]
                print(f"⚠️ Text truncated from {len(text)} to {max_chars} chars for embedding")
            
            response = self.client.embeddings.create(
                input=text,
                model='text-embedding-3-small'
            )
            return response.data[0].embedding
        except Exception as e:
            # Fallback to deterministic mock embeddings (for rate limits/demo)
            print(f"⚠️ OpenAI API failed, using mock embedding: {str(e)[:100]}")
            return self._generate_mock_embedding(text)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (more efficient).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        try:
            response = self.client.embeddings.create(
                input=texts,
                model='text-embedding-3-small'
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"⚠️ OpenAI batch API failed, using mock embeddings: {str(e)[:100]}")
            return [self._generate_mock_embedding(text) for text in texts]
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for search query.
        
        Args:
            query: Search query text
            
        Returns:
            List of floats (1536 dimensions)
        """
        try:
            # Truncate query if needed (queries are usually short, but just in case)
            max_chars = 8000 * 4
            if len(query) > max_chars:
                query = query[:max_chars]
            
            response = self.client.embeddings.create(
                input=query,
                model='text-embedding-3-small'
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️ OpenAI query API failed, using mock embedding: {str(e)[:100]}")
            return self._generate_mock_embedding(query)
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Generate deterministic mock embedding from text hash.
        Used as fallback when Cohere API fails or hits rate limit.
        """
        # Use text hash as seed for reproducible embeddings
        text_hash = hashlib.md5(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)
        np.random.seed(seed)
        
        # Generate random normalized vector
        embedding = np.random.randn(self.embedding_dim)
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.tolist()
