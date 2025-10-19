# src/utils/embeddings.py

import numpy as np
import torch
import torch.nn.functional as F
from numpy.typing import NDArray
from transformers import (AutoModel, AutoTokenizer, PreTrainedModel,
                          PreTrainedTokenizer)

from src.config.settings import settings
from src.utils.logger import logger


class EmbeddingClient:
	"""
	An embedding client that generates vector embeddings for text using a
	transformer model, mirroring the logic used for knowledge base creation.
	"""

	def __init__(self, model_name: str):
		self.model_name = model_name
		self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
		self.tokenizer: PreTrainedTokenizer | None = None
		self.model: PreTrainedModel | None = None
		self.dimension: int | None = None
		self._available = self._init_embedding_model()

	def _init_embedding_model(self) -> bool:
		"""Initializes the transformer model and tokenizer."""
		try:
			logger().info(f"Loading embedding model '{self.model_name}' on {self.device}")
			self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
			self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
			self.model.eval()

			# Dynamically determine the embedding dimension
			self.dimension = self._get_embedding_dimension()
			logger().info(f"Successfully loaded model. Embedding dimension: {self.dimension}")
			return True
		except Exception as e:
			logger().error(f"Failed to load embedding model '{self.model_name}': {e}")
			return False

	def _get_embedding_dimension(self) -> int:
		"""Runs a test input to determine the model's output dimension."""
		if not self.tokenizer or not self.model:
			raise RuntimeError("Model and tokenizer must be initialized.")

		test_input = self.tokenizer(
			"test", return_tensors="pt", truncation=True, padding=True
		).to(self.device)

		with torch.no_grad():
			test_output = self.model(**test_input)
			test_embedding = self._mean_pooling(
				test_output.last_hidden_state, test_input["attention_mask"]
			)
		return test_embedding.shape[1]

	def _mean_pooling(
		self, token_embeddings: torch.Tensor, attention_mask: torch.Tensor
	) -> torch.Tensor:
		"""Performs mean pooling on token embeddings using an attention mask."""
		input_mask_expanded = (
			attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
		)
		masked_embeddings = token_embeddings * input_mask_expanded
		summed_embeddings = torch.sum(masked_embeddings, 1)
		summed_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
		return summed_embeddings / summed_mask

	def embed(self, texts: str | list[str], batch_size: int = 64) -> list[list[float]]:
		"""
		Generates normalized, mean-pooled embeddings for the given texts.
		Returns an empty list if the model is not available or an error occurs.
		"""
		if not self.is_available() or not self.tokenizer or not self.model:
			logger().error("Embedding model is not available, cannot generate embeddings.")
			return [[] for _ in range(len(texts) if isinstance(texts, list) else 1)]

		if isinstance(texts, str):
			texts = [texts]

		all_embeddings = []
		for i in range(0, len(texts), batch_size):
			batch_texts = texts[i : i + batch_size]
			try:
				inputs = self.tokenizer(
					batch_texts,
					truncation=True,
					padding=True,
					max_length=512,
					return_tensors="pt",
				).to(self.device)

				with torch.no_grad():
					outputs = self.model(**outputs)

				attention_mask = inputs["attention_mask"]
				chunk_embeddings = self._mean_pooling(
					outputs.last_hidden_state, attention_mask
				)

				# L2 Normalization - CRITICAL STEP FOR COMPATIBILITY
				normalized_embeddings = F.normalize(chunk_embeddings, p=2, dim=1)

				all_embeddings.extend(normalized_embeddings.cpu().numpy().tolist())

			except Exception as e:
				logger().error(f"Error during embedding generation for a batch: {e}")
				# Add empty embeddings for the failed batch
				all_embeddings.extend([[] for _ in batch_texts])

		return all_embeddings

	def is_available(self) -> bool:
		"""Checks if the embedding model was loaded successfully."""
		return self._available

	def semantic_search(
		self,
		query: str,
		candidates: list[str],
		top_k: int = settings.SEMANTIC_CONTEXT_SIZE,
		threshold: float = settings.SIMILARITY_THRESHOLD,
	) -> list[str]:
		"""Finds semantically similar texts using embedding-based search."""
		if not self.is_available() or not candidates:
			return []

		query_vector = np.array(self.embed(query)[0], dtype="float32")
		if query_vector.size == 0:
			return []

		candidate_vectors = self.embed(candidates)

		similarities = [
			(
				self._cosine_similarity(query_vector, np.array(vec, dtype="float32")),
				text,
			)
			for vec, text in zip(candidate_vectors, candidates) if vec
		]

		similarities.sort(key=lambda x: x[0], reverse=True)
		return [text for score, text in similarities[:top_k] if score > threshold]

	def get_model_info(self) -> dict:
		"""Get information about the current embedding model."""
		return {
			"model_name": self.model_name,
			"dimension": self.dimension,
			"device": str(self.device),
			"available": self.is_available(),
		}

	@staticmethod
	def _cosine_similarity(
		vec_a: NDArray[np.float32], vec_b: NDArray[np.float32]
	) -> float:
		"""Calculates the cosine similarity between two vectors."""
		norm_a = np.linalg.norm(vec_a)
		norm_b = np.linalg.norm(vec_b)
		if norm_a == 0 or norm_b == 0:
			return 0.0
		return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
