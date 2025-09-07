# core/memory/history.py

import json
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from numpy.typing import NDArray

from src.core.memory.memory import MemoryLRU
from src.services import summariser
from src.services.nvidia import nvidia_chat
from src.utils.embeddings import EmbeddingClient
from src.utils.logger import get_logger
from src.utils.rotator import APIKeyRotator

logger = get_logger("RAG", __name__)

# Constants
SIMILARITY_THRESHOLD = 0.15
MAX_TITLE_LENGTH = 50
DEFAULT_TOP_K = 5
RECENT_CONTEXT_SIZE = 3
SEMANTIC_CONTEXT_SIZE = 17

@dataclass
class FileSummary:
	filename: str
	summary: str = ""

def _safe_json(text: str) -> dict[str, Any]:
	"""Safely extract JSON from text that may contain extra content."""
	try:
		return json.loads(text)
	except json.JSONDecodeError:
		# Try to extract JSON object from text
		start = text.find("{")
		end = text.rfind("}")
		if start != -1 and end != -1 and end > start:
			try:
				return json.loads(text[start:end+1])
			except json.JSONDecodeError:
				return {}
		return {}

async def files_relevance(
	question: str,
	file_summaries: Sequence[FileSummary],
	rotator: APIKeyRotator
) -> dict[str, bool]:
	"""Determine which files are relevant to the given question using AI."""
	sys_prompt = "You classify file relevance. Return STRICT JSON only with shape {\"relevance\":[{\"filename\":\"...\",\"relevant\":true|false}]}."
	items = [{"filename": f.filename, "summary": f.summary} for f in file_summaries]
	user_prompt = f"Question: {question}\n\nFiles:\n{json.dumps(items, ensure_ascii=False)}\n\nReturn JSON only."

	try:
		response = await nvidia_chat(sys_prompt, user_prompt, rotator)
		data = _safe_json(response)
		relevance = {}

		for item in data.get("relevance", []):
			filename = item.get("filename")
			is_relevant = item.get("relevant")
			if isinstance(filename, str) and isinstance(is_relevant, bool):
				relevance[filename] = is_relevant

		if not relevance and file_summaries:
			# Fallback: consider all files relevant if parsing fails
			relevance = {f.filename: True for f in file_summaries}

		return relevance

	except Exception as e:
		logger.warning(f"Error determining file relevance: {e}")
		return {f.filename: True for f in file_summaries}

def _cosine_similarity(vec_a: NDArray[np.float32], vec_b: NDArray[np.float32]) -> float:
	"""Calculate cosine similarity between two vectors."""
	denom = (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)) or 1.0
	return float(np.dot(vec_a, vec_b) / denom)

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

def _get_semantic_matches(
	question: str,
	older_summaries: list[str],
	embedder: EmbeddingClient,
	top_k: int = SEMANTIC_CONTEXT_SIZE,
	threshold: float = SIMILARITY_THRESHOLD
) -> str:
	"""Find semantically similar summaries using embedding-based search."""
	if not older_summaries:
		return ""

	query_vector = np.array(embedder.embed([question])[0], dtype="float32")
	summary_vectors = embedder.embed([s.strip() for s in older_summaries])

	similarities = [
		(_cosine_similarity(query_vector, np.array(vec, dtype="float32")), text)
		for vec, text in zip(summary_vectors, older_summaries)
	]

	similarities.sort(key=lambda x: x[0], reverse=True)
	matches = [text for score, text in similarities[:top_k] if score > threshold]

	return "\n\n".join(matches) if matches else ""

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
	semantic_text = _get_semantic_matches(question, older, embedder)

	return recent_prompt, semantic_text

