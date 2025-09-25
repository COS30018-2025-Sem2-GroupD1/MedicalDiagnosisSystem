# api/routes/system.py

import time

from fastapi import APIRouter, Depends

from src.core.state import MedicalState, get_state
from src.data.repositories.account import ACCOUNTS_COLLECTION
from src.data.repositories.medical import (MEDICAL_MEMORY_COLLECTION,
                                           MEDICAL_RECORDS_COLLECTION)
from src.data.repositories.message import CHAT_MESSAGES_COLLECTION
from src.data.repositories.patient import PATIENTS_COLLECTION
from src.data.repositories.session import CHAT_SESSIONS_COLLECTION

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health")
async def health_check(state: MedicalState = Depends(get_state)):
	"""Health check endpoint"""
	return {
		"status": "healthy",
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
		"components": {
			"memory_system": "operational",
			"embedding_client": "operational" if state.embedding_client.is_available() else "fallback_mode",
			"api_rotator": "operational",
			"gemini_keys_available": len([k for k in state.gemini_rotator.keys if k]) > 0,
			"nvidia_keys_available": len([k for k in state.nvidia_rotator.keys if k]) > 0
		}
	}

@router.get("/database")
async def get_database():
	"""List meta information about all collections in the database."""
	from src.data.connection import get_collection

	collections = [
		ACCOUNTS_COLLECTION,
		CHAT_SESSIONS_COLLECTION,
		CHAT_MESSAGES_COLLECTION,
		MEDICAL_RECORDS_COLLECTION,
		MEDICAL_MEMORY_COLLECTION,
		PATIENTS_COLLECTION
	]

	result = {}
	for name in collections:
		collection = get_collection(name)
		indexes = []
		for idx in collection.list_indexes():
			indexes.append({
				"name": idx["name"],
				"keys": list(idx["key"].items())
			})

		stats = collection.estimated_document_count()
		# Get sample document to extract field names
		sample = collection.find_one()
		fields = list(sample.keys()) if sample else []

		result[name] = {
			"document_count": stats,
			"indexes": indexes,
			"fields": fields
		}

	return {
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
		"collections": result
	}
