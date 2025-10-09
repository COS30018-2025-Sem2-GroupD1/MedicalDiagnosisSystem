# src/models/medical.py

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.models.common import BaseMongoModel, PyObjectId


class MedicalRecord(BaseMongoModel):
	"""A Pydantic model for a structured medical record."""
	patient_id: PyObjectId
	doctor_id: PyObjectId
	record_type: str
	details: dict[str, Any]
	created_at: datetime
	updated_at: datetime

class MedicalMemory(BaseMongoModel):
	"""A Pydantic model for a medical memory summary, used for semantic search."""
	patient_id: PyObjectId
	doctor_id: PyObjectId
	session_id: PyObjectId | None = None
	summary: str
	embedding: list[float] | None = None
	created_at: datetime

class SemanticSearchResult(BaseModel):
	"""A Pydantic model for the result of a semantic search."""
	summary: str
	similarity_score: float
	created_at: datetime
	session_id: PyObjectId | None = None

	model_config = ConfigDict(frozen=True, from_attributes=True)
