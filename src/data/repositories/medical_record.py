# src/data/repositories/medical_record.py
"""
Medical record management operations for MongoDB.
Medical records are structured, factual pieces of information about a patient.

## Fields
	_id: index
	patient_id: The patient this record belongs to
	doctor_id: The doctor who created or is associated with this record
	record_type: The category of the record (e.g., 'Consultation', 'LabResult')
	details: An object containing the specific, structured data for the record
	created_at: The timestamp when the record was created
	updated_at: The timestamp when the record was last modified
"""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING
from pymongo.errors import ConnectionFailure, PyMongoError, WriteError

from src.data.connection import (ActionFailed, Collections, get_collection,
                                 setup_collection)
from src.models.medical import MedicalRecord
from src.utils.logger import logger


def init(
	*,
	collection_name: str = Collections.MEDICAL_RECORDS,
	validator_path: str = "schemas/medical_record_validator.json",
	drop: bool = False
):
	"""Initializes the medical_records collection, applying schema validation."""
	try:
		if drop:
			get_collection(collection_name).drop()
		setup_collection(collection_name, validator_path)
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to initialize collection '{collection_name}': {e}")
		raise ActionFailed(f"Database operation failed during initialization: {e}") from e

def create_medical_record(
	patient_id: str,
	doctor_id: str,
	record_type: str,
	details: dict[str, Any],
	*,
	collection_name: str = Collections.MEDICAL_RECORDS
) -> str:
	"""Creates a new medical record, raising ActionFailed on error."""
	now = datetime.now(timezone.utc)
	try:
		collection = get_collection(collection_name)
		record_data = {
			"patient_id": ObjectId(patient_id),
			"doctor_id": ObjectId(doctor_id),
			"record_type": record_type,
			"details": details,
			"created_at": now,
			"updated_at": now
		}
		result = collection.insert_one(record_data)
		return str(result.inserted_id)
	except InvalidId as e:
		logger().error(f"Invalid ObjectId format provided for medical record: {e}")
		raise ActionFailed("Patient ID or Doctor ID is not a valid format.") from e
	except (WriteError, ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to create medical record: {e}")
		raise ActionFailed("A database error occurred while creating the medical record.") from e

def get_records_for_patient(
	patient_id: str,
	*,
	collection_name: str = Collections.MEDICAL_RECORDS
) -> list[MedicalRecord]:
	"""Retrieves all medical records for a patient, sorted by creation date."""
	try:
		obj_patient_id = ObjectId(patient_id)
		collection = get_collection(collection_name)
		cursor = collection.find(
			{"patient_id": obj_patient_id}
		).sort("created_at", ASCENDING)

		return [MedicalRecord.model_validate(doc) for doc in cursor]
	except InvalidId as e:
		logger().error(f"Invalid patient_id format for get_records_for_patient: '{patient_id}'")
		raise ActionFailed("The provided patient ID is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error retrieving records for patient '{patient_id}': {e}")
		raise ActionFailed("A database error occurred while retrieving medical records.") from e
