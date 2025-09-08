# utils/context_utils.py

import json

from src.core.memory import MemoryLRU
from src.utils.embedding_operations import semantic_search
from src.utils.embeddings import EmbeddingClient
from src.utils.logger import get_logger

logger = get_logger("CONTEXT_UTILS", __name__)

RECENT_CONTEXT_SIZE = 3

async def _get_recent_related_text(
	question: str,
	recent_summaries: list[str]
) -> str:
	"""Get text from recent summaries that directly relate to the question."""
	if not recent_summaries:
		return ""

	sys_prompt = (
		"Pick only items that directly relate to the new question. "
		"Output the selected items verbatim, no commentary. "
		"If none, output nothing."
	)

	numbered_items = [
		{"id": i+1, "text": summary}
		for i, summary in enumerate(recent_summaries)
	]

	user_prompt = (
		f"Question: {question}\n"
		f"Candidates:\n{json.dumps(numbered_items, ensure_ascii=False)}\n"
		"Select any related items and output ONLY their 'text' lines concatenated."
	)

	return user_prompt  # Note: actual NVIDIA call handled by caller

async def related_recent_and_semantic_context(
	user_id: str,
	question: str,
	memory: MemoryLRU,
	embedder: EmbeddingClient,
	recent_size: int = RECENT_CONTEXT_SIZE
) -> tuple[str, str]:
	"""
	Get context from both recent and older summaries.

	Args:
		user_id: User identifier
		question: Current question
		memory: Memory system instance
		embedder: Embedding client for semantic search
		recent_size: Number of recent summaries to check

	Returns:
		tuple[str, str]: (recent_related_text, semantic_related_text)
		- recent_related_text: Empty string (to be filled by caller using NVIDIA)
		- semantic_related_text: Semantically related older summaries
	"""
	recent = memory.recent(user_id, recent_size)
	older = memory.rest(user_id, recent_size)

	recent_prompt = await _get_recent_related_text(question, recent)
	semantic_text = semantic_search(question, older, embedder)

	return recent_prompt, "\n\n".join(semantic_text)
