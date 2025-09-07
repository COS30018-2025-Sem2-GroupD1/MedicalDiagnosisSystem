"""MongoDB Integration Tests

To run this file, execute `python -m tests.mongo_test` from the project root directory.
"""

import unittest
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from src.data.mongodb import (ACCOUNTS_COLLECTION, CHAT_SESSIONS_COLLECTION,
                              MEDICAL_RECORDS_COLLECTION, add_message,
                              backup_collection, close_connection,
                              create_account, create_chat_session,
                              create_index, create_medical_record,
                              delete_old_sessions, get_account_frame,
                              get_database, get_session_messages,
                              get_user_medical_records, get_user_sessions,
                              update_account)
from src.utils.logger import get_logger

logger = get_logger("MONGO_TESTS", __name__)

class TestMongoDB(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		"""Initialize test database"""
		cls.db = get_database()
		# Map production collections to test collections
		# Doing it this make makes sure that if any collection is ever removed, the tests cannot be run
		cls.test_collections = {
			ACCOUNTS_COLLECTION: "test_accounts",
			CHAT_SESSIONS_COLLECTION: "test_chat_sessions",
			MEDICAL_RECORDS_COLLECTION: "test_medical_records"
		}
		logger.info("Test database initialized")

	def setUp(self):
		"""Reset collections before each test"""
		for prod_name, test_name in self.test_collections.items():
			if test_name in self.db.list_collection_names():
				self.db.drop_collection(test_name)

	def test_account_operations(self):
		"""Test account creation and updates"""
		test_coll = self.test_collections[ACCOUNTS_COLLECTION]

		# Create test account
		user_data = {
			"_id": "test_user_1",
			"name": "Test User",
			"email": "test@example.com"
		}
		user_id = create_account(user_data, collection_name=test_coll)
		self.assertIsNotNone(user_id)

		# Test updating account
		updates = {"name": "Updated Name"}
		success = update_account(user_id, updates, collection_name=test_coll)
		self.assertTrue(success)

		# Test DataFrame conversion
		df = get_account_frame(collection_name=test_coll)
		self.assertFalse(df.empty)
		self.assertEqual(df.iloc[0]["name"], "Updated Name")

	def test_chat_session_operations(self):
		"""Test chat session management"""
		test_coll = self.test_collections[CHAT_SESSIONS_COLLECTION]

		# Create session
		session_data = {
			"user_id": "test_user_1",
			"title": "Test Chat"
		}
		session_id = create_chat_session(session_data, collection_name=test_coll)
		self.assertIsNotNone(session_id)

		# Add messages
		messages = [
			{"role": "user", "content": "Test message 1"},
			{"role": "assistant", "content": "Test response 1"},
			{"role": "user", "content": "Test message 2"}
		]
		for msg in messages:
			result = add_message(session_id, msg, collection_name=test_coll)
			self.assertIsNotNone(result)

		# Get session messages
		retrieved_msgs = get_session_messages(session_id, collection_name=test_coll)
		self.assertEqual(len(retrieved_msgs), 3)

		# Test user sessions
		sessions = get_user_sessions("test_user_1", collection_name=test_coll)
		self.assertEqual(len(sessions), 1)
		self.assertEqual(sessions[0]["title"], "Test Chat")

	def test_medical_records(self):
		"""Test medical record operations"""
		test_coll = self.test_collections[MEDICAL_RECORDS_COLLECTION]

		# Create record
		record_data = {
			"user_id": "test_user_1",
			"type": "examination",
			"notes": "Test medical record"
		}
		record_id = create_medical_record(record_data, collection_name=test_coll)
		self.assertIsNotNone(record_id)

		# Get user records
		records = get_user_medical_records("test_user_1", collection_name=test_coll)
		self.assertEqual(len(records), 1)
		self.assertEqual(records[0]["type"], "examination")

	def test_utility_functions(self):
		"""Test utility functions"""
		test_accounts = self.test_collections[ACCOUNTS_COLLECTION]
		test_sessions = self.test_collections[CHAT_SESSIONS_COLLECTION]

		# Test index creation
		create_index(test_accounts, "email", unique=True)

		# Create test session
		session_data = {
			"user_id": "test_user_1",
			"title": "Old Chat",
			"updated_at": datetime.now(timezone.utc)
		}
		create_chat_session(session_data, collection_name=test_sessions)

		# Test session deletion
		deleted = delete_old_sessions(days=0, collection_name=test_sessions)
		self.assertEqual(deleted, 1)

		# Test backup
		backup_name = backup_collection(test_accounts)
		self.assertTrue(backup_name.startswith(f"{test_accounts}_backup_"))

	def test_error_handling(self):
		"""Test error cases"""
		test_accounts = self.test_collections[ACCOUNTS_COLLECTION]
		test_sessions = self.test_collections[CHAT_SESSIONS_COLLECTION]

		# Test duplicate email handling
		create_index(test_accounts, "email", unique=True)

		user1 = {
			"_id": "user1",
			"email": "same@email.com",
			"name": "User 1"
		}
		create_account(user1, collection_name=test_accounts)

		# Has the same email
		user2 = {
			"_id": "user2",
			"email": "same@email.com",
			"name": "User 2"
		}
		with self.assertRaises(DuplicateKeyError):
			create_account(user2, collection_name=test_accounts)

		# Test invalid session ID
		with self.assertRaises(ValueError):
			add_message(
				"invalid_id",
				{"content": "test"},
				collection_name=test_sessions
			)

if __name__ == "__main__":
	try:
		logger.info("Starting MongoDB integration tests...")
		unittest.main(verbosity=2)
	finally:
		close_connection()
		logger.info("Tests completed, connection closed")
