# src/services/reranker.py

from src.config.settings import settings
from src.models.information import InfoChunk
from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator, robust_post_json


async def rerank_documents(
	query: str,
	documents: list[InfoChunk],
	rotator: APIKeyRotator,
	top_k: int = 3,
) -> list[InfoChunk]:
	"""
	Reranks a list of documents based on a query using the NVIDIA Rerank API.

	Args:
		query: The user's query string.
		documents: A list of InfoChunk objects retrieved from the initial search.
		rotator: The API key rotator for NVIDIA services.
		top_k: The final number of documents to return after reranking.

	Returns:
		A sorted list of the top_k most relevant InfoChunk objects.
		Returns the original list sliced to top_k if reranking fails.
	"""
	if not documents:
		return []

	headers = {
		"Authorization": f"Bearer {rotator.get_key() or ''}",
		"Accept": "application/json",
		"Content-Type": "application/json",
	}

	passages = [doc.content for doc in documents]

	payload = {
		"model": settings.NVIDIA_RERANKER_MODEL,
		"query": query,
		"passages": passages,
		"top_n": top_k,
	}

	try:
		# Use the existing robust helper for consistency
		data = await robust_post_json(settings.NVIDIA_RERANKER_ENDPOINT, headers, payload, rotator)
		results = data.get("results", [])

		if not results:
			logger().warning("Reranking returned no results, falling back to original order.")
			return documents[:top_k]

		# Create a mapping of original document content to the document object
		doc_map = {doc.content: doc for doc in documents}

		# Reconstruct the sorted list of documents based on rerank results
		reranked_docs = []
		for result in sorted(results, key=lambda x: x["rank"]):
			if result["passage"] in doc_map:
				reranked_docs.append(doc_map[result["passage"]])

		return reranked_docs

	except Exception as e:
		logger().error(f"An unexpected error occurred during reranking: {e}")

	# Fallback: return the top_k documents from the original list
	return documents[:top_k]
