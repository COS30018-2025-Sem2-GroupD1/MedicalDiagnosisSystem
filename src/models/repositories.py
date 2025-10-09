# src/models/repositories.py

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

PyObjectId = Annotated[str, BeforeValidator(str)]

class BaseMongoModel(BaseModel):
	"""A base Pydantic model for all MongoDB documents."""
	id: PyObjectId = Field(..., alias="_id")

	model_config = ConfigDict(
		frozen=True,
		from_attributes=True,
		arbitrary_types_allowed=True
	)

class Account(BaseMongoModel):
	"""A Pydantic model for an account."""
	name: str
	role: str
	specialty: str | None = None
	created_at: datetime
	updated_at: datetime
	last_seen: datetime

class Patient(BaseMongoModel):
	"""A Pydantic model for a patient."""
	name: str
	age: int
	sex: str
	ethnicity: str
	created_at: datetime
	updated_at: datetime
	address: str | None = None
	phone: str | None = None
	email: str | None = None
	medications: list[str] | None = None
	past_assessment_summary: str | None = None
	assigned_doctor_id: PyObjectId | None = None

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
	account_id: PyObjectId
	patient_id: PyObjectId
	title: str
	created_at: datetime
	updated_at: datetime
	messages: list[Message] = Field(default_factory=list)
