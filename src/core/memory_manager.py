# src/core/memory_manager.py

from src.data.connection import ActionFailed
from src.data.repositories import account as account_repo
from src.data.repositories import medical_memory as memory_repo
from src.data.repositories import patient as patient_repo
from src.data.repositories import session as session_repo
from src.models.account import Account
from src.models.patient import Patient
from src.models.session import Message, Session
from src.services import summariser
from src.services.nvidia import nvidia_chat
from src.utils.embeddings import EmbeddingClient
from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator


class MemoryManager:
	"""
	A service layer that orchestrates data access and business logic for managing
	accounts, chat sessions, and long-term medical memory.
	"""
	def __init__(self, embedder: EmbeddingClient, max_sessions_per_user: int = 10):
		self.embedder = embedder
		self.max_sessions_per_user = max_sessions_per_user

	# --- Account Management Facade ---

	def create_account(
		self,
		name: str = "Anonymous",
		role: str = "Other",
		specialty: str | None = None
	) -> str | None:
		"""Creates a new user account."""
		try:
			return account_repo.create_account(name=name, role=role, specialty=specialty)
		except ActionFailed as e:
			logger().error(f"Failed to create account in MemoryManager: {e}")
			return None

	def get_account(self, user_id: str) -> Account | None:
		"""Retrieves a user account by its ID."""
		try:
			return account_repo.get_account(user_id)
		except ActionFailed as e:
			logger().error(f"Failed to get account '{user_id}' in MemoryManager: {e}")
			return None

	def get_all_accounts(self, limit: int = 50) -> list[Account]:
		"""Retrieves a list of all accounts."""
		try:
			return account_repo.get_all_accounts(limit=limit)
		except ActionFailed as e:
			logger().error(f"Failed to get all accounts in MemoryManager: {e}")
			return []

	def search_accounts(self, query: str, limit: int = 10) -> list[Account]:
		"""Searches for accounts by name."""
		try:
			return account_repo.search_accounts(query, limit=limit)
		except ActionFailed as e:
			logger().error(f"Failed to search accounts in MemoryManager: {e}")
			return []

	# --- Patient Management Facade ---

	def create_patient(self, **kwargs) -> str | None:
		"""Creates a new patient record."""
		try:
			return patient_repo.create_patient(**kwargs)
		except ActionFailed as e:
			logger().error(f"Failed to create patient in MemoryManager: {e}")
			return None

	def get_patient_by_id(self, patient_id: str) -> Patient | None:
		"""Retrieves a patient by their unique ID."""
		try:
			return patient_repo.get_patient_by_id(patient_id)
		except ActionFailed as e:
			logger().error(f"Failed to get patient '{patient_id}' in MemoryManager: {e}")
			return None

	def update_patient_profile(self, patient_id: str, updates: dict) -> int:
		"""Updates a patient's profile."""
		try:
			return patient_repo.update_patient_profile(patient_id, updates)
		except ActionFailed as e:
			logger().error(f"Failed to update patient '{patient_id}' in MemoryManager: {e}")
			return 0

	def search_patients(self, query: str, limit: int = 10) -> list[Patient]:
		"""Searches for patients by name."""
		try:
			return patient_repo.search_patients(query, limit=limit)
		except ActionFailed as e:
			logger().error(f"Failed to search patients in MemoryManager: {e}")
			return []

	# --- Session Management Facade ---

	def create_session(self, user_id: str, patient_id: str, title: str = "New Chat") -> Session | None:
		"""Creates a new chat session for a user."""
		try:
			return session_repo.create_session(user_id, patient_id, title)
		except ActionFailed as e:
			logger().error(f"Failed to create session in MemoryManager: {e}")
			return None

	def get_session(self, session_id: str) -> Session | None:
		"""Retrieves a single chat session by its ID."""
		try:
			return session_repo.get_session(session_id)
		except ActionFailed as e:
			logger().error(f"Failed to get session '{session_id}' in MemoryManager: {e}")
			return None

	def get_user_sessions(self, user_id: str) -> list[Session]:
		"""Retrieves all sessions for a specific user."""
		try:
			return session_repo.get_user_sessions(user_id, limit=self.max_sessions_per_user)
		except ActionFailed as e:
			logger().error(f"Failed to get user sessions for '{user_id}': {e}")
			return []

	def update_session_title(self, session_id: str, title: str) -> bool:
		"""Updates the title of a session."""
		try:
			return session_repo.update_session_title(session_id, title)
		except ActionFailed as e:
			logger().error(f"Failed to update title for session '{session_id}': {e}")
			return False

	def list_patient_sessions(self, patient_id: str) -> list[Session]:
		"""Retrieves all sessions for a specific patient."""
		try:
			return session_repo.list_patient_sessions(patient_id, limit=self.max_sessions_per_user)
		except ActionFailed as e:
			logger().error(f"Failed to get sessions for patient '{patient_id}': {e}")
			return []

	def delete_session(self, session_id: str) -> bool:
		"""Deletes a chat session."""
		try:
			return session_repo.delete_session(session_id)
		except ActionFailed as e:
			logger().error(f"Failed to delete session '{session_id}' in MemoryManager: {e}")
			return False

	def get_session_messages(self, session_id: str, limit: int | None = None) -> list[Message]:
		"""Gets messages from a specific chat session."""
		try:
			return session_repo.get_session_messages(session_id, limit)
		except ActionFailed as e:
			logger().error(f"Failed to get messages for session '{session_id}': {e}")
			return []

	# --- Core Business Logic ---

	async def process_medical_exchange(
		self,
		session_id: str,
		patient_id: str,
		doctor_id: str,
		question: str,
		answer: str,
		gemini_rotator: APIKeyRotator,
		nvidia_rotator: APIKeyRotator
	) -> str | None:
		"""
		Processes a medical Q&A exchange: adds messages to the session, generates
		a summary, creates an embedding, and saves it to long-term memory.
		"""
		try:
			# 1. Add messages to the current session
			session_repo.add_message(session_id, question, sent_by_user=True)
			session_repo.add_message(session_id, answer, sent_by_user=False)

			# 2. Generate a concise summary of the exchange
			summary = await self._generate_summary(question, answer, gemini_rotator, nvidia_rotator)
			if not summary:
				return None # Could not generate a summary

			# 3. Generate an embedding for the summary for semantic search
			embedding = None
			if self.embedder:
				try:
					embedding = self.embedder.embed([summary])[0]
				except Exception as e:
					logger().warning(f"Failed to generate embedding for summary: {e}")

			# 4. Save the summary and embedding to long-term medical memory
			memory_repo.create_memory(
				patient_id=patient_id,
				doctor_id=doctor_id,
				session_id=session_id,
				summary=summary,
				embedding=embedding
			)

			# 5. Update the session title if this was the first exchange
			await self._update_session_title_if_first_message(session_id, question, nvidia_rotator)

			return summary
		except ActionFailed as e:
			logger().error(f"Database error processing medical exchange for session '{session_id}': {e}")
			return None
		except Exception as e:
			logger().error(f"Unexpected error processing medical exchange: {e}")
			return None

	async def get_enhanced_context(
		self,
		session_id: str,
		patient_id: str,
		question: str,
		nvidia_rotator: APIKeyRotator
	) -> str:
		"""
		Builds a rich, multi-source context string for a new question, combining
		short-term memory, long-term semantic memory, and current conversation.
		"""
		context_parts = []

		# 1. Get recent summaries (Short-Term Memory)
		try:
			recent_memories = memory_repo.get_recent_memories(patient_id, limit=3)
			if recent_memories:
				# Use NVIDIA to reason about relevance
				relevant_stm = await self._filter_summaries_for_relevance(
					question, [mem.summary for mem in recent_memories], nvidia_rotator
				)
				if relevant_stm:
					context_parts.append("Recent relevant medical context (STM):\n" + "\n".join(relevant_stm))
		except ActionFailed as e:
			logger().warning(f"Could not retrieve recent memories for enhanced context: {e}")

		# 2. Get semantically similar summaries (Long-Term Memory)
		if self.embedder:
			try:
				query_embedding = self.embedder.embed([question])[0]
				ltm_results = memory_repo.search_memories_semantic(patient_id, query_embedding, limit=2)
				if ltm_results:
					ltm_summaries = [result.summary for result in ltm_results]
					context_parts.append("Semantically relevant medical history (LTM):\n" + "\n".join(ltm_summaries))
			except (ActionFailed, Exception) as e:
				logger().warning(f"Failed to perform LTM semantic search: {e}")

		# 3. Get current conversation context
		try:
			session = session_repo.get_session(session_id)
			if session and session.messages:
				session_context = "\n".join([
					f"{'User' if msg.sent_by_user else 'Assistant'}: {msg.content}"
					for msg in session.messages[-10:] # Get last 10 messages
				])
				context_parts.append("Current conversation:\n" + session_context)
		except ActionFailed as e:
			logger().warning(f"Could not retrieve current session context: {e}")

		return "\n\n".join(context_parts)

	# --- Private Helper Methods ---

	async def _update_session_title_if_first_message(
		self,
		session_id: str,
		question: str,
		nvidia_rotator: APIKeyRotator
	) -> None:
		"""Updates the session title if it contains only the first Q&A pair."""
		try:
			session = self.get_session(session_id)
			# Check if it's the first user message and first assistant response
			if session and len(session.messages) == 2:
				title = await summariser.summarise_title_with_nvidia(question, nvidia_rotator, max_words=5)
				if not title:
					title = question[:80] # Fallback to first 80 chars
				self.update_session_title(session_id, title)
		except Exception as e:
			logger().warning(f"Failed to auto-update session title for session '{session_id}': {e}")

	async def _generate_summary(
		self,
		question: str,
		answer: str,
		gemini_rotator: APIKeyRotator,
		nvidia_rotator: APIKeyRotator
	) -> str:
		"""Generates a summary of a Q&A exchange, falling back to a basic format if AI fails."""
		try:
			summary = await summariser.summarise_qa_with_gemini(question, answer, gemini_rotator)
			if summary:
				return summary
			# Fallback to NVIDIA if Gemini fails
			summary = await summariser.summarise_qa_with_nvidia(question, answer, nvidia_rotator)
			if summary:
				return summary
		except Exception as e:
			logger().warning(f"Failed to generate AI summary: {e}")

		# Fallback for both exceptions and cases where services return None
		return f"Question: {question}\nAnswer: {answer}"

	async def _filter_summaries_for_relevance(
		self,
		question: str,
		summaries: list[str],
		nvidia_rotator: APIKeyRotator
	) -> list[str]:
		"""Uses an AI model to select only the most relevant summaries for a given question."""
		if not summaries:
			return []
		try:
			sys_prompt = "You are a medical AI assistant. Select only the most relevant recent medical context that directly relates to the new question. Return the selected items verbatim, separated by a newline. If none are relevant, return nothing."
			user_prompt = f"Question: {question}\n\nSelect relevant items from recent medical context:\n" + "\n".join(summaries)

			relevant_text = await nvidia_chat(sys_prompt, user_prompt, nvidia_rotator)
			return relevant_text.strip().split('\n') if relevant_text and relevant_text.strip() else []
		except Exception as e:
			logger().warning(f"Failed to get AI reasoning for STM relevance: {e}")
			return summaries # Fallback to returning all summaries
