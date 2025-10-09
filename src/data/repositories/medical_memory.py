# src/data/repositories/medical_memory.py
"""
Medical memory management operations for MongoDB.
Medical memories are unstructured summaries, often with vector embeddings for semantic search.

## Fields
	_id: index
	patient_id: The patient this memory relates to
	doctor_id: The doctor involved in the context of this memory
	session_id: The chat session this memory was derived from (optional)
	summary: The unstructured text summary of the medical context
	embedding: The vector embedding of the summary for semantic search (optional)
	created_at: The timestamp when the memory was created
"""
from datetime import datetime, timezone

import numpy as np
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError, WriteError

from src.data.connection import (ActionFailed, Collections, get_collection,
                                 setup_collection)
from src.models.medical import MedicalMemory, SemanticSearchResult
from src.utils.logger import logger


def init(
	*,
	collection_name: str = Collections.MEDICAL_MEMORY,
	validator_path: str = "schemas/medical_memory_validator.json",
	drop: bool = False
):
	"""Initializes the medical_memory collection, applying schema validation."""
	try:
		if drop:
			get_collection(collection_name).drop()
		setup_collection(collection_name, validator_path)
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to initialize collection '{collection_name}': {e}")
		raise ActionFailed(f"Database operation failed during initialization: {e}") from e

def create_memory(
	patient_id: str,
	doctor_id: str,
	summary: str,
	session_id: str | None = None,
	embedding: list[float] | None = None,
	*,
	collection_name: str = Collections.MEDICAL_MEMORY
) -> str:
	"""Saves a new medical memory summary, raising ActionFailed on error."""
	try:
		collection = get_collection(collection_name)
		doc = {
			"patient_id": ObjectId(patient_id),
			"doctor_id": ObjectId(doctor_id),
			"summary": summary,
			"created_at": datetime.now(timezone.utc)
		}
		if session_id:
			doc["session_id"] = ObjectId(session_id)
		if embedding:
			doc["embedding"] = embedding

		result = collection.insert_one(doc)
		return str(result.inserted_id)
	except InvalidId as e:
		logger().error(f"Invalid ObjectId format provided for medical memory: {e}")
		raise ActionFailed("Patient, Doctor, or Session ID is not a valid format.") from e
	except (WriteError, ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to create medical memory: {e}")
		raise ActionFailed("A database error occurred while creating the medical memory.") from e

def get_recent_memories(
	patient_id: str,
	limit: int = 20,
	*,
	collection_name: str = Collections.MEDICAL_MEMORY
) -> list[MedicalMemory]:
	"""Retrieves the most recent memory summaries for a patient."""
	try:
		obj_patient_id = ObjectId(patient_id)
		collection = get_collection(collection_name)
		cursor = collection.find(
			{"patient_id": obj_patient_id}
		).sort("created_at", DESCENDING).limit(limit)

		return [MedicalMemory.model_validate(doc) for doc in cursor]
	except InvalidId as e:
		logger().error(f"Invalid patient_id format for get_recent_memories: '{patient_id}'")
		raise ActionFailed("The provided patient ID is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error retrieving recent memories for patient '{patient_id}': {e}")
		raise ActionFailed("A database error occurred while retrieving recent memories.") from e

def search_memories_semantic(
	patient_id: str,
	query_embedding: list[float],
	limit: int = 5,
	*,
	collection_name: str = Collections.MEDICAL_MEMORY
) -> list[SemanticSearchResult]:
	"""Searches memory summaries using semantic similarity with embeddings."""
	try:
		obj_patient_id = ObjectId(patient_id)
		collection = get_collection(collection_name)

		# In a real-world scenario, this would be an Atlas Vector Search query.
		# This implementation fetches all docs and calculates similarity in the client.
		docs = list(collection.find({
			"patient_id": obj_patient_id,
			"embedding": {"$exists": True}
		}))

		if not docs:
			return []

		query_vec = np.array(query_embedding, dtype="float32")
		results = []
		for doc in docs:
			doc_vec = np.array(doc["embedding"], dtype="float32")

			# Calculate cosine similarity
			dot_product = np.dot(query_vec, doc_vec)
			norm_query = np.linalg.norm(query_vec)
			norm_doc = np.linalg.norm(doc_vec)

			if norm_query > 0 and norm_doc > 0:
				similarity = float(dot_product / (norm_query * norm_doc))
				result_data = {
					"summary": doc["summary"],
					"similarity_score": similarity,
					"created_at": doc["created_at"],
					"session_id": doc.get("session_id")
				}
				results.append(SemanticSearchResult.model_validate(result_data))

		# Sort by similarity (highest first) and return top results
		results.sort(key=lambda x: x.similarity_score, reverse=True)
		return results[:limit]
	except InvalidId as e:
		logger().error(f"Invalid patient_id format for semantic search: '{patient_id}'")
		raise ActionFailed("The provided patient ID is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error during semantic search for patient '{patient_id}': {e}")
		raise ActionFailed("A database error occurred during the semantic search.") from e
