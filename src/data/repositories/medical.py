# data/repositories/medical.py

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import (ConnectionFailure, DuplicateKeyError,
                            OperationFailure, PyMongoError)

from src.data.repositories.base import ActionFailed, get_collection

MEDICAL_RECORDS_COLLECTION = "medical_records"
MEDICAL_CONTEXT_COLLECTION = "medical_context"

def create_medical_record(
	record_data: dict[str, Any],
	/, *,
	collection_name: str = MEDICAL_RECORDS_COLLECTION
) -> str:
	"""Creates a new medical record."""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	record_data.update({"created_at": now, "updated_at": now})
	result = collection.insert_one(record_data)
	return str(result.inserted_id)

def get_user_medical_records(
	user_id: str,
	/, *,
	collection_name: str = MEDICAL_RECORDS_COLLECTION
) -> list[dict[str, Any]]:
	"""Retrieves all medical records for a specific user."""
	collection = get_collection(collection_name)
	cursor = collection.find(
		{"user_id": user_id}
	).sort(
		"created_at", ASCENDING
	)
	return list(cursor)

def add_medical_context(
	user_id: str,
	/,
	summary: str,
	*,
	collection_name: str = MEDICAL_CONTEXT_COLLECTION
) -> str:
	"""Adds a medical context summary for a user."""
	collection = get_collection(collection_name)
	doc = {
		"_id": str(ObjectId()),
		"user_id": user_id,
		"summary": summary,
		"timestamp": datetime.now(timezone.utc)
	}
	result = collection.insert_one(doc)
	return str(result.inserted_id)

def get_medical_context(
	user_id: str,
	/,
	limit: int | None = None,
	*,
	collection_name: str = MEDICAL_CONTEXT_COLLECTION
) -> list[dict[str, Any]]:
	"""Retrieves medical context summaries for a user."""
	collection = get_collection(collection_name)
	cursor = collection.find(
		{"user_id": user_id}
	).sort(
		"timestamp", DESCENDING
	)
	if limit:
		cursor = cursor.limit(limit)
	return list(cursor)
