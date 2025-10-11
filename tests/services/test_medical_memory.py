import unittest
from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import ConnectionFailure

from src.data.connection import ActionFailed, Collections
from src.data.repositories import medical_memory as medical_memory_repo
from src.models.medical import MedicalMemory, SemanticSearchResult
from src.utils.logger import logger
from ..base_test import BaseMongoTest


class TestMedicalMemoryRepository(BaseMongoTest):
	"""Test class for the 'happy path' of medical memory repository functions."""

	def setUp(self):
		"""Set up a clean test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.MEDICAL_MEMORY]
		medical_memory_repo.init(collection_name=self.test_collection, drop=True)
		self.patient_id = str(ObjectId())
		self.doctor_id = str(ObjectId())
		self.session_id = str(ObjectId())
		self.embedding = [0.1, 0.2, 0.3]

	def test_init_functionality(self):
		"""Test that the init function correctly sets up the collection."""
		self.assertIn(self.test_collection, self.db.list_collection_names())

	def test_create_memory(self):
		"""Test successful creation of a medical memory with and without optional fields."""
		# Test full creation
		memory_id = medical_memory_repo.create_memory(
			self.patient_id, self.doctor_id, "Full summary", self.session_id, self.embedding,
			collection_name=self.test_collection
		)
		self.assertIsInstance(memory_id, str)
		doc = self.get_doc_by_id(Collections.MEDICAL_MEMORY, memory_id)
		self.assertIsNotNone(doc)
		self.assertEqual(doc["summary"], "Full summary") # type: ignore
		self.assertEqual(len(doc["embedding"]), 3) # type: ignore

		# Test minimal creation
		min_id = medical_memory_repo.create_memory(
			self.patient_id, self.doctor_id, "Minimal summary", collection_name=self.test_collection
		)
		self.assertIsInstance(min_id, str)

	def test_get_recent_memories(self):
		"""Test retrieving recent memories, verifying sorting, filtering, and limit."""
		medical_memory_repo.create_memory(self.patient_id, self.doctor_id, "Oldest", collection_name=self.test_collection)
		medical_memory_repo.create_memory(str(ObjectId()), self.doctor_id, "Other Patient", collection_name=self.test_collection)
		medical_memory_repo.create_memory(self.patient_id, self.doctor_id, "Newest", collection_name=self.test_collection)

		memories = medical_memory_repo.get_recent_memories(self.patient_id, collection_name=self.test_collection)
		self.assertEqual(len(memories), 2)
		self.assertIsInstance(memories[0], MedicalMemory)
		self.assertEqual(memories[0].summary, "Newest") # Descending sort order

		# Test limit
		limited = medical_memory_repo.get_recent_memories(self.patient_id, limit=1, collection_name=self.test_collection)
		self.assertEqual(len(limited), 1)

	def test_search_memories_semantic(self):
		"""Test semantic search functionality, verifying similarity logic and sorting."""
		# Create memories with known embeddings
		vec_a = [1.0, 0.0, 0.0] # Most similar
		vec_b = [0.7, 0.7, 0.0] # Less similar
		vec_c = [0.0, 0.0, 1.0] # Not similar
		medical_memory_repo.create_memory(self.patient_id, self.doctor_id, "Vec A", embedding=vec_a, collection_name=self.test_collection)
		medical_memory_repo.create_memory(self.patient_id, self.doctor_id, "Vec B", embedding=vec_b, collection_name=self.test_collection)
		medical_memory_repo.create_memory(self.patient_id, self.doctor_id, "Vec C", embedding=vec_c, collection_name=self.test_collection)
		medical_memory_repo.create_memory(self.patient_id, self.doctor_id, "No Embedding", collection_name=self.test_collection)

		query_embedding = [0.9, 0.1, 0.0]
		results = medical_memory_repo.search_memories_semantic(self.patient_id, query_embedding, collection_name=self.test_collection)

		self.assertEqual(len(results), 3) # Vec C should be filtered by default numpy math
		self.assertIsInstance(results[0], SemanticSearchResult)
		self.assertEqual(results[0].summary, "Vec A") # Most similar should be first
		self.assertGreater(results[0].similarity_score, results[1].similarity_score)


class TestMedicalMemoryRepositoryExceptions(BaseMongoTest):
	"""Test class for the exception handling of medical memory repository functions."""

	def setUp(self):
		"""Set up the test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.MEDICAL_MEMORY]
		medical_memory_repo.init(collection_name=self.test_collection, drop=True)
		self.patient_id = str(ObjectId())
		self.doctor_id = str(ObjectId())

	def test_invalid_id_raises_action_failed(self):
		"""Test that functions raise ActionFailed when given a malformed ObjectId string."""
		with self.assertRaises(ActionFailed):
			medical_memory_repo.create_memory("bad-id", self.doctor_id, "t", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			medical_memory_repo.get_recent_memories("bad-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			medical_memory_repo.search_memories_semantic("bad-id", [], collection_name=self.test_collection)

	@patch('src.data.repositories.medical_memory.get_collection')
	def test_all_functions_raise_on_connection_error(self, mock_get_collection):
		"""Test that all repo functions catch generic PyMongoErrors and raise ActionFailed."""
		mock_get_collection.side_effect = ConnectionFailure("Simulated connection error")

		with self.assertRaises(ActionFailed):
			medical_memory_repo.init(collection_name=self.test_collection, drop=True)
		with self.assertRaises(ActionFailed):
			medical_memory_repo.create_memory(self.patient_id, self.doctor_id, "t", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			medical_memory_repo.get_recent_memories(self.patient_id, collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			medical_memory_repo.search_memories_semantic(self.patient_id, [], collection_name=self.test_collection)

if __name__ == "__main__":
	logger().info("Starting MongoDB repository integration tests...")
	unittest.main(verbosity=2)
	logger().info("Tests completed and database connection closed.")
