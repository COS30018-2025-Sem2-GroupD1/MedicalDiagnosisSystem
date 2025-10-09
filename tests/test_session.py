import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import ConnectionFailure, WriteError

from src.data.connection import ActionFailed, Collections, get_collection
from src.data.repositories import session as session_repo
from src.models.session import Message, Session
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestSessionRepository(BaseMongoTest):
	"""Test class for the 'happy path' and edge cases of session repository functions."""

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
		session = session_repo.create_session(
			self.account_id, self.patient_id, "Test Chat", collection_name=self.test_collection
		)
		self.assertIsInstance(session, Session)
		self.assertEqual(session.title, "Test Chat")

		retrieved = session_repo.get_session(session.id, collection_name=self.test_collection)
		self.assertIsNotNone(retrieved)
		self.assertIsInstance(retrieved, Session)
		self.assertEqual(retrieved.id, session.id) # type: ignore
		self.assertEqual(retrieved.account_id, self.account_id) # type: ignore
		self.assertIsNone(session_repo.get_session(str(ObjectId()), collection_name=self.test_collection))

	def test_add_and_get_messages(self):
		"""Test adding messages and retrieving them as Message models."""
		session = session_repo.create_session(self.account_id, self.patient_id, "Msg Test", collection_name=self.test_collection)

		session_repo.add_message(session.id, "User message 1", True, collection_name=self.test_collection)
		# Add a small delay to ensure a distinct timestamp for the next message
		time.sleep(0.01)
		session_repo.add_message(session.id, "AI response 1", False, collection_name=self.test_collection)

		messages = session_repo.get_session_messages(session.id, collection_name=self.test_collection)
		self.assertEqual(len(messages), 2)
		self.assertIsInstance(messages[0], Message)
		self.assertEqual(messages[0].content, "AI response 1") # Descending order is now guaranteed
		self.assertEqual(messages[1].id, 0)
		self.assertEqual(len(session_repo.get_session_messages(session.id, limit=1, collection_name=self.test_collection)), 1)

	def test_list_sessions(self):
		"""Test listing sessions for a patient and user returns lists of Session models."""
		session_repo.create_session(self.account_id, self.patient_id, "First", collection_name=self.test_collection)
		time.sleep(0.01)
		s2 = session_repo.create_session(self.account_id, self.patient_id, "Second", collection_name=self.test_collection)

		patient_sessions = session_repo.list_patient_sessions(self.patient_id, collection_name=self.test_collection)
		self.assertEqual(len(patient_sessions), 2)
		self.assertIsInstance(patient_sessions[0], Session)
		self.assertEqual(patient_sessions[0].id, s2.id)

		user_sessions = session_repo.get_user_sessions(self.account_id, collection_name=self.test_collection)
		self.assertEqual(len(user_sessions), 2)
		self.assertEqual(user_sessions[0].id, s2.id)

	def test_update_session_title(self):
		"""Test updating a session's title and its timestamp."""
		session = session_repo.create_session(self.account_id, self.patient_id, "Old", collection_name=self.test_collection)
		original_doc = self.get_doc_by_id(Collections.SESSION, session.id)
		self.assertIsNotNone(original_doc)

		success = session_repo.update_session_title(session.id, "New", collection_name=self.test_collection)
		self.assertTrue(success)

		updated_doc = self.get_doc_by_id(Collections.SESSION, session.id)
		self.assertIsNotNone(updated_doc)
		self.assertEqual(updated_doc["title"], "New") # type: ignore
		self.assertLess(original_doc["updated_at"], updated_doc["updated_at"]) # type: ignore
		self.assertFalse(session_repo.update_session_title(str(ObjectId()), "Ghost", collection_name=self.test_collection))

	def test_delete_session(self):
		"""Test deleting a session."""
		session = session_repo.create_session(self.account_id, self.patient_id, "To Delete", collection_name=self.test_collection)
		self.assertTrue(session_repo.delete_session(session.id, collection_name=self.test_collection))
		self.assertIsNone(session_repo.get_session(session.id, collection_name=self.test_collection))
		self.assertFalse(session_repo.delete_session(str(ObjectId()), collection_name=self.test_collection))

	def test_prune_old_sessions(self):
		"""Test deleting sessions older than a specified number of days."""
		old_session = session_repo.create_session(self.account_id, self.patient_id, "Old", collection_name=self.test_collection)
		session_repo.create_session(self.account_id, self.patient_id, "New", collection_name=self.test_collection)
		old_date = datetime.now(timezone.utc) - timedelta(days=31)
		get_collection(self.test_collection).update_one(
			{"_id": ObjectId(old_session.id)}, {"$set": {"updated_at": old_date}}
		)
		self.assertEqual(get_collection(self.test_collection).count_documents({}), 2)
		deleted_count = session_repo.prune_old_sessions(days=30, collection_name=self.test_collection)
		self.assertEqual(deleted_count, 1)


class TestSessionRepositoryExceptions(BaseMongoTest):
	"""Test class for the exception handling of all session repository functions."""

	def setUp(self):
		"""Set up a clean test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.SESSION]
		session_repo.init(collection_name=self.test_collection, drop=True)
		self.account_id = str(ObjectId())
		self.patient_id = str(ObjectId())

	@patch('src.data.repositories.session.get_collection')
	def test_write_error_raises_action_failed(self, mock_get_collection):
		"""Test that a WriteError during an operation is raised as ActionFailed."""
		mock_collection = mock_get_collection.return_value
		mock_collection.update_one.side_effect = WriteError("Simulated schema validation error")
		mock_collection.find_one.return_value = {"messages": []}
		with self.assertRaises(ActionFailed):
			session_repo.add_message(str(ObjectId()), "content", True, collection_name=self.test_collection)

	def test_invalid_id_raises_action_failed(self):
		"""Test that functions raise ActionFailed when given a malformed ObjectId string."""
		with self.assertRaises(ActionFailed):
			session_repo.create_session("bad-id", self.patient_id, "t", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.get_user_sessions("bad-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.list_patient_sessions("bad-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.get_session("bad-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.get_session_messages("bad-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.update_session_title("bad-id", "t", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.delete_session("bad-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.add_message("bad-id", "t", True, collection_name=self.test_collection)

	@patch('src.data.repositories.session.get_collection')
	def test_all_functions_raise_on_connection_error(self, mock_get_collection):
		"""Test that all repo functions catch generic PyMongoErrors and raise ActionFailed."""
		mock_get_collection.side_effect = ConnectionFailure("Simulated connection error")
		with self.assertRaises(ActionFailed):
			session_repo.init(collection_name=self.test_collection, drop=True)
		with self.assertRaises(ActionFailed):
			session_repo.create_session(self.account_id, self.patient_id, "t", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.get_user_sessions(self.account_id, collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.list_patient_sessions(self.patient_id, collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.get_session(str(ObjectId()), collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.get_session_messages(str(ObjectId()), collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.update_session_title(str(ObjectId()), "t", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.delete_session(str(ObjectId()), collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.prune_old_sessions(collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			session_repo.add_message(str(ObjectId()), "t", True, collection_name=self.test_collection)

if __name__ == "__main__":
	logger().info("Starting MongoDB repository integration tests...")
	unittest.main(verbosity=2)
	logger().info("Tests completed.")
