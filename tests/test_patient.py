import unittest

from bson import ObjectId

from src.data.connection import Collections, close_connection, get_collection
from src.data.repositories import patient as patient_repo
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestPatientRepository(BaseMongoTest):

	def setUp(self):
		"""Set up a clean test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.PATIENT]
		# Initialize the collection with schema and indexes for each test
		patient_repo.init(collection_name=self.test_collection, drop=True)

	def test_init_functionality(self):
		"""Test that the init function correctly sets up the collection and its indexes."""
		# Verify collection exists
		self.assertIn(self.test_collection, self.db.list_collection_names())

		# Verify that the index on assigned_doctor_id was created
		index_info = get_collection(self.test_collection).index_information()
		self.assertIn("assigned_doctor_id_1", index_info)

	def test_create_patient(self):
		"""Test patient creation with required and optional fields."""
		# Test minimal creation
		patient_id = patient_repo.create_patient(
			name="John Doe",
			age=45,
			sex="Male",
			ethnicity="Caucasian",
			collection_name=self.test_collection
		)
		self.assertIsInstance(patient_id, str)
		doc = self.get_doc_by_id(Collections.PATIENT, patient_id)
		self.assertIsNotNone(doc)
		self.assertEqual(doc["name"], "John Doe") # type: ignore
		self.assertIn("created_at", doc) # type: ignore
		self.assertEqual(doc["created_at"], doc["updated_at"]) # type: ignore

		# Test full creation
		doctor_id = ObjectId()
		patient_id_full = patient_repo.create_patient(
			name="Jane Doe",
			age=30,
			sex="Female",
			ethnicity="Asian",
			address="123 Test St",
			phone="555-0123",
			email="jane@test.com",
			medications=["Med A", "Med B"],
			past_assessment_summary="Previous checkup normal",
			assigned_doctor_id=str(doctor_id),
			collection_name=self.test_collection
		)
		doc_full = self.get_doc_by_id(Collections.PATIENT, patient_id_full)
		self.assertIsNotNone(doc_full)
		self.assertEqual(doc_full["email"], "jane@test.com") # type: ignore
		self.assertEqual(len(doc_full["medications"]), 2) # type: ignore
		self.assertIsInstance(doc_full["assigned_doctor_id"], ObjectId) # type: ignore
		self.assertEqual(doc_full["assigned_doctor_id"], doctor_id) # type: ignore

	def test_get_patient_by_id(self):
		"""Test retrieving a single patient by their ID."""
		patient_id = patient_repo.create_patient("GetMe", 33, "Female", "Other", collection_name=self.test_collection)

		patient = patient_repo.get_patient_by_id(patient_id, collection_name=self.test_collection)
		self.assertIsNotNone(patient)
		self.assertEqual(patient["_id"], patient_id) # type: ignore
		self.assertEqual(patient["name"], "GetMe") # type: ignore
		self.assertIsInstance(patient["_id"], str) # type: ignore

		# Test retrieval of a non-existent patient returns None
		non_existent_id = str(ObjectId())
		patient = patient_repo.get_patient_by_id(non_existent_id, collection_name=self.test_collection)
		self.assertIsNone(patient)

	def test_update_patient_profile(self):
		"""Test patient profile updates for existing and non-existing patients."""
		patient_id = patient_repo.create_patient(
			name="Update Test",
			age=25,
			sex="Male",
			ethnicity="Hispanic",
			collection_name=self.test_collection
		)
		original_doc = self.get_doc_by_id(Collections.PATIENT, patient_id)
		self.assertIsNotNone(original_doc)

		# Test partial update
		updates = {"age": 26, "phone": "555-9999"}
		modified_count = patient_repo.update_patient_profile(
			patient_id, updates, collection_name=self.test_collection
		)
		self.assertEqual(modified_count, 1)

		updated_doc = self.get_doc_by_id(Collections.PATIENT, patient_id)
		self.assertIsNotNone(updated_doc)
		self.assertEqual(updated_doc["age"], 26) # type: ignore
		self.assertEqual(updated_doc["phone"], "555-9999") # type: ignore
		self.assertLess(original_doc["updated_at"], updated_doc["updated_at"]) # type: ignore

		# Test updating a non-existent patient returns a modified count of 0
		non_existent_id = str(ObjectId())
		modified_count = patient_repo.update_patient_profile(
			non_existent_id, {"name": "Ghost"}, collection_name=self.test_collection
		)
		self.assertEqual(modified_count, 0)

	def test_search_patients(self):
		"""Test patient search functionality with various queries and limits."""
		# Create test patients
		patient_repo.create_patient("Alice Smith", 30, "Female", "Asian", collection_name=self.test_collection)
		patient_repo.create_patient("Bob Smith", 45, "Male", "Caucasian", collection_name=self.test_collection)
		patient_repo.create_patient("Charlie Brown", 60, "Male", "African", collection_name=self.test_collection)

		# Test search by partial name, should be case-insensitive
		results = patient_repo.search_patients("smith", collection_name=self.test_collection)
		self.assertEqual(len(results), 2)

		# Test search is sorted ascending by name
		self.assertEqual(results[0]["name"], "Alice Smith")
		self.assertEqual(results[1]["name"], "Bob Smith")

		# Test case-insensitive exact match
		results = patient_repo.search_patients("charlie brown", collection_name=self.test_collection)
		self.assertEqual(len(results), 1)
		self.assertEqual(results[0]["name"], "Charlie Brown")

		# Test limit parameter
		results = patient_repo.search_patients("S", limit=1, collection_name=self.test_collection)
		self.assertEqual(len(results), 1)

		# Test query with no results
		results = patient_repo.search_patients("Zebra", collection_name=self.test_collection)
		self.assertEqual(len(results), 0)

		# Test empty query string returns an empty list
		results = patient_repo.search_patients("", collection_name=self.test_collection)
		self.assertEqual(len(results), 0)

if __name__ == "__main__":
	try:
		logger().info("Starting MongoDB repository integration tests...")
		unittest.main(verbosity=2)
	finally:
		logger().info("Tests completed and database connection closed.")
		close_connection()
