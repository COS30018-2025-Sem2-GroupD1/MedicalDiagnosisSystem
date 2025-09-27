# data/patient/operations.py
"""
Patient management operations for MongoDB.
A patient is a person who has been assigned to a doctor for treatment.

## Fields
	_id: index
	name: The name of the patient
	age: How old the patient is
	sex: Male or female
	ethnicity: Geneological information
	address: Where they live
	phone: What their phone number is
	email: What their email address it
	medications: Any medications they are currently taking
	past_assessment_summary: Summarisation of past assessments
	assigned_doctor_id: The id of the account assigned to this patient
	created_at: The timestamp when the patient was created
	updated_at: The timestamp when the patient data was last modified
"""

import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import (ConnectionFailure, DuplicateKeyError,
                            OperationFailure, PyMongoError)

from src.data.connection import ActionFailed, create_collection, get_collection
from src.utils.logger import logger

PATIENTS_COLLECTION = "patients"

def create():
	#get_collection(PATIENTS_COLLECTION).drop()
	create_collection(PATIENTS_COLLECTION, "schemas/patient_validator.json")
	get_collection(PATIENTS_COLLECTION).create_index("assigned_doctor_id")

def get_patient_by_id(patient_id: str) -> dict[str, Any] | None:
	logger().info(f"Searching for patient with id '{patient_id}'")
	try:
		collection = get_collection(PATIENTS_COLLECTION)
		return collection.find_one({"_id": ObjectId(patient_id)})
	except Exception as e:
		logger().error(f"Error in get_patient_by_id: {e}")
		return None

def create_patient(
	name: str,
	age: int,
	sex: str,
	ethnicity: str,
	address: str | None = None,
	phone: str | None = None,
	email: str | None = None,
	medications: list[str] | None = None,
	past_assessment_summary: str | None = None,
	assigned_doctor_id: str | None = None
) -> str:
	collection = get_collection(PATIENTS_COLLECTION)
	now = datetime.now(timezone.utc)
	doc = {
		"name": name,
		"age": age,
		"sex": sex,
		"ethnicity": ethnicity,
		"address": address or "",
		"phone": phone or "",
		"email": email or "",
		"medications": medications or [],
		"past_assessment_summary": past_assessment_summary or "",
		"assigned_doctor_id": assigned_doctor_id or "",
		"created_at": now,
		"updated_at": now
	}
	result = collection.insert_one(doc)
	return str(result.inserted_id)

def update_patient_profile(patient_id: str, updates: dict[str, Any]) -> int:
	try:
		collection = get_collection(PATIENTS_COLLECTION)
		updates["updated_at"] = datetime.now(timezone.utc)
		result = collection.update_one({"_id": ObjectId(patient_id)}, {"$set": updates})
		return result.modified_count
	except Exception as e:
		logger().error(f"Error in update_patient_profile: {e}")
		return 0

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
