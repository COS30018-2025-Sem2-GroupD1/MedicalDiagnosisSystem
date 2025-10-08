# src/models/account.py

from datetime import datetime

from src.models.common import BaseMongoModel


class Account(BaseMongoModel):
	"""A Pydantic model for an account, used across all layers."""
	# The '_id' field and base config are inherited from BaseMongoModel
	name: str
	role: str
	specialty: str | None = None
	created_at: datetime
	updated_at: datetime
	last_seen: datetime
