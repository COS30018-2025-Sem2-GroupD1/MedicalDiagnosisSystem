"""MongoDB Integration Tests

To run this file, execute `python -m tests.mongo_test` from the project root directory.

@TODO This file is outdated and will need to be updated after the validators have been implemented.
"""

import unittest

from pymongo.errors import DuplicateKeyError

from src.data import connection as db_conn
from src.data import utils as db_utils
from src.data.repositories import account as account_repo
from src.data.repositories import medical as medical_repo
from src.data.repositories import session as chat_repo
from src.data.repositories.account import ACCOUNTS_COLLECTION
from src.data.repositories.medical import (MEDICAL_CONTEXT_COLLECTION,
                                           MEDICAL_RECORDS_COLLECTION)
from src.data.repositories.session import CHAT_SESSIONS_COLLECTION
from src.utils.logger import logger


class TestMongoDBRepositories(unittest.TestCase):
	"""Integration tests for the MongoDB repository modules."""

	@classmethod
	def setUpClass(cls):
		"""Initializes a test database and collection mappings."""
		cls.db = db_conn.get_database()
		cls.test_collections = {
			ACCOUNTS_COLLECTION: "test_accounts",
			CHAT_SESSIONS_COLLECTION: "test_chat_sessions",
			MEDICAL_RECORDS_COLLECTION: "test_medical_records",
			MEDICAL_CONTEXT_COLLECTION: "test_medical_context"
		}
		logger().info("Test database initialized.")

	def setUp(self):
		"""Clears all test collections before each test."""
		for test_name in self.test_collections.values():
			self.db.drop_collection(test_name)

	def test_account_operations(self):
		"""Tests account creation, updates, and retrieval."""
		test_coll = self.test_collections[ACCOUNTS_COLLECTION]

		user_id = account_repo.create_account(user_id="test_user_1", name="Test User", collection_name=test_coll)
		self.assertEqual(user_id, "test_user_1")

		success = account_repo.update_account(user_id, {"name": "Updated Name"}, collection_name=test_coll)
		self.assertTrue(success)

		profile = account_repo.get_user_profile(user_id, collection_name=test_coll)
		self.assertIsNotNone(profile)
		self.assertEqual(profile["name"], "Updated Name") # type: ignore

	def test_chat_session_operations(self):
		"""Tests chat session creation, message handling, and retrieval."""
		test_coll = self.test_collections[CHAT_SESSIONS_COLLECTION]

		session_id = chat_repo.create_session("test_user_1", "Test Chat", collection_name=test_coll)
		self.assertIsNotNone(session_id)

		messages = [
			{"role": "user", "content": "Message 1"},
			{"role": "assistant", "content": "Response 1"},
		]
		for msg in messages:
			result_id = chat_repo.add_message(session_id, msg, collection_name=test_coll)
			self.assertEqual(result_id, session_id)

		session = chat_repo.get_session(session_id, collection_name=test_coll)
		self.assertIsNotNone(session)
		self.assertEqual(len(session["messages"]), 2) # type: ignore

		user_sessions = chat_repo.get_user_sessions("test_user_1", collection_name=test_coll)
		self.assertEqual(len(user_sessions), 1)
		self.assertEqual(user_sessions[0]["title"], "Test Chat")

	def test_medical_records(self):
		"""Tests medical record creation and retrieval."""
		test_coll = self.test_collections[MEDICAL_RECORDS_COLLECTION]
		record_data = {"user_id": "test_user_1", "type": "lab_result", "notes": "Normal"}

		record_id = medical_repo.create_medical_record(record_data, collection_name=test_coll)
		self.assertIsNotNone(record_id)

		records = medical_repo.get_user_medical_records("test_user_1", collection_name=test_coll)
		self.assertEqual(len(records), 1)
		self.assertEqual(records[0]["type"], "lab_result")

	def test_utility_functions(self):
		"""Tests database utility functions like indexing and backups."""
		test_accounts = self.test_collections[ACCOUNTS_COLLECTION]
		test_sessions = self.test_collections[CHAT_SESSIONS_COLLECTION]

		db_utils.create_index(test_accounts, "email", unique=True)
		chat_repo.create_session("test_user_1", "Old Chat", collection_name=test_sessions)

		deleted_count = db_utils.delete_old_data(test_sessions, days=0)
		self.assertEqual(deleted_count, 1)

		backup_name = db_utils.backup_collection(test_accounts)
		self.assertTrue(backup_name.startswith(f"{test_accounts}_backup_"))
		self.assertIn(backup_name, self.db.list_collection_names())

	def test_error_handling(self):
		"""Tests expected error cases, such as duplicate keys and invalid IDs."""
		test_accounts = self.test_collections[ACCOUNTS_COLLECTION]
		test_sessions = self.test_collections[CHAT_SESSIONS_COLLECTION]

		db_utils.create_index(test_accounts, "name", unique=True)
		account_repo.create_account(name="User", user_id="user1", collection_name=test_accounts)

		with self.assertRaises(DuplicateKeyError):
			account_repo.create_account(name="User", user_id="user2", collection_name=test_accounts)

		with self.assertRaises(ValueError):
			chat_repo.add_message("invalid_session_id", {"role": "user", "content": "test"}, collection_name=test_sessions)

if __name__ == "__main__":
	try:
		logger().info("Starting MongoDB repository integration tests...")
		unittest.main(verbosity=2)
	finally:
		db_conn.close_connection()
		logger().info("Tests completed and database connection closed.")
