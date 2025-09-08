# core/session.py

import uuid
from datetime import datetime, timezone
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("SESSION")

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
