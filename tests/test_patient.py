import unittest
from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import ConnectionFailure

from src.data.connection import (ActionFailed, Collections, close_connection,
                                 get_collection)
from src.data.repositories import patient as patient_repo
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestPatientRepository(BaseMongoTest):
	"""Test class for the 'happy path' and edge cases of patient repository functions."""

	def setUp(self):
		"""Set up a clean test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.PATIENT]
		patient_repo.init(collection_name=self.test_collection, drop=True)

	def test_init_functionality(self):
		"""Test that the init function correctly sets up the collection and its indexes."""
		self.assertIn(self.test_collection, self.db.list_collection_names())
		index_info = get_collection(self.test_collection).index_information()
		self.assertIn("assigned_doctor_id_1", index_info)

	def test_create_patient(self):
		"""Test patient creation with minimal and full data."""
		# Test minimal creation
		patient_id = patient_repo.create_patient(
			"John Doe", 45, "Male", "Caucasian", collection_name=self.test_collection
		)
		self.assertIsInstance(patient_id, str)
		doc = self.get_doc_by_id(Collections.PATIENT, patient_id)
		self.assertIsNotNone(doc)
		self.assertEqual(doc["name"], "John Doe") # type: ignore

		# Test full creation with all optional parameters
		doctor_id = str(ObjectId())
		full_id = patient_repo.create_patient(
			name="Jane Doe",
			age=30,
			sex="Female",
			ethnicity="Asian",
			address="123 Wellness Way",
			phone="555-123-4567",
			email="jane.doe@example.com",
			medications=["Lisinopril", "Metformin"],
			past_assessment_summary="Routine check-up, generally healthy.",
			assigned_doctor_id=doctor_id,
			collection_name=self.test_collection
		)
		self.assertIsInstance(full_id, str)
		full_doc = self.get_doc_by_id(Collections.PATIENT, full_id)

		# Verify all fields were saved correctly
		self.assertIsNotNone(full_doc)
		self.assertEqual(full_doc["address"], "123 Wellness Way") # type: ignore
		self.assertEqual(full_doc["phone"], "555-123-4567") # type: ignore
		self.assertEqual(full_doc["email"], "jane.doe@example.com") # type: ignore
		self.assertEqual(len(full_doc["medications"]), 2) # type: ignore
		self.assertIn("Lisinopril", full_doc["medications"]) # type: ignore
		self.assertEqual(full_doc["past_assessment_summary"], "Routine check-up, generally healthy.") # type: ignore
		self.assertEqual(str(full_doc["assigned_doctor_id"]), doctor_id) # type: ignore

	def test_get_patient_by_id(self):
		"""Test retrieving an existing patient by ID."""
		patient_id = patient_repo.create_patient("GetMe", 33, "Female", "Other", collection_name=self.test_collection)
		patient = patient_repo.get_patient_by_id(patient_id, collection_name=self.test_collection)
		self.assertIsNotNone(patient)
		self.assertEqual(patient["_id"], patient_id) # type: ignore
		# Test retrieval of a non-existent patient returns None
		self.assertIsNone(patient_repo.get_patient_by_id(str(ObjectId()), collection_name=self.test_collection))

	def test_update_patient_profile(self):
		"""Test successfully updating an existing patient's profile."""
		patient_id = patient_repo.create_patient("Update Test", 25, "Male", "Hispanic", collection_name=self.test_collection)
		updates = {"age": 26, "phone": "555-9999"}
		modified_count = patient_repo.update_patient_profile(patient_id, updates, collection_name=self.test_collection)
		self.assertEqual(modified_count, 1)
		doc = self.get_doc_by_id(Collections.PATIENT, patient_id)
		self.assertEqual(doc["age"], 26) # type: ignore
		# Test updating a non-existent patient returns a modified count of 0
		self.assertEqual(patient_repo.update_patient_profile(str(ObjectId()), {"name": "Ghost"}, collection_name=self.test_collection), 0)

	def test_search_patients(self):
		"""Test patient search functionality with various queries and limits."""
		patient_repo.create_patient("Alice Smith", 30, "Female", "Asian", collection_name=self.test_collection)
		patient_repo.create_patient("Bob Smith", 45, "Male", "Caucasian", collection_name=self.test_collection)
		results = patient_repo.search_patients("smith", collection_name=self.test_collection)
		self.assertEqual(len(results), 2)
		self.assertEqual(results[0]["name"], "Alice Smith")
		# Test limit parameter
		self.assertEqual(len(patient_repo.search_patients("s", limit=1, collection_name=self.test_collection)), 1)


class TestPatientRepositoryExceptions(BaseMongoTest):
	"""Test class for the exception handling of all patient repository functions."""

	def setUp(self):
		"""Set up the test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.PATIENT]
		patient_repo.init(collection_name=self.test_collection, drop=True)

	def test_write_error_raises_action_failed(self):
		"""Test that creating or updating with data violating schema raises ActionFailed."""
		# Test creating a patient with a 'sex' value not in the schema's enum
		with self.assertRaises(ActionFailed):
			patient_repo.create_patient("Schema Test", 25, "InvalidValue", "Other", collection_name=self.test_collection)

		# Test updating a patient with an invalid value
		patient_id = patient_repo.create_patient("UpdateSchema", 30, "Male", "Other", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			patient_repo.update_patient_profile(patient_id, {"ethnicity": 123}, collection_name=self.test_collection)

	def test_invalid_id_raises_action_failed(self):
		"""Test that functions raise ActionFailed when given a malformed ObjectId string."""
		with self.assertRaises(ActionFailed):
			patient_repo.create_patient("Test", 30, "Male", "Other", assigned_doctor_id="not-a-valid-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			patient_repo.get_patient_by_id("not-a-valid-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			patient_repo.update_patient_profile("not-a-valid-id", {"name": "test"}, collection_name=self.test_collection)

	@patch('src.data.repositories.patient.get_collection')
	def test_all_functions_raise_on_connection_error(self, mock_get_collection):
		"""Test that all repo functions catch generic PyMongoErrors and raise ActionFailed."""
		mock_get_collection.side_effect = ConnectionFailure("Simulated connection error")

		with self.assertRaises(ActionFailed):
			patient_repo.init(collection_name=self.test_collection, drop=True)
		with self.assertRaises(ActionFailed):
			patient_repo.create_patient("Test", 30, "Male", "Other", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			patient_repo.get_patient_by_id(str(ObjectId()), collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			patient_repo.update_patient_profile(str(ObjectId()), {"name": "test"}, collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			patient_repo.search_patients("test", collection_name=self.test_collection)

if __name__ == "__main__":
	try:
		logger().info("Starting MongoDB repository integration tests...")
		unittest.main(verbosity=2)
	finally:
		logger().info("Tests completed and database connection closed.")
		close_connection()
