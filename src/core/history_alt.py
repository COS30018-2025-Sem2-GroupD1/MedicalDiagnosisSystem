# core/memory/history.py

import json
from datetime import datetime, timezone

import numpy as np

from src.data.repositories.medical import (get_recent_memory_summaries,
                                           save_memory_summary,
                                           search_memory_summaries_semantic)
from src.data.repositories.message import save_chat_message
from src.data.repositories.session import ensure_session
from src.services.nvidia import nvidia_chat
from src.services.summariser import (summarise_qa_with_gemini,
                                     summarise_qa_with_nvidia)
from src.utils.embeddings import EmbeddingClient
from src.utils.logger import logger

class MedicalHistoryManager:
	"""
	Enhanced medical history manager that works with the new memory system
	"""
	def __init__(self, memory, embedder: EmbeddingClient | None = None):
		self.memory = memory
		self.embedder = embedder

	async def process_medical_exchange(
		self,
		user_id: str,
		session_id: str,
		question: str,
		answer: str,
		gemini_rotator,
		nvidia_rotator=None,
		*,
		patient_id: str | None = None,
		doctor_id: str | None = None,
		session_title: str | None = None
	) -> str:
		"""
		Process a medical Q&A exchange and store it in memory and MongoDB
		"""
		try:
			# Check if we have valid API keys
			if not gemini_rotator or not gemini_rotator.get_key() or gemini_rotator.get_key() == "":
				logger().info("No valid Gemini API keys available, using fallback summary")
				summary = f"q: {question}\na: {answer}"
			else:
				# Try to create summary using Gemini (preferred) or NVIDIA as fallback
				try:
					# First try Gemini
					summary = await summarise_qa_with_gemini(question, answer, gemini_rotator)
					if not summary or summary.strip() == "":
						# Fallback to NVIDIA if Gemini fails
						if nvidia_rotator and nvidia_rotator.get_key():
							summary = await summarise_qa_with_nvidia(question, answer, nvidia_rotator)
							if not summary or summary.strip() == "":
								summary = f"q: {question}\na: {answer}"
						else:
							summary = f"q: {question}\na: {answer}"
				except Exception as e:
					logger().warning(f"Failed to create AI summary: {e}")
					summary = f"q: {question}\na: {answer}"

			# Short-term cache under patient_id when available
			cache_key = patient_id or user_id
			self.memory.add(cache_key, summary)

			# Add to session history in cache
			self.memory.add_message_to_session(session_id, "user", question)
			self.memory.add_message_to_session(session_id, "assistant", answer)

			# Persist to MongoDB with patient/doctor context
			if patient_id and doctor_id:
				ensure_session(session_id=session_id, patient_id=patient_id, doctor_id=doctor_id, title=session_title or "New Chat", last_activity=datetime.now(timezone.utc))
				save_chat_message(session_id=session_id, patient_id=patient_id, doctor_id=doctor_id, role="user", content=question)
				save_chat_message(session_id=session_id, patient_id=patient_id, doctor_id=doctor_id, role="assistant", content=answer)

				# Generate embedding for semantic search
				embedding = None
				if self.embedder:
					try:
						embedding = self.embedder.embed([summary])[0]
					except Exception as e:
						logger().warning(f"Failed to generate embedding for summary: {e}")

				save_memory_summary(patient_id=patient_id, doctor_id=doctor_id, summary=summary, embedding=embedding)

			# Update session title if it's the first message
			session = self.memory.get_session(session_id)
			if session and len(session.messages) == 2:  # Just user + assistant
				# Generate a title using NVIDIA API if available
				try:
					from src.services.summariser import summarise_title_with_nvidia
					title = await summarise_title_with_nvidia(question, nvidia_rotator, max_words=5)
					if not title or title.strip() == "":
						title = question[:50] + ("..." if len(question) > 50 else "")
				except Exception as e:
					logger().warning(f"Failed to generate title with NVIDIA: {e}")
					title = question[:50] + ("..." if len(question) > 50 else "")

				self.memory.update_session_title(session_id, title)

				# Also update the session in MongoDB
				if patient_id and doctor_id:
					ensure_session(session_id=session_id, patient_id=patient_id, doctor_id=doctor_id, title=title, last_activity=datetime.now(timezone.utc))

			return summary

		except Exception as e:
			logger().error(f"Error processing medical exchange: {e}")
			# Fallback: store without summary
			summary = f"q: {question}\na: {answer}"
			cache_key = patient_id or user_id
			self.memory.add(cache_key, summary)
			self.memory.add_message_to_session(session_id, "user", question)
			self.memory.add_message_to_session(session_id, "assistant", answer)
			return summary

	def get_conversation_context(self, user_id: str, session_id: str, question: str, *, patient_id: str | None = None) -> str:
		"""
		Get relevant conversation context combining short-term cache (3) and long-term Mongo (20)
		"""
		# Short-term summaries
		cache_key = patient_id or user_id
		recent_qa = self.memory.recent(cache_key, 3)

		# Long-term summaries from Mongo (exclude ones already likely in cache by time order)
		long_term = []
		if patient_id:
			try:
				long_term = get_recent_memory_summaries(patient_id, limit=20)
			except Exception as e:
				logger().warning(f"Failed to fetch long-term memory: {e}")

		# Get current session messages for context
		session = self.memory.get_session(session_id)
		session_context = ""
		if session:
			recent_messages = session.get_messages(10)
			session_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])

		# Combine context
		context_parts = []
		combined = []
		if long_term:
			combined.extend(long_term[::-1])  # oldest to newest within limit
		if recent_qa:
			combined.extend(recent_qa[::-1])
		if combined:
			context_parts.append("Recent medical context:\n" + "\n".join(combined[-20:]))
		if session_context:
			context_parts.append("Current conversation:\n" + session_context)

		return "\n\n".join(context_parts) if context_parts else ""

	async def get_enhanced_conversation_context(self, user_id: str, session_id: str, question: str, nvidia_rotator, *, patient_id: str | None = None) -> str:
		"""
		Enhanced context retrieval combining STM (3) + LTM semantic search (2) with NVIDIA reasoning.
		Returns context that NVIDIA model can use to decide between STM and LTM information.
		"""
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
				numbered = [{"id": i+1, "text": s} for i, s in enumerate(recent_qa)]
				user = f"Question: {question}\n\nRecent medical context (last 3 exchanges):\n{json.dumps(numbered, ensure_ascii=False)}\n\nSelect any relevant items and output ONLY their 'text' lines concatenated."
				relevant_stm_text = await nvidia_chat(sys, user, nvidia_rotator)
				if relevant_stm_text and relevant_stm_text.strip():
					relevant_stm = [relevant_stm_text.strip()]
			except Exception as e:
				logger().warning(f"Failed to get NVIDIA STM reasoning: {e}")
				# Fallback to all recent QA if NVIDIA fails
				relevant_stm = recent_qa
		else:
			relevant_stm = recent_qa

		# Combine all relevant context
		context_parts = []

		# Add STM context
		if relevant_stm:
			context_parts.append("Recent relevant medical context (STM):\n" + "\n".join(relevant_stm))

		# Add LTM semantic context
		if ltm_semantic:
			context_parts.append("Semantically relevant medical history (LTM):\n" + "\n".join(ltm_semantic))

		# Add current session context
		if session_context:
			context_parts.append("Current conversation:\n" + session_context)

		return "\n\n".join(context_parts) if context_parts else ""

	def get_user_medical_history(self, user_id: str, limit: int = 20) -> list[str]:
		"""
		Get user's medical history (QA summaries)
		"""
		return self.memory.all(user_id)[-limit:]

	def search_medical_context(self, user_id: str, query: str, top_k: int = 5) -> list[str]:
		"""
		Search through user's medical context for relevant information
		"""
		if not self.embedder:
			# Fallback to simple text search
			all_context = self.memory.all(user_id)
			query_lower = query.lower()
			relevant = [ctx for ctx in all_context if query_lower in ctx.lower()]
			return relevant[:top_k]

		try:
			# Semantic search using embeddings
			query_embedding = np.array(self.embedder.embed([query])[0], dtype="float32")
			all_context = self.memory.all(user_id)

			if not all_context:
				return []

			context_embeddings = self.embedder.embed(all_context)
			similarities = []

			for i, ctx_emb in enumerate(context_embeddings):
				sim = EmbeddingClient._cosine_similarity(query_embedding, np.array(ctx_emb, dtype="float32"))
				similarities.append((sim, all_context[i]))

			# Sort by similarity and return top-k
			similarities.sort(key=lambda x: x[0], reverse=True)
			return [ctx for sim, ctx in similarities[:top_k] if sim > 0.1]

		except Exception as e:
			logger().error(f"Error in semantic search: {e}")
			# Fallback to simple search
			all_context = self.memory.all(user_id)
			query_lower = query.lower()
			relevant = [ctx for ctx in all_context if query_lower in ctx.lower()]
			return relevant[:top_k]
