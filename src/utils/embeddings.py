# utils/embeddings.py

import numpy as np
from numpy.typing import NDArray

from src.config.settings import settings
from src.utils.logger import logger


class EmbeddingClient:
	"""A simple embedding client with a fallback mechanism."""

	def __init__(self, model_name: str = "default", dimension: int = 384):
		self.model_name = model_name
		self.dimension = dimension
		self.model = None
		self._fallback_mode = True
		self._init_embedding_model()

	def _init_embedding_model(self):
		"""Initializes the sentence-transformer embedding model."""
		try:
			from sentence_transformers import SentenceTransformer  # type: ignore
			self.model = SentenceTransformer(self.model_name)
			self._fallback_mode = False
			logger().info(f"Successfully loaded embedding model: {self.model_name}")
		except ImportError:
			logger().warning("sentence-transformers not found, using fallback embedding mode.")
		except Exception as e:
			logger().error(f"Error loading embedding model '{self.model_name}': {e}")

	def embed(self, texts: str | list[str]) -> list[list[float]]:
		"""Generates embeddings for the given texts."""
		if isinstance(texts, str):
			texts = [texts]
		return self._fallback_embed(texts) if self._fallback_mode else self._proper_embed(texts)

	def _proper_embed(self, texts: list[str]) -> list[list[float]]:
		"""Generates embeddings using the sentence-transformer model."""
		try:
			embeddings = self.model.encode(texts, convert_to_numpy=True) # type: ignore
			return embeddings.tolist()
		except Exception as e:
			logger().error(f"Error during embedding generation: {e}")
			return self._fallback_embed(texts)

	def _fallback_embed(self, texts: list[str]) -> list[list[float]]:
		"""Generates deterministic, hash-based embeddings as a fallback."""
		embeddings = []
		for text in texts:
			# Create a deterministic hash-based embedding
			text_hash = hash(text) % (2**32)
			np.random.seed(text_hash)
			vector = np.random.normal(0, 1, self.dimension)
			norm = np.linalg.norm(vector)
			if norm > 0:
				vector /= norm
			embeddings.append(vector.tolist())
		return embeddings

	def is_available(self) -> bool:
		"""Checks if the proper embedding model is available."""
		return not self._fallback_mode

	def semantic_search(
		self,
		query: str,
		candidates: list[str],
		top_k: int = settings.SEMANTIC_CONTEXT_SIZE,
		threshold: float = settings.SIMILARITY_THRESHOLD
	) -> list[str]:
		"""Finds semantically similar texts using embedding-based search."""
		if not candidates:
			return []

		query_vector = np.array(self.embed(query)[0], dtype="float32")
		candidate_vectors = self.embed([s.strip() for s in candidates])

		similarities = [
			(self._cosine_similarity(query_vector, np.array(vec, dtype="float32")), text)
			for vec, text in zip(candidate_vectors, candidates)
		]

		similarities.sort(key=lambda x: x[0], reverse=True)
		return [text for score, text in similarities[:top_k] if score > threshold]

	def similarity(self, text1: str, text2: str) -> float:
		"""Calculate cosine similarity between two texts."""
		emb1 = self.embed([text1])[0]
		emb2 = self.embed([text2])[0]

		# Convert to numpy arrays
		emb1_np = np.array(emb1)
		emb2_np = np.array(emb2)

		return self._cosine_similarity(emb1_np, emb2_np)

	def batch_similarity(self, query: str, candidates: list[str]) -> list[float]:
		"""Calculate similarity between a query and multiple candidate texts."""
		query_emb = self.embed([query])[0]
		candidate_embs = self.embed(candidates)

		similarities = []
		query_emb_np = np.array(query_emb)

		for candidate_emb in candidate_embs:
			candidate_emb_np = np.array(candidate_emb)
			similarities.append(self._cosine_similarity(query_emb_np, candidate_emb_np))

		return similarities

	def get_model_info(self) -> dict:
		"""Get information about the current embedding model"""
		return {
			"model_name": self.model_name,
			"dimension": self.dimension,
			"fallback_mode": self._fallback_mode,
			"available": self.is_available()
		}

	@staticmethod
	def _cosine_similarity(vec_a: NDArray[np.float32], vec_b: NDArray[np.float32]) -> float:
		"""Calculates the cosine similarity between two vectors."""
		norm_a = np.linalg.norm(vec_a)
		norm_b = np.linalg.norm(vec_b)
		if norm_a == 0 or norm_b == 0:
			return 0.0
		return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
