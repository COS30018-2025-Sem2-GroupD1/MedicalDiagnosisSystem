# utils/context_utils.py

import json

from src.core.memory import MemoryLRU
from src.utils.embeddings import EmbeddingClient

RECENT_CONTEXT_SIZE = 3

async def _get_recent_related_prompt(
	question: str,
	recent_summaries: list[str]
) -> str:
	"""Creates a prompt to select relevant text from recent summaries."""
	if not recent_summaries:
		return ""

	numbered_items = [
		{"id": i + 1, "text": summary}
		for i, summary in enumerate(recent_summaries)
	]

	return (
		f"Question: {question}\n"
		f"Candidates:\n{json.dumps(numbered_items, ensure_ascii=False)}\n"
		"Select any related items and output ONLY their 'text' lines concatenated."
	)

async def related_recent_and_semantic_context(
	user_id: str,
	question: str,
	memory: MemoryLRU,
	embedder: EmbeddingClient,
	recent_size: int = RECENT_CONTEXT_SIZE
) -> tuple[str, str]:
	"""
	Gathers context from recent and older summaries.

	Returns a tuple containing:
	- A prompt for an LLM to extract recent related text.
	- A string of semantically related older text.
	"""
	recent = memory.recent(user_id, recent_size)
	older = memory.rest(user_id, recent_size)

	recent_prompt = await _get_recent_related_prompt(question, recent)
	semantic_text_list = embedder.semantic_search(question, older)

	return recent_prompt, "\n\n".join(semantic_text_list)
