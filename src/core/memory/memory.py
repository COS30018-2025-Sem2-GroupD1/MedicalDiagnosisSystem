# core/memory/memory.py

import uuid
from datetime import datetime, timezone
from typing import Any

from src.data import mongodb
from src.utils.logger import get_logger

logger = get_logger("MEMORY")

class ChatSession:
	"""Represents a chat session with a user"""
	def __init__(self, session_id: str, user_id: str, title: str = "New Chat"):
		self.session_id = session_id
		self.user_id = user_id
		self.title = title
		self.created_at = datetime.now(timezone.utc)
		self.last_activity = datetime.now(timezone.utc)
		self.messages: list[dict[str, Any]] = []

	def add_message(self, role: str, content: str, metadata: dict | None = None):
		"""Add a message to the session"""
		message = {
			"id": str(uuid.uuid4()),
			"role": role,  # "user" or "assistant"
			"content": content,
			"timestamp": datetime.now(timezone.utc),
			"metadata": metadata or {}
		}
		self.messages.append(message)
		self.last_activity = datetime.now(timezone.utc)

	def get_messages(self, limit: int | None = None) -> list[dict[str, Any]]:
		"""Get messages from the session, optionally limited"""
		if limit is None:
			return self.messages
		return self.messages[-limit:]

	def update_title(self, title: str):
		"""Update the session title"""
		self.title = title
		self.last_activity = datetime.now(timezone.utc)

	@classmethod
	def from_dict(cls, data: dict) -> "ChatSession":
		"""Create a ChatSession from a dictionary"""
		if not isinstance(data, dict):
			logger.error(f"Invalid data type for ChatSession.from_dict: {type(data)}")
			raise ValueError(f"Expected dict, got {type(data)}")

		required_fields = ["_id", "user_id"]
		missing_fields = [f for f in required_fields if f not in data]
		if missing_fields:
			logger.error(f"Missing required fields in ChatSession data: {missing_fields}")
			logger.error(f"Available fields: {list(data.keys())}")
			raise ValueError(f"Missing required fields: {missing_fields}")

		try:
			instance = cls(
				session_id=str(data["_id"]),
				user_id=str(data["user_id"]),
				title=str(data.get("title", "New Chat"))
			)

			# Handle timestamps with detailed error checking
			try:
				instance.created_at = data.get("created_at", datetime.now(timezone.utc))
				instance.last_activity = data.get("updated_at", instance.created_at)
			except Exception as e:
				logger.error(f"Error processing timestamps: {e}")
				logger.error(f"created_at: {data.get('created_at')}")
				logger.error(f"updated_at: {data.get('updated_at')}")
				# Use current time as fallback
				now = datetime.now(timezone.utc)
				instance.created_at = now
				instance.last_activity = now

			instance.messages = data.get("messages", [])
			return instance
		except Exception as e:
			logger.error(f"Error creating ChatSession from data: {e}")
			logger.error(f"Data: {data}")
			raise ValueError(f"Failed to create ChatSession: {e}") from e

class UserProfile:
	"""Represents a user profile with multiple chat sessions"""
	def __init__(self, user_id: str, name: str = "Anonymous"):
		self.user_id = user_id
		self.name = name
		self.created_at = datetime.now(timezone.utc)
		self.last_seen = datetime.now(timezone.utc)
		self.preferences: dict[str, Any] = {}

	def update_activity(self):
		"""Update last seen timestamp"""
		self.last_seen = datetime.now(timezone.utc)

	def set_preference(self, key: str, value: Any):
		"""Set a user preference"""
		self.preferences[key] = value

	@property
	def role(self) -> str:
		"""Get user role from preferences"""
		return self.preferences.get("role", "Unknown")

	@classmethod
	def from_dict(cls, data: dict) -> "UserProfile":
		"""Create a UserProfile from a dictionary"""
		instance = cls(data["_id"], data["name"])
		instance.created_at = data["created_at"]
		instance.last_seen = data["last_seen"]
		instance.preferences = data["preferences"]
		return instance

