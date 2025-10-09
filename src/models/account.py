# src/models/account.py

from datetime import datetime

from src.models.common import BaseMongoModel


class Account(BaseMongoModel):
	"""A Pydantic model for an account."""
	name: str
	role: str
	specialty: str | None = None
	created_at: datetime
	updated_at: datetime
	last_seen: datetime
