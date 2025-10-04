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
		cls._collections = {
			name: f"test_{name.lower()}" for name, _ in vars(Collections).items()
			if not name.startswith('_')
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
		"""Helper to get a document by ID"""
		test_coll = self._collections[collection]
		return get_collection(test_coll).find_one({"_id": ObjectId(doc_id)})
