# utils/embedding_operations.py

import numpy as np
from numpy.typing import NDArray

from src.config.settings import settings
from src.utils.embeddings import EmbeddingClient
from src.utils.logger import get_logger

logger = get_logger("EMBEDDING_OPERATIONS", __name__)

def cosine_similarity(vec_a: NDArray[np.float32], vec_b: NDArray[np.float32]) -> float:
	"""Calculate cosine similarity between two vectors."""
	denom = (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)) or 1.0
	return float(np.dot(vec_a, vec_b) / denom)

def semantic_search(
	query: str,
	candidates: list[str],
	embedder: EmbeddingClient,
	top_k: int = settings.SEMANTIC_CONTEXT_SIZE,
	threshold: float = settings.SIMILARITY_THRESHOLD
) -> list[str]:
	"""
	Find semantically similar texts using embedding-based search.

	Args:
		query: Search query text
		candidates: List of texts to search through
		embedder: Embedding client for vector generation
		top_k: Maximum number of results to return
		threshold: Minimum similarity score threshold
		join_results: If True, join results with newlines, otherwise return list

	Returns:
		Either list of matching texts or newline-joined string depending on join_results
	"""
	if not candidates:
		return []

	query_vector = np.array(embedder.embed([query])[0], dtype="float32")
	candidate_vectors = embedder.embed([s.strip() for s in candidates])

	similarities = [
		(cosine_similarity(query_vector, np.array(vec, dtype="float32")), text)
		for vec, text in zip(candidate_vectors, candidates)
	]

	similarities.sort(key=lambda x: x[0], reverse=True)
	matches = [text for score, text in similarities[:top_k] if score > threshold]

	return matches
