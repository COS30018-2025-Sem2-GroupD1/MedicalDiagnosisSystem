"""
Run individual tests:
python -m tests.test_account
python -m tests.test_patient
python -m tests.test_session

Run collective tests:
python -m unittest discover tests "test_*.py"
"""

import unittest
from typing import Any

from bson import ObjectId

from src.data.connection import Collections, get_collection, get_database


class BaseMongoTest(unittest.TestCase):
	"""Base class for MongoDB tests that handles test collection management."""

	@classmethod
	def setUpClass(cls):
		"""Initialize test database connection"""
		cls.db = get_database()
		# Map production collections to test collections
		# The key is the collection's actual name (the attribute's value)
		cls._collections = {
			value: f"test_{value.lower()}" for name, value in vars(Collections).items()
			if not name.startswith('_') and isinstance(value, str)
		}

	def setUp(self):
		"""Create clean test collections before each test"""
		for test_name in self._collections.values():
			self.db.drop_collection(test_name)

	def tearDown(self):
		"""Clean up test collections after each test"""
		for test_name in self._collections.values():
			self.db.drop_collection(test_name)

	def get_doc_by_id(self, collection: str, doc_id: str) -> dict[str, Any] | None:
		"""
		Helper to get a document by ID.
		`collection` should be the production collection name from `Collections`.
		"""
		# Look up the test collection name using the production name as the key
		test_coll_name = self._collections.get(collection)
		if not test_coll_name:
			raise KeyError(f"No test collection mapping found for '{collection}'")
		return get_collection(test_coll_name).find_one({"_id": ObjectId(doc_id)})
