# src/models/session.py

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.common import BaseMongoModel, PyObjectId


class Message(BaseModel):
	"""A Pydantic sub-model for a single message within a session."""
	# This _id is an integer, not an ObjectId, so we don't use PyObjectId here.
	id: int = Field(..., alias="_id")
	sent_by_user: bool
	content: str
	timestamp: datetime

	# Use a standard config for this sub-model
	model_config = ConfigDict(frozen=True, from_attributes=True)


class Session(BaseMongoModel):
	"""A Pydantic model for a chat session, including nested messages."""
	# The '_id' field and base config are inherited from BaseMongoModel
	account_id: PyObjectId
	patient_id: PyObjectId
	title: str
	created_at: datetime
	updated_at: datetime
	messages: list[Message] = Field(default_factory=list)
