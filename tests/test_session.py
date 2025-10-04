import time
import unittest
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from src.data.connection import ActionFailed, Collections, get_collection
from src.data.repositories import session as session_repo
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestSessionRepository(BaseMongoTest):

	def setUp(self):
		"""Set up a clean test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.SESSION]
		session_repo.init(collection_name=self.test_collection, drop=True)

		self.account_id = str(ObjectId())
		self.patient_id = str(ObjectId())

	def test_init_functionality(self):
		"""Test that init sets up the collection and indexes correctly."""
		self.assertIn(self.test_collection, self.db.list_collection_names())
		index_info = get_collection(self.test_collection).index_information()
		self.assertIn("messages._id_1", index_info)

	def test_create_and_get_session(self):
		"""Test chat session creation and retrieval by ID."""
		# Test creation
		session = session_repo.create_session(
			self.account_id,
			self.patient_id,
			"Test Chat",
			collection_name=self.test_collection
		)
		self.assertIn("_id", session)
		self.assertIsInstance(session["_id"], str)
		self.assertEqual(session["title"], "Test Chat")
		self.assertEqual(len(session["messages"]), 0)

		# Test retrieval
		retrieved = session_repo.get_session(session["_id"], collection_name=self.test_collection)
		self.assertIsNotNone(retrieved)
		self.assertEqual(retrieved["_id"], session["_id"]) # type: ignore
		self.assertEqual(retrieved["account_id"], self.account_id) # type: ignore
		self.assertEqual(retrieved["patient_id"], self.patient_id) # type: ignore

		# Test getting a non-existent session
		non_existent = session_repo.get_session(str(ObjectId()), collection_name=self.test_collection)
		self.assertIsNone(non_existent)

	def test_add_and_get_messages(self):
		"""Test adding messages and retrieving them in the correct order."""
		session = session_repo.create_session(
			self.account_id, self.patient_id, "Message Test", collection_name=self.test_collection
		)
		session_id = session["_id"]

		# Add messages and verify session's updated_at timestamp changes
		original_doc = self.get_doc_by_id(Collections.SESSION, session_id)
		time.sleep(0.01) # Ensure timestamp will be different
		session_repo.add_message(session_id, "User message 1", True, collection_name=self.test_collection)
		updated_doc = self.get_doc_by_id(Collections.SESSION, session_id)
		self.assertLess(original_doc["updated_at"], updated_doc["updated_at"]) # type: ignore

		session_repo.add_message(session_id, "AI response 1", False, collection_name=self.test_collection)
		session_repo.add_message(session_id, "User message 2", True, collection_name=self.test_collection)

		# Test message retrieval (should be in descending order of creation)
		messages = session_repo.get_session_messages(session_id, collection_name=self.test_collection)
		self.assertEqual(len(messages), 3)
		self.assertEqual(messages[0]["_id"], 2)
		self.assertEqual(messages[0]["content"], "User message 2")
		self.assertEqual(messages[1]["_id"], 1)
		self.assertEqual(messages[2]["_id"], 0)

		# Test limit
		limited_messages = session_repo.get_session_messages(session_id, limit=2, collection_name=self.test_collection)
		self.assertEqual(len(limited_messages), 2)
		self.assertEqual(limited_messages[0]["_id"], 2)

		# Test adding message to non-existent session
		with self.assertRaises(ActionFailed):
			session_repo.add_message(str(ObjectId()), "ghost", True, collection_name=self.test_collection)

	def test_list_patient_sessions(self):
		"""Test listing sessions for a specific patient, sorted by update time."""
		p_id_1 = str(ObjectId())
		p_id_2 = str(ObjectId())

		# Create sessions, sleeping briefly to ensure distinct updated_at times
		session_repo.create_session(self.account_id, p_id_1, "P1 Chat 1", collection_name=self.test_collection)
		time.sleep(0.01)
		session_repo.create_session(self.account_id, p_id_2, "P2 Chat 1", collection_name=self.test_collection) # Belongs to other patient
		time.sleep(0.01)
		s2 = session_repo.create_session(self.account_id, p_id_1, "P1 Chat 2", collection_name=self.test_collection)

		# Test listing for patient 1
		sessions = session_repo.list_patient_sessions(p_id_1, collection_name=self.test_collection)
		self.assertEqual(len(sessions), 2)
		self.assertEqual(sessions[0]["_id"], s2["_id"]) # Most recently created should be first

	def test_get_user_sessions(self):
		"""Test listing sessions for a specific user, sorted by update time."""
		user1 = str(ObjectId())
		user2 = str(ObjectId())

		s1 = session_repo.create_session(user1, self.patient_id, "U1 Chat 1", collection_name=self.test_collection)
		time.sleep(0.01)
		session_repo.create_session(user2, self.patient_id, "U2 Chat 1", collection_name=self.test_collection)
		time.sleep(0.01)
		s3 = session_repo.create_session(user1, self.patient_id, "U1 Chat 2", collection_name=self.test_collection)

		sessions = session_repo.get_user_sessions(user1, collection_name=self.test_collection)
		self.assertEqual(len(sessions), 2)
		self.assertEqual(sessions[0]["_id"], s3["_id"]) # s3 was updated most recently
		self.assertEqual(sessions[1]["_id"], s1["_id"])

		# Test limit
		sessions_limited = session_repo.get_user_sessions(user1, limit=1, collection_name=self.test_collection)
		self.assertEqual(len(sessions_limited), 1)

	def test_update_session_title(self):
		"""Test updating a session's title."""
		session = session_repo.create_session(self.account_id, self.patient_id, "Old Title", collection_name=self.test_collection)
		session_id = session["_id"]

		success = session_repo.update_session_title(session_id, "New Title", collection_name=self.test_collection)
		self.assertTrue(success)

		updated_session = session_repo.get_session(session_id, collection_name=self.test_collection)
		self.assertEqual(updated_session["title"], "New Title") # type: ignore

		# Test updating non-existent session
		success_fail = session_repo.update_session_title(str(ObjectId()), "Ghost", collection_name=self.test_collection)
		self.assertFalse(success_fail)

	def test_delete_session(self):
		"""Test deleting a session."""
		session = session_repo.create_session(self.account_id, self.patient_id, "To Delete", collection_name=self.test_collection)
		session_id = session["_id"]

		success = session_repo.delete_session(session_id, collection_name=self.test_collection)
		self.assertTrue(success)

		deleted_session = session_repo.get_session(session_id, collection_name=self.test_collection)
		self.assertIsNone(deleted_session)

		# Test deleting non-existent session
		success_fail = session_repo.delete_session(str(ObjectId()), collection_name=self.test_collection)
		self.assertFalse(success_fail)

	def test_prune_old_sessions(self):
		"""Test deleting sessions older than a specified number of days."""
		coll = get_collection(self.test_collection)
		now = datetime.now(timezone.utc)
		old_date = now - timedelta(days=31)

		# Manually insert one old and one new session
		coll.insert_one({
			"account_id": ObjectId(self.account_id), "patient_id": ObjectId(self.patient_id),
			"title": "Old Session", "created_at": old_date, "updated_at": old_date, "messages": []
		})
		coll.insert_one({
			"account_id": ObjectId(self.account_id), "patient_id": ObjectId(self.patient_id),
			"title": "New Session", "created_at": now, "updated_at": now, "messages": []
		})

		self.assertEqual(coll.count_documents({}), 2)

		deleted_count = session_repo.prune_old_sessions(days=30, collection_name=self.test_collection)
		self.assertEqual(deleted_count, 1)
		self.assertEqual(coll.count_documents({}), 1)

		remaining = coll.find_one()
		self.assertEqual(remaining["title"], "New Session") # type: ignore


if __name__ == "__main__":
	try:
		logger().info("Starting MongoDB repository integration tests...")
		unittest.main(verbosity=2)
	finally:
		logger().info("Tests completed and database connection closed.")
