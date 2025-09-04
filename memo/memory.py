# memo/memory.py

import time
import uuid
from collections import defaultdict, deque
from typing import Any


class ChatSession:
	"""Represents a chat session with a user"""
	def __init__(self, session_id: str, user_id: str, title: str = "New Chat"):
		self.session_id = session_id
		self.user_id = user_id
		self.title = title
		self.created_at = time.time()
		self.last_activity = time.time()
		self.messages: list[dict[str, Any]] = []

	def add_message(self, role: str, content: str, metadata: dict | None = None):
		"""Add a message to the session"""
		message = {
			"id": str(uuid.uuid4()),
			"role": role,  # "user" or "assistant"
			"content": content,
			"timestamp": time.time(),
			"metadata": metadata or {}
		}
		self.messages.append(message)
		self.last_activity = time.time()

	def get_messages(self, limit: int | None = None) -> list[dict[str, Any]]:
		"""Get messages from the session, optionally limited"""
		if limit is None:
			return self.messages
		return self.messages[-limit:]

	def update_title(self, title: str):
		"""Update the session title"""
		self.title = title
		self.last_activity = time.time()

class UserProfile:
	"""Represents a user profile with multiple chat sessions"""
	def __init__(self, user_id: str, name: str = "Anonymous"):
		self.user_id = user_id
		self.name = name
		self.created_at = time.time()
		self.last_seen = time.time()
		self.preferences: dict[str, Any] = {}

	def update_activity(self):
		"""Update last seen timestamp"""
		self.last_seen = time.time()

	def set_preference(self, key: str, value: Any):
		"""Set a user preference"""
		self.preferences[key] = value

	@property
	def role(self) -> str:
		"""Get user role from preferences"""
		return self.preferences.get("role", "Unknown")

class MemoryLRU:
	"""
	Enhanced LRU-like memory system supporting:
	- Multiple users with profiles
	- Multiple chat sessions per user
	- Chat history and continuity
	- Medical context summaries
	"""
	def __init__(self, capacity: int = 20, max_sessions_per_user: int = 10):
		self.capacity = capacity
		self.max_sessions_per_user = max_sessions_per_user

		# User profiles and sessions
		self._users: dict[str, UserProfile] = {}
		self._sessions: dict[str, ChatSession] = {}
		self._user_sessions: dict[str, list[str]] = defaultdict(list)

		# Medical context summaries (QA pairs)
		self._qa_store: dict[str, deque] = defaultdict(lambda: deque(maxlen=self.capacity))

	def create_user(self, user_id: str, name: str = "Anonymous") -> UserProfile:
		"""Create a new user profile"""
		if user_id not in self._users:
			user = UserProfile(user_id, name)
			self._users[user_id] = user
		return self._users[user_id]

	def get_user(self, user_id: str) -> UserProfile | None:
		"""Get user profile by ID"""
		user = self._users.get(user_id)
		if user:
			user.update_activity()
		return user

	def create_session(self, user_id: str, title: str = "New Chat") -> str:
		"""Create a new chat session for a user"""
		# Ensure user exists
		if user_id not in self._users:
			self.create_user(user_id)

		# Create session
		session_id = str(uuid.uuid4())
		session = ChatSession(session_id, user_id, title)
		self._sessions[session_id] = session

		# Add to user's session list
		user_sessions = self._user_sessions[user_id]
		user_sessions.append(session_id)

		# Enforce max sessions per user
		if len(user_sessions) > self.max_sessions_per_user:
			oldest_session = user_sessions.pop(0)
			if oldest_session in self._sessions:
				del self._sessions[oldest_session]

		return session_id

	def get_session(self, session_id: str) -> ChatSession | None:
		"""Get a chat session by ID"""
		return self._sessions.get(session_id)

	def get_user_sessions(self, user_id: str) -> list[ChatSession]:
		"""Get all sessions for a user"""
		session_ids = self._user_sessions.get(user_id, [])
		sessions = []
		for sid in session_ids:
			if sid in self._sessions:
				sessions.append(self._sessions[sid])
		# Sort by last activity (most recent first)
		sessions.sort(key=lambda x: x.last_activity, reverse=True)
		return sessions

	def add_message_to_session(self, session_id: str, role: str, content: str, metadata: dict | None = None):
		"""Add a message to a specific session"""
		session = self._sessions.get(session_id)
		if session:
			session.add_message(role, content, metadata)

	def update_session_title(self, session_id: str, title: str):
		"""Update the title of a session"""
		session = self._sessions.get(session_id)
		if session:
			session.update_title(title)

	def delete_session(self, session_id: str):
		"""Delete a chat session"""
		if session_id in self._sessions:
			session = self._sessions[session_id]
			user_id = session.user_id

			# Remove from user's session list
			if user_id in self._user_sessions:
				self._user_sessions[user_id] = [s for s in self._user_sessions[user_id] if s != session_id]

			# Delete session
			del self._sessions[session_id]

	# Legacy methods for backward compatibility
	def add(self, user_id: str, qa_summary: str):
		"""Add a QA summary to the medical context store"""
		self._qa_store[user_id].append(qa_summary)

	def recent(self, user_id: str, n: int = 3) -> list[str]:
		"""Get recent QA summaries for medical context"""
		d = self._qa_store[user_id]
		if not d:
			return []
		return list(d)[-n:][::-1]

	def rest(self, user_id: str, skip_n: int = 3) -> list[str]:
		"""Get older QA summaries for medical context"""
		d = self._qa_store[user_id]
		if not d:
			return []
		return list(d)[:-skip_n] if len(d) > skip_n else []

	def all(self, user_id: str) -> list[str]:
		"""Get all QA summaries for medical context"""
		return list(self._qa_store[user_id])

	def clear(self, user_id: str) -> None:
		"""Clear all cached summaries for the given user"""
		if user_id in self._qa_store:
			self._qa_store[user_id].clear()

	def get_medical_context(self, user_id: str, session_id: str, question: str) -> str:
		"""Get relevant medical context for a question"""
		# Get recent QA summaries
		recent_qa = self.recent(user_id, 5)

		# Get current session messages for context
		session = self.get_session(session_id)
		session_context = ""
		if session:
			recent_messages = session.get_messages(10)
			session_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])

		# Combine context
		context_parts = []
		if recent_qa:
			context_parts.append("Recent medical context:\n" + "\n".join(recent_qa))
		if session_context:
			context_parts.append("Current conversation:\n" + session_context)

		return "\n\n".join(context_parts) if context_parts else ""
