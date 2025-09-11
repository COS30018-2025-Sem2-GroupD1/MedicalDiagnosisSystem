# utils/embedding_operations.py

import numpy as np
from numpy.typing import NDArray

from src.config.settings import settings
from src.utils.embeddings import EmbeddingClient


def cosine_similarity(vec_a: NDArray[np.float32], vec_b: NDArray[np.float32]) -> float:
	"""Calculates the cosine similarity between two vectors."""
	denom = (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)) or 1.0
	return float(np.dot(vec_a, vec_b) / denom)

def semantic_search(
	query: str,
	candidates: list[str],
	embedder: EmbeddingClient,
	top_k: int = settings.SEMANTIC_CONTEXT_SIZE,
	threshold: float = settings.SIMILARITY_THRESHOLD
) -> list[str]:
	"""Finds semantically similar texts using embedding-based search."""
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
