# src/models/patient.py

from datetime import datetime

from src.models.common import BaseMongoModel, PyObjectId


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
