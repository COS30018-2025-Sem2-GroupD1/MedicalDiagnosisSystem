# core/history.py

from src.config.settings import settings
from src.core.memory import MemoryLRU
from src.services import summariser
from src.utils.embedding_operations import semantic_search
from src.utils.embeddings import EmbeddingClient
from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator


class MedicalHistoryManager:
	"""Manages medical conversation history with enhanced context awareness."""

	def __init__(self, memory: MemoryLRU, embedder: EmbeddingClient):
		self.memory = memory
		self.embedder = embedder

	async def process_medical_exchange(
		self,
		user_id: str,
		session_id: str,
		question: str,
		answer: str,
		gemini_rotator,
		nvidia_rotator
	) -> str:
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
			logger().error(f"Error processing medical exchange: {e}")
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
			title = question[:settings.MAX_TITLE_LENGTH] + ("..." if len(question) > settings.MAX_TITLE_LENGTH else "")
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
		top_k: int = settings.DEFAULT_TOP_K
	) -> list[str]:
		"""Search through user's medical context for relevant information using embeddings."""
		if not self.embedder:
			return self._fallback_text_search(user_id, query, top_k)

		try:
			all_context = self.memory.all(user_id)
			if not all_context:
				return []
			return semantic_search(query, all_context, self.embedder, top_k)
		except Exception as e:
			logger().error(f"Semantic search failed: {e}")
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

	async def _generate_summary(
		self,
		question: str,
		answer: str,
		gemini_rotator: APIKeyRotator,
		nvidia_rotator: APIKeyRotator
	) -> str:
		"""Generate a summary of the Q&A exchange using available AI models."""
		if not gemini_rotator or not gemini_rotator.get_key():
			return f"q: {question}\na: {answer}"

		try:
			summary = await summariser.summarise_qa_with_gemini(
				question, answer, gemini_rotator
			)
			if not summary or not summary.strip():
				if nvidia_rotator.get_key():
					summary = await summariser.summarise_qa_with_nvidia(
						question, answer, nvidia_rotator
					)
			return summary if summary and summary.strip() else f"q: {question}\na: {answer}"

		except Exception as e:
			logger().warning(f"Failed to generate AI summary: {e}")
			return f"q: {question}\na: {answer}"
