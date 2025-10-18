# src/models/information.py

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InfoChunkMetadata(BaseModel):
	"""Pydantic model for the nested metadata object."""
	parent_id: str
	source: str
	task: str
	sequence: int
	total_chunks: int
	content_type: str
	related_chunks: list[str] | None = None
	chunk_length: int | None = None
	created_timestamp: datetime | None = None

	model_config = ConfigDict(
		frozen=True,
		from_attributes=True,
		populate_by_name=True
	)

class InfoChunk(BaseModel):
	"""Pydantic model for the MongoDB collection."""
	chunk_id: str
	content: str
	embedding: list[float]
	embedding_model: str
	embedding_dim: int = Field(..., gt=0)
	metadata: InfoChunkMetadata

	model_config = ConfigDict(
		frozen=True,
		from_attributes=True,
		populate_by_name=True
	)
