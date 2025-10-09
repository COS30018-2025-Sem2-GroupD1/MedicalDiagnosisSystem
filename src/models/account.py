# src/models/account.py

from datetime import datetime

from pydantic import BaseModel

from src.models.common import BaseMongoModel


class Account(BaseMongoModel):
	"""A Pydantic model for an account, used for API responses."""
	name: str
	role: str
	specialty: str | None = None
	created_at: datetime
	updated_at: datetime
	last_seen: datetime

class AccountCreateRequest(BaseModel):
	"""A Pydantic model for an account creation request from the API."""
	name: str
	role: str
	specialty: str | None = None
