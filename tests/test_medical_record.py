import time
import unittest
from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import ConnectionFailure

from src.data.connection import ActionFailed, Collections
from src.data.repositories import medical_record as medical_record_repo
from src.models.repositories import MedicalRecord
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestMedicalRecordRepository(BaseMongoTest):
	"""Test class for the 'happy path' of medical record repository functions."""

	def setUp(self):
		"""Set up a clean test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.MEDICAL_RECORDS]
		medical_record_repo.init(collection_name=self.test_collection, drop=True)
		self.patient_id = str(ObjectId())
		self.doctor_id = str(ObjectId())

	def test_init_functionality(self):
		"""Test that the init function correctly sets up the collection."""
		self.assertIn(self.test_collection, self.db.list_collection_names())

	def test_create_medical_record(self):
		"""Test successful creation of a medical record."""
		record_id = medical_record_repo.create_medical_record(
			patient_id=self.patient_id,
			doctor_id=self.doctor_id,
			record_type="Consultation",
			details={"symptoms": "Fever, cough", "diagnosis": "Common cold"},
			collection_name=self.test_collection
		)
		self.assertIsInstance(record_id, str)
		doc = self.get_doc_by_id(Collections.MEDICAL_RECORDS, record_id)
		self.assertIsNotNone(doc)
		self.assertEqual(doc["record_type"], "Consultation") # type: ignore
		self.assertEqual(str(doc["patient_id"]), self.patient_id) # type: ignore

	def test_get_records_for_patient(self):
		"""Test retrieving all records for a patient, verifying sorting and filtering."""
		other_patient_id = str(ObjectId())
		# Create records, sleeping to ensure distinct creation timestamps for sorting check
		r1_id = medical_record_repo.create_medical_record(self.patient_id, self.doctor_id, "R1", {}, collection_name=self.test_collection)
		time.sleep(0.01)
		medical_record_repo.create_medical_record(other_patient_id, self.doctor_id, "Other", {}, collection_name=self.test_collection)
		time.sleep(0.01)
		r2_id = medical_record_repo.create_medical_record(self.patient_id, self.doctor_id, "R2", {}, collection_name=self.test_collection)

		# Retrieve records for the target patient
		records = medical_record_repo.get_records_for_patient(self.patient_id, collection_name=self.test_collection)

		# Verify correct filtering, count, and type
		self.assertEqual(len(records), 2)
		self.assertIsInstance(records[0], MedicalRecord)

		# Verify sorting (ascending by creation date)
		self.assertEqual(records[0].id, r1_id)
		self.assertEqual(records[1].id, r2_id)

		# Test edge case: patient with no records
		no_records = medical_record_repo.get_records_for_patient(str(ObjectId()), collection_name=self.test_collection)
		self.assertEqual(len(no_records), 0)


class TestMedicalRecordRepositoryExceptions(BaseMongoTest):
	"""Test class for the exception handling of medical record repository functions."""

	def setUp(self):
		"""Set up the test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.MEDICAL_RECORDS]
		medical_record_repo.init(collection_name=self.test_collection, drop=True)
		self.patient_id = str(ObjectId())
		self.doctor_id = str(ObjectId())

	def test_invalid_id_raises_action_failed(self):
		"""Test that functions raise ActionFailed when given a malformed ObjectId string."""
		with self.assertRaises(ActionFailed):
			medical_record_repo.create_medical_record("bad-id", self.doctor_id, "t", {}, collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			medical_record_repo.get_records_for_patient("bad-id", collection_name=self.test_collection)

	@patch('src.data.repositories.medical_record.get_collection')
	def test_all_functions_raise_on_connection_error(self, mock_get_collection):
		"""Test that all repo functions catch generic PyMongoErrors and raise ActionFailed."""
		mock_get_collection.side_effect = ConnectionFailure("Simulated connection error")

		with self.assertRaises(ActionFailed):
			medical_record_repo.init(collection_name=self.test_collection, drop=True)
		with self.assertRaises(ActionFailed):
			medical_record_repo.create_medical_record(self.patient_id, self.doctor_id, "t", {}, collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			medical_record_repo.get_records_for_patient(self.patient_id, collection_name=self.test_collection)

if __name__ == "__main__":
	logger().info("Starting MongoDB repository integration tests...")
	unittest.main(verbosity=2)
	logger().info("Tests completed and database connection closed.")
