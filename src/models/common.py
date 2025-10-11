# src/models/common.py

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

PyObjectId = Annotated[str, BeforeValidator(str)]

class BaseMongoModel(BaseModel):
	"""A base Pydantic model for all MongoDB documents."""
	id: PyObjectId = Field(..., validation_alias="_id")

	model_config = ConfigDict(
		frozen=True,
		from_attributes=True,
		arbitrary_types_allowed=True,
		populate_by_name=True
	)
