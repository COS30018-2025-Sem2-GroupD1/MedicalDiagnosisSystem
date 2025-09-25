# core/memory.py

import uuid
from datetime import datetime, timezone
from typing import Any

from src.core.profile import UserProfile
from src.core.session import ChatSession
from src.data.repositories import account, medical, session
from src.utils.logger import logger


class MemoryLRU:
	"""
	A memory system that orchestrates data access between the application core
	and the data repositories, managing users, sessions, and medical context.
	"""

	def __init__(self, max_sessions_per_user: int = 10):
		self.max_sessions_per_user = max_sessions_per_user

	def create_user(self,
		name: str = "Anonymous",
		role: str | None = None,
		speciality: str | None = None,
		roles: list[str] = [],
		preferences: dict[str, Any] = {},
		*,
		user_id: str,
	) -> UserProfile:
		"""Creates a new user profile."""
		account.create_account(
			name=name,
			role=role,
			speciality=speciality,
			roles=roles,
			preferences=preferences,
			user_id=user_id
		)
		return UserProfile(user_id, name)

	def get_user(self, user_id: str) -> UserProfile | None:
		"""Retrieves a user profile by its ID."""
		data = account.get_user_profile(user_id)
		return UserProfile.from_dict(data) if data else None

	def create_session(self, user_id: str, title: str = "New Chat") -> str:
		"""Creates a new chat session for a user."""
		return session.create_session(user_id, title)

	def get_session(self, session_id: str) -> ChatSession | None:
		"""Retrieves a single chat session by its ID."""
		try:
			data = session.get_session(session_id)
			return ChatSession.from_dict(data) if data else None
		except Exception as e:
			logger().error(f"Error retrieving session {session_id}: {e}")
			raise

	def get_user_sessions(self, user_id: str) -> list[ChatSession]:
		"""Retrieves all sessions for a specific user."""
		sessions_data = session.get_user_sessions(user_id, limit=self.max_sessions_per_user)
		return [ChatSession.from_dict(data) for data in sessions_data]

	def add_message_to_session(
		self,
		session_id: str,
		role: str,
		content: str,
		metadata: dict = {}
	):
		"""
		Adds a message to a chat session.

		@TODO Update.
		"""
		message = {
			"id": str(uuid.uuid4()),
			"role": role,
			"content": content,
			"timestamp": datetime.now(timezone.utc),
			"metadata": metadata
		}
		session.add_message(session_id, message)

	def update_session_title(self, session_id: str, title: str):
		"""Updates the title of a session."""
		session.update_session_title(session_id, title)

	def delete_session(self, session_id: str):
		"""Deletes a chat session."""
		session.delete_session(session_id)

	def set_user_preferences(
		self,
		user_id: str,
		update_data: dict[str, Any]
	):
		"""Sets a preference for a user."""
		account.set_user_preferences(user_id, update_data)

	def add(self, user_id: str, summary: str):
		"""Adds a medical context summary for a user."""
		medical.add_medical_context(user_id, summary)

	def all(self, user_id: str) -> list[str]:
		"""Retrieves all medical context summaries for a user."""
		contexts = medical.get_medical_context(user_id)
		return [ctx["summary"] for ctx in contexts]

	def recent(self, user_id: str, n: int) -> list[str]:
		"""Retrieves the N most recent medical context summaries."""
		contexts = medical.get_medical_context(user_id, limit=n)
		return [ctx["summary"] for ctx in contexts]

	def rest(self, user_id: str, skip: int) -> list[str]:
		"""Retrieves all summaries except for the N most recent ones."""
		all_contexts = self.all(user_id)
		return all_contexts[skip:]

	# TODO
	#def clear(self, user_id: str):

	def get_medical_context(
		self,
		user_id: str,
		limit: int = 5
	) -> str:
		"""Retrieves and formats recent medical context into a single string."""
		## Get recent QA summaries
		#recent_qa = self.recent(user_id, 5)

		## Get current session messages for context
		#session = self.get_session(session_id)
		#session_context = ""
		#if session:
		#	recent_messages = session.get_messages(10)
		#	session_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])

		## Combine context
		#context_parts = []
		#if recent_qa:
		#	context_parts.append("Recent medical context:\n" + "\n".join(recent_qa))
		#if session_context:
		#	context_parts.append("Current conversation:\n" + session_context)

		#return "\n\n".join(context_parts) if context_parts else ""

		try:
			contexts = self.recent(user_id, limit)
			return "\n\n".join(contexts)
		except Exception as e:
			logger().error(f"Error getting medical context for user {user_id}: {e}")
			return ""