class MedicalHistoryManager:
	"""Manages medical conversation history with enhanced context awareness."""

	def __init__(self, memory: MemoryLRU, embedder: EmbeddingClient):
		self.memory = memory
		self.embedder = embedder

	async def process_medical_exchange(self, user_id: str, session_id: str, question: str, answer: str, gemini_rotator, nvidia_rotator=None) -> str:
		"""
		Process a medical Q&A exchange and store it in memory
		"""
		try:
			summary = await self._generate_summary(question, answer, gemini_rotator, nvidia_rotator)

			# Store in memory
			self.memory.add(user_id, summary)

			# Add to session history
			self.memory.add_message_to_session(session_id, "user", question)
			self.memory.add_message_to_session(session_id, "assistant", answer)

			# Update session title if it's the first message
			self._update_session_if_first_message(session_id, question)

			return summary

		except Exception as e:
			logger.error(f"Error processing medical exchange: {e}")
			# Fallback: store without summary
			summary = f"q: {question}\na: {answer}"
			self.memory.add(user_id, summary)
			self.memory.add_message_to_session(session_id, "user", question)
			self.memory.add_message_to_session(session_id, "assistant", answer)
			return summary

	def _update_session_if_first_message(self, session_id: str, question: str) -> None:
		"""Update session title if this is the first message."""
		session = self.memory.get_session(session_id)
		if session and len(session.messages) == 2:  # Just user + assistant
			title = question[:MAX_TITLE_LENGTH] + ("..." if len(question) > MAX_TITLE_LENGTH else "")
			self.memory.update_session_title(session_id, title)

	def get_conversation_context(self, user_id: str, session_id: str, question: str) -> str:
		"""
		Get relevant conversation context for a new question
		"""
		return self.memory.get_medical_context(user_id, session_id, question)

	def get_user_medical_history(self, user_id: str, limit: int = 10) -> list[str]:
		"""
		Get user's medical history (QA summaries)
		"""
		return self.memory.all(user_id)[-limit:]

	def search_medical_context(
		self,
		user_id: str,
		query: str,
		top_k: int = DEFAULT_TOP_K
	) -> list[str]:
		"""Search through user's medical context for relevant information using embeddings."""
		if not self.embedder:
			return self._fallback_text_search(user_id, query, top_k)

		try:
			return self._semantic_search(user_id, query, top_k)
		except Exception as e:
			logger.error(f"Semantic search failed: {e}")
			return self._fallback_text_search(user_id, query, top_k)

	def _fallback_text_search(
		self,
		user_id: str,
		query: str,
		top_k: int
	) -> list[str]:
		"""Simple text-based search fallback."""
		all_context = self.memory.all(user_id)
		query_lower = query.lower()
		relevant = [ctx for ctx in all_context if query_lower in ctx.lower()]
		return relevant[:top_k]

	def _semantic_search(
		self,
		user_id: str,
		query: str,
		top_k: int
	) -> list[str]:
		"""Semantic search using embeddings."""
		all_context = self.memory.all(user_id)
		if not all_context:
			return []

		query_embedding = np.array(self.embedder.embed([query])[0], dtype="float32")
		context_embeddings = self.embedder.embed(all_context)

		similarities = [
			(_cosine_similarity(query_embedding, np.array(ctx_emb, dtype="float32")), ctx)
			for ctx_emb, ctx in zip(context_embeddings, all_context)
		]

		similarities.sort(key=lambda x: x[0], reverse=True)
		return [ctx for sim, ctx in similarities[:top_k] if sim > SIMILARITY_THRESHOLD]

	async def _generate_summary(
		self,
		question: str,
		answer: str,
		gemini_rotator: APIKeyRotator,
		nvidia_rotator: APIKeyRotator | None = None
	) -> str:
		"""Generate a summary of the Q&A exchange using available AI models."""
		if not gemini_rotator or not gemini_rotator.get_key():
			return f"q: {question}\na: {answer}"

		try:
			summary = await summariser.summarise_qa_with_gemini(
				question, answer, gemini_rotator
			)
			if not summary or not summary.strip():
				if nvidia_rotator and nvidia_rotator.get_key():
					summary = await summariser.summarise_qa_with_nvidia(
						question, answer, nvidia_rotator
					)
			return summary if summary and summary.strip() else f"q: {question}\na: {answer}"

		except Exception as e:
			logger.warning(f"Failed to generate AI summary: {e}")
			return f"q: {question}\na: {answer}"
