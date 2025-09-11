# core/session.py

import uuid
from datetime import datetime, timezone
from typing import Any

from src.utils.logger import logger


class ChatSession:
	"""Represents a single chat session with a user."""

	def __init__(self, session_id: str, user_id: str, title: str = "New Chat"):
		self.session_id = session_id
		self.user_id = user_id
		self.title = title
		self.created_at = datetime.now(timezone.utc)
		self.last_activity = datetime.now(timezone.utc)
		self.messages: list[dict[str, Any]] = []

	def add_message(self, role: str, content: str, metadata: dict | None = None):
		"""Adds a message to the session."""
		message = {
			"id": str(uuid.uuid4()),
			"role": role,
			"content": content,
			"timestamp": datetime.now(timezone.utc),
			"metadata": metadata or {}
		}
		self.messages.append(message)
		self.last_activity = datetime.now(timezone.utc)

	def get_messages(self, limit: int | None = None) -> list[dict[str, Any]]:
		"""Retrieves messages from the session, optionally limited."""
		return self.messages if limit is None else self.messages[-limit:]

	def update_title(self, title: str):
		"""Updates the session title."""
		self.title = title
		self.last_activity = datetime.now(timezone.utc)

	@classmethod
	def from_dict(cls, data: dict) -> "ChatSession":
		"""Creates a ChatSession instance from a dictionary."""
		if not isinstance(data, dict):
			raise ValueError(f"Expected dict for ChatSession, got {type(data)}")

		required = ["_id", "user_id"]
		if not all(f in data for f in required):
			raise ValueError(f"Missing required fields in ChatSession data: {required}")

		try:
			instance = cls(
				session_id=str(data["_id"]),
				user_id=str(data["user_id"]),
				title=str(data.get("title", "New Chat"))
			)
			now = datetime.now(timezone.utc)
			instance.created_at = data.get("created_at", now)
			instance.last_activity = data.get("updated_at", instance.created_at)
			instance.messages = data.get("messages", [])
			return instance
		except Exception as e:
			logger().error(f"Error creating ChatSession from data: {data}\nError: {e}")
			raise ValueError(f"Failed to create ChatSession: {e}") from e
