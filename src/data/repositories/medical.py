# data/repositories/medical.py
"""
Medical records and memory management operations for MongoDB.

@Note Could this be split into two? One for records and one for memory.
"""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import (ConnectionFailure, DuplicateKeyError,
                            OperationFailure, PyMongoError)

from src.data.connection import ActionFailed, get_collection
from src.utils.logger import logger

MEDICAL_RECORDS_COLLECTION = "medical_records"
MEDICAL_MEMORY_COLLECTION = "medical_memory"

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
	collection_name: str = MEDICAL_MEMORY_COLLECTION
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
	collection_name: str = MEDICAL_MEMORY_COLLECTION
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

# TODO Delete context

def save_memory_summary(
	*,
	patient_id: str,
	doctor_id: str,
	summary: str,
	embedding: list[float] | None = None,
	created_at: datetime | None = None,
	collection_name: str = MEDICAL_MEMORY_COLLECTION
) -> str:
	collection = get_collection(collection_name)
	ts = created_at or datetime.now(timezone.utc)
	doc = {
		"patient_id": patient_id,
		"doctor_id": doctor_id,
		"summary": summary,
		"created_at": ts
	}
	if embedding is not None:
		doc["embedding"] = embedding
	result = collection.insert_one(doc)
	return str(result.inserted_id)

def get_recent_memory_summaries(
	patient_id: str,
	/,
	*,
	limit: int = 20,
	collection_name: str = MEDICAL_MEMORY_COLLECTION
) -> list[str]:
	collection = get_collection(collection_name)
	docs = list(collection.find({"patient_id": patient_id}).sort("created_at", DESCENDING).limit(limit))
	return [d.get("summary", "") for d in docs]

def search_memory_summaries_semantic(
	patient_id: str,
	query_embedding: list[float],
	/,
	*,
	limit: int = 5,
	similarity_threshold: float = 0.5,  # >= 50% semantic similarity
	collection_name: str = MEDICAL_MEMORY_COLLECTION
) -> list[dict[str, Any]]:
	"""
	Search memory summaries using semantic similarity with embeddings.
	Returns list of {summary, similarity_score, created_at} sorted by similarity.
	"""
	collection = get_collection(collection_name)

	# Get all summaries with embeddings for this patient
	docs = list(collection.find({
		"patient_id": patient_id,
		"embedding": {"$exists": True}
	}))

	if not docs:
		return []

	# Calculate similarities
	import numpy as np
	query_vec = np.array(query_embedding, dtype="float32")
	results = []

	for doc in docs:
		embedding = doc.get("embedding")
		if not embedding:
			continue

		# Calculate cosine similarity
		doc_vec = np.array(embedding, dtype="float32")
		dot_product = np.dot(query_vec, doc_vec)
		norm_query = np.linalg.norm(query_vec)
		norm_doc = np.linalg.norm(doc_vec)

		if norm_query == 0 or norm_doc == 0:
			similarity = 0.0
		else:
			similarity = float(dot_product / (norm_query * norm_doc))

		if similarity >= similarity_threshold:
			results.append({
					"summary": doc.get("summary", ""),
					"similarity_score": similarity,
					"created_at": doc.get("created_at"),
					"session_id": doc.get("session_id")  # if we add this field later
			})

	# Sort by similarity (highest first) and return top results
	results.sort(key=lambda x: x["similarity_score"], reverse=True)
	return results[:limit]
