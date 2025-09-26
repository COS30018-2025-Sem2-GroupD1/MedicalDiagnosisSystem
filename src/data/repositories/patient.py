# data/patient/operations.py
"""
Patient management operations for MongoDB.
A patient is a person who has been assigned to a doctor for treatment.

## Fields
	_id: index
	name:
	age:
	sex:
	address:
	phone:
	email:
	medications:
	past_assessment_summary:
	assigned_doctor_id:
	created_at:
	updated_at:
"""

import re
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING
from pymongo.errors import (ConnectionFailure, DuplicateKeyError,
                            OperationFailure, PyMongoError)

from src.data.connection import ActionFailed, create_collection, get_collection
from src.utils.logger import logger

PATIENTS_COLLECTION = "patients"

def create():
	#get_collection(PATIENTS_COLLECTION).drop()
	create_collection(PATIENTS_COLLECTION, "schemas/patient_validator.json")

def _generate_patient_id() -> str:
	"""Generate zero-padded 8-digit ID"""
	import random
	return f"{random.randint(0, 99999999):08d}"


def get_patient_by_id(patient_id: str) -> dict[str, Any] | None:
	collection = get_collection(PATIENTS_COLLECTION)
	return collection.find_one({"patient_id": patient_id})


def create_patient(
	*,
	name: str,
	age: int,
	sex: str,
	address: str | None = None,
	phone: str | None = None,
	email: str | None = None,
	medications: list[str] | None = None,
	past_assessment_summary: str | None = None,
	assigned_doctor_id: str | None = None
) -> dict[str, Any]:
	collection = get_collection(PATIENTS_COLLECTION)
	now = datetime.now(timezone.utc)
	# Ensure unique 8-digit id
	for _ in range(10):
		pid = _generate_patient_id()
		if not collection.find_one({"patient_id": pid}):
			break
	else:
		raise RuntimeError("Failed to generate unique patient ID")
	doc = {
		"patient_id": pid,
		"name": name,
		"age": age,
		"sex": sex,
		"address": address,
		"phone": phone,
		"email": email,
		"medications": medications or [],
		"past_assessment_summary": past_assessment_summary or "",
		"assigned_doctor_id": assigned_doctor_id,
		"created_at": now,
		"updated_at": now
	}
	collection.insert_one(doc)
	return doc


def update_patient_profile(patient_id: str, updates: dict[str, Any]) -> int:
	collection = get_collection(PATIENTS_COLLECTION)
	updates["updated_at"] = datetime.now(timezone.utc)
	result = collection.update_one({"patient_id": patient_id}, {"$set": updates})
	return result.modified_count


def search_patients(query: str, limit: int = 10) -> list[dict[str, Any]]:
	"""Search patients by name (case-insensitive starts-with/contains) or partial patient_id."""
	collection = get_collection(PATIENTS_COLLECTION)
	if not query:
		return []

	logger().info(f"Searching patients with query: '{query}', limit: {limit}")

	# Build a regex for name search and patient_id partial match
	pattern = re.compile(re.escape(query), re.IGNORECASE)

	try:
		cursor = collection.find({
			"$or": [
				{"name": {"$regex": pattern}},
				{"patient_id": {"$regex": pattern}}
			]
		}).sort("name", ASCENDING).limit(limit)
		results = []
		for p in cursor:
			p["_id"] = str(p.get("_id")) if p.get("_id") else None
			results.append(p)
		logger().info(f"Found {len(results)} patients matching query")
		return results
	except Exception as e:
		logger().error(f"Error in search_patients: {e}")
		return []
