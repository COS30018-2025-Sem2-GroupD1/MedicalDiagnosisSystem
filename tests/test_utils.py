import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from pymongo.errors import ConnectionFailure

from src.data import utils as db_utils
from src.data.connection import ActionFailed, Collections, get_collection
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestDatabaseUtils(BaseMongoTest):
	"""Test class for the 'happy path' of all database utility functions."""

	def setUp(self):
		"""Set up a clean test environment before each test."""
		super().setUp()
		self.test_collection_name = self._collections[Collections.ACCOUNT]
		self.test_collection = get_collection(self.test_collection_name)

	def test_create_index(self):
		"""Test that an index is correctly created on a collection."""
		db_utils.create_index(self.test_collection_name, "test_field")
		index_info = self.test_collection.index_information()
		self.assertIn("test_field_1", index_info)

		# Test unique index creation
		db_utils.create_index(self.test_collection_name, "unique_field", unique=True)
		index_info_unique = self.test_collection.index_information()
		self.assertTrue(index_info_unique["unique_field_1"]["unique"])

	def test_delete_old_data(self):
		"""Test that only documents older than the cutoff are deleted."""
		now = datetime.now(timezone.utc)
		old_date = now - timedelta(days=31)

		# Insert one old and one new document
		self.test_collection.insert_one({"name": "old_doc", "updated_at": old_date})
		self.test_collection.insert_one({"name": "new_doc", "updated_at": now})
		self.assertEqual(self.test_collection.count_documents({}), 2)

		deleted_count = db_utils.delete_old_data(self.test_collection_name, days=30)
		self.assertEqual(deleted_count, 1)
		self.assertEqual(self.test_collection.count_documents({}), 1)

		remaining_doc = self.test_collection.find_one()
		self.assertEqual(remaining_doc["name"], "new_doc") # type: ignore

	def test_backup_collection(self):
		"""Test that a collection is successfully backed up."""
		self.test_collection.insert_one({"name": "doc1"})
		self.test_collection.insert_one({"name": "doc2"})

		backup_name = db_utils.backup_collection(self.test_collection_name)
		self.assertIn(backup_name, self.db.list_collection_names())

		backup_collection = self.db[backup_name]
		self.assertEqual(backup_collection.count_documents({}), 2)


class TestDatabaseUtilsExceptions(BaseMongoTest):
	"""Test class for the exception handling of all database utility functions."""

	@patch('src.data.utils.get_collection')
	@patch('src.data.utils.get_database')
	def test_all_functions_raise_on_connection_error(self, mock_get_database, mock_get_collection):
		"""Test that all utility functions catch PyMongoErrors and raise ActionFailed."""
		mock_get_collection.side_effect = ConnectionFailure("Simulated connection error")
		mock_get_database.side_effect = ConnectionFailure("Simulated connection error")

		with self.assertRaises(ActionFailed):
			db_utils.create_index("any_collection", "any_field")
		with self.assertRaises(ActionFailed):
			db_utils.delete_old_data("any_collection", days=30)
		with self.assertRaises(ActionFailed):
			db_utils.backup_collection("any_collection")

if __name__ == "__main__":
	logger().info("Starting MongoDB repository integration tests...")
	unittest.main(verbosity=2)
	logger().info("Tests completed.")
