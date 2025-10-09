# src/data/repositories/patient.py
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
from bson.errors import InvalidId
from pymongo import ASCENDING
from pymongo.errors import ConnectionFailure, PyMongoError, WriteError

from src.data.connection import (ActionFailed, Collections, get_collection,
                                 setup_collection)
from src.models.repositories import Patient
from src.utils.logger import logger


def init(
	*,
	collection_name: str = Collections.PATIENT,
	validator_path: str = "schemas/patient_validator.json",
	drop: bool = False
):
	"""Initializes the collection, applying schema and indexes."""
	try:
		if drop:
			get_collection(collection_name).drop()
		setup_collection(collection_name, validator_path)
		get_collection(collection_name).create_index("assigned_doctor_id")
		logger("Init").info(f"Created index on assigned_doctor_id in '{collection_name}'")
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to initialize collection '{collection_name}': {e}")
		raise ActionFailed(f"Database operation failed during initialization: {e}") from e

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
	assigned_doctor_id: str | None = None,
	*,
	collection_name: str = Collections.PATIENT
) -> str:
	"""Creates a new patient record, raising ActionFailed on error."""
	now = datetime.now(timezone.utc)
	patient_data = {
		"name": name,
		"age": age,
		"sex": sex,
		"ethnicity": ethnicity,
		"created_at": now,
		"updated_at": now
	}
	# Add optional fields to the dictionary
	if address: patient_data["address"] = address
	if phone: patient_data["phone"] = phone
	if email: patient_data["email"] = email
	if medications: patient_data["medications"] = medications
	if past_assessment_summary: patient_data["past_assessment_summary"] = past_assessment_summary

	try:
		collection = get_collection(collection_name)
		if assigned_doctor_id:
			patient_data["assigned_doctor_id"] = ObjectId(assigned_doctor_id)

		result = collection.insert_one(patient_data)
		return str(result.inserted_id)
	except InvalidId as e:
		logger().error(f"Invalid assigned_doctor_id format: '{assigned_doctor_id}'")
		raise ActionFailed(f"The assigned doctor ID is not a valid format.") from e
	except WriteError as e:
		logger().error(f"Failed to create patient due to validation or write error: {e}")
		raise ActionFailed(f"Patient could not be created due to invalid data.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error while creating patient: {e}")
		raise ActionFailed(f"A database error occurred while creating the patient.") from e

def get_patient_by_id(
	patient_id: str,
	*,
	collection_name: str = Collections.PATIENT
) -> Patient | None:
	"""Gets a patient by ID. Returns a Pydantic Patient object or None."""
	logger().info(f"Searching for patient with id '{patient_id}'")
	try:
		obj_patient_id = ObjectId(patient_id)
		collection = get_collection(collection_name)
		patient_dict = collection.find_one({"_id": obj_patient_id})

		if patient_dict:
			return Patient.model_validate(patient_dict)
		return None
	except InvalidId as e:
		logger().error(f"Invalid patient_id format for get: '{patient_id}'")
		raise ActionFailed(f"The provided patient ID '{patient_id}' is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error in get_patient_by_id for ID '{patient_id}': {e}")
		raise ActionFailed(f"A database error occurred while retrieving the patient.") from e

# TODO Make this more rigidly typed, maybe merge with create_patient?
def update_patient_profile(
	patient_id: str,
	updates: dict[str, Any],
	*,
	collection_name: str = Collections.PATIENT
) -> int:
	"""Updates a patient's profile, raising ActionFailed on error."""
	try:
		obj_patient_id = ObjectId(patient_id)
		collection = get_collection(collection_name)
		updates["updated_at"] = datetime.now(timezone.utc)

		result = collection.update_one(
			{"_id": obj_patient_id},
			{"$set": updates}
		)
		return result.modified_count
	except InvalidId as e:
		logger().error(f"Invalid patient_id format for update: '{patient_id}'")
		raise ActionFailed(f"The provided patient ID '{patient_id}' is not a valid format.") from e
	except WriteError as e:
		logger().error(f"Failed to update patient '{patient_id}' due to validation or write error: {e}")
		raise ActionFailed(f"Patient profile could not be updated due to invalid data.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error in update_patient_profile for ID '{patient_id}': {e}")
		raise ActionFailed(f"A database error occurred while updating the patient profile.") from e

def search_patients(
	query: str,
	limit: int = 10,
	*,
	collection_name: str = Collections.PATIENT
) -> list[Patient]:
	"""Searches patients by name, returning a list of Pydantic Patient objects."""
	if not query:
		return []

	logger().info(f"Searching patients with query: '{query}', limit: {limit}")
	pattern = re.compile(re.escape(query), re.IGNORECASE)

	try:
		collection = get_collection(collection_name)
		cursor = collection.find({
			"name": {"$regex": pattern}
		}).sort("name", ASCENDING).limit(limit)

		patients = [Patient.model_validate(doc) for doc in cursor]
		logger().info(f"Found {len(patients)} patients matching query")
		return patients
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error during patient search for query '{query}': {e}")
		raise ActionFailed(f"A database error occurred during the patient search.") from e
