# core/session.py

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


class ChatSession:
	"""Represents a single MongoDB session document."""

	class Message:
		"""Represents a single message in a chat session."""

		def __init__(
			self,
			message_id: int,
			content: str,
			sent_by_user: bool,
			timestamp: datetime
		):
			self._id = message_id
			self._content: str = content
			self._sent_by_user: bool = sent_by_user
			self._timestamp = timestamp

		@property
		def id(self) -> int:
			return self._id

		@property
		def content(self) -> str:
			return self._content

		@property
		def sent_by_user(self) -> bool:
			return self._sent_by_user

		@property
		def timestamp(self) -> datetime:
			return self._timestamp

		def to_dict(self) -> dict[str, Any]:
			"""Convert to MongoDB format."""
			return {
				"_id": self._id,
				"content": self._content,
				"sent_by_user": self._sent_by_user,
				"timestamp": self._timestamp
			}

		@classmethod
		def from_dict(cls, data: dict) -> "ChatSession.Message":
			"""Create from MongoDB document."""
			return cls(
				message_id=int(data["_id"]),
				content=str(data["content"]),
				sent_by_user=bool(data["sent_by_user"]),
				timestamp=data.get("timestamp") or datetime.now(timezone.utc)
			)

	def __init__(
		self,
		session_id: str,
		account_id: str,
		patient_id: str,
		title: str = "New Chat",
		created_at: datetime | None = None,
		updated_at: datetime | None = None,
		messages: list[dict[str, Any]] | None = None
	):
		self._session_id = str(session_id)
		self._account_id = str(account_id)
		self._patient_id = str(patient_id)
		self._title = str(title)
		self._created_at = created_at or datetime.now(timezone.utc)
		self._updated_at = updated_at or self._created_at
		self._messages = tuple(
			ChatSession.Message.from_dict(msg) for msg in (messages or [])
		)

	@property
	def session_id(self) -> str:
		return self._session_id

	@property
	def account_id(self) -> str:
		return self._account_id

	@property
	def patient_id(self) -> str:
		return self._patient_id

	@property
	def title(self) -> str:
		return self._title

	@property
	def created_at(self) -> datetime:
		return self._created_at

	@property
	def updated_at(self) -> datetime:
		return self._updated_at

	@property
	def messages(self) -> tuple[Message, ...]:
		return self._messages

	def get_messages(self, limit: int | None = None) -> tuple[Message, ...]:
		"""Retrieves messages from the session, optionally limited."""
		if limit is None:
			return self._messages
		return self._messages[-limit:]

	def to_dict(self) -> dict[str, Any]:
		"""Converts the session to a dictionary for MongoDB storage."""
		return {
			"account_id": self._account_id,
			"patient_id": self._patient_id,
			"title": self._title,
			"created_at": self._created_at,
			"updated_at": self._updated_at,
			"messages": [msg.to_dict() for msg in self._messages]
		}

	@classmethod
	def from_dict(cls, data: dict) -> "ChatSession":
		"""Creates a ChatSession instance from a MongoDB document."""

		errors = []
		# Validate required fields with types
		if "_id" not in data:
			errors.append("Missing '_id' field")
		elif not isinstance(data["_id"], (str, ObjectId)):
			errors.append(f"Invalid '_id' type: {type(data['_id'])}")

		if "account_id" not in data:
			errors.append("Missing 'account_id' field")
		elif not isinstance(data["account_id"], (str, ObjectId)):
			errors.append(f"Invalid 'account_id' type: {type(data['account_id'])}")

		if "patient_id" not in data:
			errors.append("Missing 'patient_id' field")
		elif not isinstance(data["patient_id"], (str, ObjectId)):
			errors.append(f"Invalid 'patient_id' type: {type(data['patient_id'])}")

		if "title" in data and not isinstance(data["title"], str):
			errors.append(f"Invalid 'title' type: {type(data['title'])}")

		if "created_at" not in data:
			errors.append("Missing 'created_at' field")
		elif not isinstance(data["created_at"], datetime):
			errors.append(f"Invalid 'created_at' type: {type(data['created_at'])}")

		if "updated_at" not in data:
			errors.append("Missing 'updated_at' field")
		elif not isinstance(data["updated_at"], datetime):
			errors.append(f"Invalid 'updated_at' type: {type(data['updated_at'])}")

		# Validate messages array if present
		if "messages" in data:
			if not isinstance(data["messages"], list):
				errors.append(f"Invalid 'messages' type: {type(data['messages'])}")
			else:
				for i, msg in enumerate(data["messages"]):
					if not isinstance(msg, dict):
						errors.append(f"Invalid message type at index {i}: {type(msg)}")
						continue

					msg_errors = []
					if "_id" not in msg:
						msg_errors.append("Missing '_id'")
					elif not isinstance(msg["_id"], int):
						msg_errors.append(f"Invalid '_id' type: {type(msg['_id'])}")

					if "sent_by_user" not in msg:
						msg_errors.append("Missing 'sent_by_user'")
					elif not isinstance(msg["sent_by_user"], bool):
						msg_errors.append(f"Invalid 'sent_by_user' type: {type(msg['sent_by_user'])}")

					if "content" not in msg:
						msg_errors.append("Missing 'content'")
					elif not isinstance(msg["content"], str):
						msg_errors.append(f"Invalid 'content' type: {type(msg['content'])}")

					if "timestamp" not in msg:
						msg_errors.append("Missing 'timestamp'")
					elif not isinstance(msg["timestamp"], datetime):
						msg_errors.append(f"Invalid 'timestamp' type: {type(msg['timestamp'])}")

					if msg_errors:
						errors.append(f"Message {i} validation errors: {', '.join(msg_errors)}")

		if errors:
			raise ValueError("ChatSession validation failed:\n" + "\n".join(errors))

		return cls(
			session_id=data["_id"], # type: ignore
			account_id=data["account_id"], # type: ignore
			patient_id=data["patient_id"], # type: ignore
			title=data.get("title", "New Chat"),
			created_at=data.get("created_at"),
			updated_at=data.get("updated_at"),
			messages=data.get("messages", [])
		)
