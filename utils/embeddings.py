# ────────────────────────────── utils/embeddings.py ──────────────────────────────
import numpy as np
from typing import List, Union
import logging

from .logger import get_logger

logger = get_logger("EMBEDDINGS", __name__)

class EmbeddingClient:
    """
    Simple embedding client that provides fallback functionality
    when proper embedding models are not available
    """
    
    def __init__(self, model_name: str = "default", dimension: int = 384):
        self.model_name = model_name
        self.dimension = dimension
        self._fallback_mode = True
        
        # Try to initialize proper embedding model
        try:
            self._init_embedding_model()
        except Exception as e:
            logger.warning(f"Could not initialize embedding model {model_name}: {e}")
            logger.info("Using fallback embedding mode")
            self._fallback_mode = True
    
    def _init_embedding_model(self):
        """Initialize the actual embedding model"""
        try:
            # Try to import sentence transformers
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self._fallback_mode = False
            logger.info(f"Successfully loaded embedding model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, using fallback mode")
            self._fallback_mode = True
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self._fallback_mode = True
    
    def embed(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Generate embeddings for the given texts
        
        Args:
            texts: Single text string or list of text strings
            
        Returns:
            List of embedding vectors
        """
        if isinstance(texts, str):
            texts = [texts]
        
        if self._fallback_mode:
            return self._fallback_embed(texts)
        else:
            return self._proper_embed(texts)
    
    def _proper_embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using the proper model"""
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            # Convert to list of lists for consistency
            if len(texts) == 1:
                return [embeddings.tolist()]
            else:
                return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error in proper embedding: {e}")
            return self._fallback_embed(texts)
    
    def _fallback_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Fallback embedding using simple hash-based approach
        This is not semantically meaningful but provides consistent dimensionality
        """
        embeddings = []
        
        for text in texts:
            # Create a deterministic hash-based embedding
            text_hash = hash(text) % (2**32)
            np.random.seed(text_hash)
            
            # Generate random vector with fixed dimension
            embedding = np.random.normal(0, 1, self.dimension)
            # Normalize to unit length
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            embeddings.append(embedding.tolist())
        
        return embeddings
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        emb1 = self.embed([text1])[0]
        emb2 = self.embed([text2])[0]
        
        # Convert to numpy arrays
        emb1_np = np.array(emb1)
        emb2_np = np.array(emb2)
        
        # Calculate cosine similarity
        dot_product = np.dot(emb1_np, emb2_np)
        norm1 = np.linalg.norm(emb1_np)
        norm2 = np.linalg.norm(emb2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def batch_similarity(self, query: str, candidates: List[str]) -> List[float]:
        """
        Calculate similarity between a query and multiple candidate texts
        
        Args:
            query: Query text
            candidates: List of candidate texts
            
        Returns:
            List of similarity scores
        """
        query_emb = self.embed([query])[0]
        candidate_embs = self.embed(candidates)
        
        similarities = []
        query_emb_np = np.array(query_emb)
        
        for candidate_emb in candidate_embs:
            candidate_emb_np = np.array(candidate_emb)
            
            dot_product = np.dot(query_emb_np, candidate_emb_np)
            norm1 = np.linalg.norm(query_emb_np)
            norm2 = np.linalg.norm(candidate_emb_np)
            
            if norm1 == 0 or norm2 == 0:
                similarities.append(0.0)
            else:
                similarities.append(float(dot_product / (norm1 * norm2)))
        
        return similarities
    
    def is_available(self) -> bool:
        """Check if proper embedding model is available"""
        return not self._fallback_mode
    
    def get_model_info(self) -> dict:
        """Get information about the current embedding model"""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "fallback_mode": self._fallback_mode,
            "available": self.is_available()
        }

# Convenience function for creating embedding client
def create_embedding_client(model_name: str = "default", dimension: int = 384) -> EmbeddingClient:
    """
    Create an embedding client with the specified parameters
    
    Args:
        model_name: Name of the embedding model
        dimension: Dimension of the embedding vectors
        
    Returns:
        EmbeddingClient instance
    """
    return EmbeddingClient(model_name, dimension)