class MemoryLRU:
	"""
	Memory system using MongoDB for persistence, supporting:
	- Multiple users with profiles
	- Multiple chat sessions per user
	- Chat history and continuity
	- Medical context summaries
	"""
	def __init__(self, max_sessions_per_user: int = 10):
		self.max_sessions_per_user = max_sessions_per_user

	def create_user(self, user_id: str, name: str = "Anonymous") -> UserProfile:
		"""Create a new user profile"""
		user = UserProfile(user_id, name)
		mongodb.create_account({
			"_id": user_id,
			"name": name,
			"created_at": datetime.now(timezone.utc),
			"last_seen": datetime.now(timezone.utc),
			"preferences": {}
		})
		return user

	def get_user(self, user_id: str) -> UserProfile | None:
		"""Get user profile by ID"""
		data = mongodb.get_user_profile(user_id)
		return UserProfile.from_dict(data) if data else None

	def create_session(self, user_id: str, title: str = "New Chat") -> str:
		"""Create a new chat session"""
		session_id = str(uuid.uuid4())
		mongodb.create_chat_session({
			"_id": session_id,
			"user_id": user_id,
			"title": title,
			"messages": []
		})
		return session_id

	def get_session(self, session_id: str) -> ChatSession | None:
		"""Get chat session by ID"""
		try:
			data = mongodb.get_session(session_id)
			if not data:
				logger.info(f"Session not found: {session_id}")
				return None

			logger.debug(f"Retrieved session data: {data}")
			return ChatSession.from_dict(data)
		except Exception as e:
			logger.error(f"Error retrieving session {session_id}: {e}")
			logger.error(f"Stack trace:", exc_info=True)
			raise

	def get_user_sessions(self, user_id: str) -> list[ChatSession]:
		"""Get all sessions for a user"""
		sessions_data = mongodb.get_user_sessions(user_id, limit=self.max_sessions_per_user)
		return [ChatSession.from_dict(data) for data in sessions_data]

	def add_message_to_session(self, session_id: str, role: str, content: str, metadata: dict | None = None):
		"""Add a message to a session"""
		message = {
			"id": str(uuid.uuid4()),
			"role": role,
			"content": content,
			"timestamp": datetime.now(timezone.utc),
			"metadata": metadata or {}
		}
		mongodb.add_message(session_id, message)

	def update_session_title(self, session_id: str, title: str):
		"""Update session title"""
		mongodb.update_session_title(session_id, title)

	def delete_session(self, session_id: str):
		"""Delete a chat session"""
		mongodb.delete_chat_session(session_id)

	def set_user_preference(self, user_id: str, key: str, value: Any):
		"""Set user preference"""
		mongodb.set_user_preference(user_id, key, value)

	# Medical context methods
	def add(self, user_id: str, summary: str):
		"""Add a medical context summary"""
		mongodb.add_medical_context(user_id, summary)

	def all(self, user_id: str) -> list[str]:
		"""Get all medical context summaries for a user"""
		contexts = mongodb.get_medical_context(user_id)
		return [ctx["summary"] for ctx in contexts]

	def recent(self, user_id: str, n: int) -> list[str]:
		"""Get n most recent medical context summaries"""
		contexts = mongodb.get_medical_context(user_id, limit=n)
		return [ctx["summary"] for ctx in contexts]

	def rest(self, user_id: str, skip: int) -> list[str]:
		"""Get all summaries except the most recent n"""
		contexts = mongodb.get_medical_context(user_id)
		return [ctx["summary"] for ctx in contexts[skip:]]

	def get_medical_context(self, user_id: str, session_id: str, question: str) -> str:
		"""Get relevant medical context for a question"""
		try:
			# Get recent contexts
			contexts = mongodb.get_medical_context(user_id, limit=5)
			if not contexts:
				return ""

			# Format contexts into a string
			context_texts = []
			for ctx in contexts:
				summary = ctx.get("summary")
				if summary:
					context_texts.append(summary)

			if not context_texts:
				return ""

			return "\n\n".join(context_texts)
		except Exception as e:
			logger.error(f"Error getting medical context: {e}")
			logger.error("Stack trace:", exc_info=True)
			return ""
