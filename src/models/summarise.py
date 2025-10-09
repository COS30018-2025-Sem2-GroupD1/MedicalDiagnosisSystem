# src/models/summarise.py

from pydantic import BaseModel, Field


class SummariseRequest(BaseModel):
	"""Request model for the text summarisation endpoint."""
	text: str
	max_words: int = Field(default=5, ge=3, le=10) # Enforce reasonable limits


class SummariseResponse(BaseModel):
	"""Response model for the text summarisation endpoint."""
	title: str
