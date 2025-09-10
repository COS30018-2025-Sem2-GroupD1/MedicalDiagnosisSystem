# core/profile.py

from datetime import datetime, timezone
from typing import Any


class UserProfile:
	"""Represents a user profile with multiple chat sessions."""

	def __init__(self, user_id: str, name: str = "Anonymous"):
		self.user_id = user_id
		self.name = name
		self.created_at = datetime.now(timezone.utc)
		self.last_seen = datetime.now(timezone.utc)
		self.preferences: dict[str, Any] = {}

	def update_activity(self):
		"""Updates the last seen timestamp."""
		self.last_seen = datetime.now(timezone.utc)

	def set_preference(self, key: str, value: Any):
		"""Sets a user preference."""
		self.preferences[key] = value

	@property
	def role(self) -> str:
		"""Retrieves the user role from preferences."""
		return self.preferences.get("role", "Unknown")

	@classmethod
	def from_dict(cls, data: dict) -> "UserProfile":
		"""Creates a UserProfile instance from a dictionary."""
		instance = cls(data["_id"], data["name"])
		instance.created_at = data["created_at"]
		instance.last_seen = data["last_seen"]
		instance.preferences = data["preferences"]
		return instance
