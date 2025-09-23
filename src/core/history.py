# core/history.py

from datetime import datetime, timezone

from src.config.settings import settings
from src.core.memory import MemoryLRU
from src.data.repositories.medical import (get_recent_memory_summaries,
                                           save_memory_summary,
                                           search_memory_summaries_semantic)
from src.data.repositories.message import save_chat_message
from src.data.repositories.session import ensure_session
from src.services import summariser
from src.services.nvidia import nvidia_chat
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
		gemini_rotator: APIKeyRotator,
		nvidia_rotator: APIKeyRotator,
		*,
		patient_id: str | None = None,
		doctor_id: str | None = None,
		session_title: str | None = None
	) -> str:
		"""Processes and stores a medical Q&A exchange, returning a summary."""
		try:
			summary = await self._generate_summary(question, answer, gemini_rotator, nvidia_rotator)

			# Cache under patient_id when available
			cache_key = patient_id or user_id
			self.memory.add(cache_key, summary)

			# Add to session history
			self.memory.add_message_to_session(session_id, "user", question)
			self.memory.add_message_to_session(session_id, "assistant", answer)

			# Persist to MongoDB with patient/doctor context
			if patient_id and doctor_id:
				ensure_session(
					session_id=session_id,
					patient_id=patient_id,
					doctor_id=doctor_id,
					title=session_title or "New Chat",
					last_activity=datetime.now(timezone.utc)
				)
				save_chat_message(
					session_id=session_id,
					patient_id=patient_id,
					doctor_id=doctor_id,
					role="user",
					content=question
				)
				save_chat_message(
					session_id=session_id,
					patient_id=patient_id,
					doctor_id=doctor_id,
					role="assistant",
					content=answer
				)

				# Generate embedding for semantic search
				embedding = None
				if self.embedder:
					try:
						embedding = self.embedder.embed([summary])[0]
					except Exception as e:
						logger().warning(f"Failed to generate embedding for summary: {e}")

				save_memory_summary(
					patient_id=patient_id,
					doctor_id=doctor_id,
					summary=summary,
					embedding=embedding
				)

			await self._update_session_if_first_message(
				session_id,
				question,
				nvidia_rotator,
				patient_id,
				doctor_id
			)
			return summary

		except Exception as e:
			logger().error(f"Error processing medical exchange: {e}")
			summary = f"q: {question}\na: {answer}"
			cache_key = patient_id or user_id
			self.memory.add(cache_key, summary)
			self.memory.add_message_to_session(session_id, "user", question)
			self.memory.add_message_to_session(session_id, "assistant", answer)
			return summary

	async def _update_session_if_first_message(
		self,
		session_id: str,
		question: str,
		nvidia_rotator: APIKeyRotator,
		patient_id: str | None = None,
		doctor_id: str | None = None
	) -> None:
		"""Updates the session title if it's the first message."""
		session = self.memory.get_session(session_id)
		if session and len(session.messages) == 2:  # Just user + assistant
			try:
				title = await summariser.summarise_title_with_nvidia(question, nvidia_rotator, max_words=5)
				if not title or title.strip() == "":
					title = question[:settings.MAX_TITLE_LENGTH] + ("..." if len(question) > settings.MAX_TITLE_LENGTH else "")
			except Exception as e:
				logger().warning(f"Failed to generate title with NVIDIA: {e}")
				title = question[:settings.MAX_TITLE_LENGTH] + ("..." if len(question) > settings.MAX_TITLE_LENGTH else "")

			self.memory.update_session_title(session_id, title)

			# TODO Verify this isn't redundant
			if patient_id and doctor_id:
				ensure_session(
					session_id=session_id,
					patient_id=patient_id,
					doctor_id=doctor_id,
					title=title,
					last_activity=datetime.now(timezone.utc)
				)

	# NOTE Likely depreciated
	def get_conversation_context(
		self,
		user_id: str
	) -> str:
		"""Retrieves relevant conversation context for a new question."""
		#get_recent_memory_summaries()
		return self.memory.get_medical_context(user_id=user_id)

	async def get_enhanced_conversation_context(
		self,
		user_id: str,
		session_id: str,
		question: str,
		nvidia_rotator: APIKeyRotator,
		*,
		patient_id: str | None = None
	) -> str:
		"""Enhanced context retrieval combining STM (3) + LTM semantic search (2) with NVIDIA reasoning."""
		cache_key = patient_id or user_id

		# Get STM summaries (recent 3)
		recent_qa = self.memory.recent(cache_key, 3)

		# Get LTM semantic matches (top 2 most similar)
		ltm_semantic = []
		if patient_id and self.embedder:
			try:
				query_embedding = self.embedder.embed([question])[0]
				ltm_results = search_memory_summaries_semantic(
					patient_id,
					query_embedding,
					limit=2
				)
				ltm_semantic = [result["summary"] for result in ltm_results]
			except Exception as e:
				logger().warning(f"Failed to perform LTM semantic search: {e}")

		# Get current session messages for context
		session = self.memory.get_session(session_id)
		session_context = ""
		if session:
			recent_messages = session.get_messages(10)
			session_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])

		# Use NVIDIA to reason about STM relevance
		relevant_stm = []
		if recent_qa and nvidia_rotator:
			try:
				sys = "You are a medical AI assistant. Select only the most relevant recent medical context that directly relates to the new question. Return the selected items verbatim, no commentary. If none are relevant, return nothing."
				user = f"Question: {question}\n\nSelect relevant items from recent medical context:\n" + "\n".join(recent_qa)
				relevant_stm_text = await nvidia_chat(sys, user, nvidia_rotator)
				if relevant_stm_text and relevant_stm_text.strip():
					relevant_stm = [relevant_stm_text.strip()]
			except Exception as e:
				logger().warning(f"Failed to get NVIDIA STM reasoning: {e}")
				relevant_stm = recent_qa
		else:
			relevant_stm = recent_qa

		# Combine all relevant context
		context_parts = []
		if relevant_stm:
			context_parts.append("Recent relevant medical context (STM):\n" + "\n".join(relevant_stm))
		if ltm_semantic:
			context_parts.append("Semantically relevant medical history (LTM):\n" + "\n".join(ltm_semantic))
		if session_context:
			context_parts.append("Current conversation:\n" + session_context)

		return "\n\n".join(context_parts) if context_parts else ""

	def get_user_medical_history(
		self,
		user_id: str,
		limit: int = 10
	) -> list[str]:
		"""Retrieves a user's most recent medical history summaries."""
		return self.memory.all(user_id)[-limit:]

	def search_medical_context(
		self,
		user_id: str,
		query: str,
		top_k: int = settings.DEFAULT_TOP_K
	) -> list[str]:
		"""Searches a user's medical context for relevant information."""
		if not self.embedder:
			return self._fallback_text_search(user_id, query, top_k)

		try:
			all_context = self.memory.all(user_id)
			if not all_context:
				return []
			return self.embedder.semantic_search(query, all_context, top_k)
		except Exception as e:
			logger().error(f"Semantic search failed: {e}")
			return self._fallback_text_search(user_id, query, top_k)

	def _fallback_text_search(
		self,
		user_id: str,
		query: str,
		top_k: int
	) -> list[str]:
		"""Performs a simple text-based search as a fallback."""
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
		"""Generates a summary of the Q&A exchange using available AI models."""
		fallback_summary = f"q: {question}\na: {answer}"
		if not gemini_rotator or not gemini_rotator.get_key():
			return fallback_summary

		try:
			summary = await summariser.summarise_qa_with_gemini(
				question, answer, gemini_rotator
			)
			if not summary or not summary.strip():
				if nvidia_rotator and nvidia_rotator.get_key():
					summary = await summariser.summarise_qa_with_nvidia(
						question, answer, nvidia_rotator
					)
			return summary if summary and summary.strip() else fallback_summary
		except Exception as e:
			logger().warning(f"Failed to generate AI summary: {e}")
			return fallback_summary
