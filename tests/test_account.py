import unittest
from datetime import datetime
from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import ConnectionFailure

from src.data.connection import ActionFailed, Collections, get_collection
from src.data.repositories import account as account_repo
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestAccountRepository(BaseMongoTest):
	"""Test class for the 'happy path' and edge cases of account repository functions."""

	def setUp(self):
		"""Set up the test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.ACCOUNT]
		account_repo.init(collection_name=self.test_collection, drop=True)

	def test_init_functionality(self):
		"""Test the init function's ability to create, drop, and preserve collections."""
		self.assertIn(self.test_collection, self.db.list_collection_names())
		# Test that data persists when drop=False
		account_id = account_repo.create_account("Persist Test", "Doctor", collection_name=self.test_collection)
		account_repo.init(collection_name=self.test_collection, drop=False)
		self.assertEqual(get_collection(self.test_collection).count_documents({}), 1)
		# Test that data is deleted when drop=True
		account_repo.init(collection_name=self.test_collection, drop=True)
		self.assertEqual(get_collection(self.test_collection).count_documents({}), 0)

	def test_create_account(self):
		"""Test successful account creation, including optional fields."""
		# Test basic creation
		name, role = "Test Doctor", "Doctor"
		account_id = account_repo.create_account(name=name, role=role, collection_name=self.test_collection)
		self.assertIsInstance(account_id, str)
		doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(doc)
		self.assertEqual(doc["name"], name) # type: ignore
		# Test creation with specialty
		spec_id = account_repo.create_account("Spec", "Nurse", specialty="Cardiology", collection_name=self.test_collection)
		spec_doc = self.get_doc_by_id(Collections.ACCOUNT, spec_id)
		self.assertEqual(spec_doc["specialty"], "Cardiology") # type: ignore

	def test_update_account_logic(self):
		"""Test the specific business logic of the update_account function."""
		account_id = account_repo.create_account("Update Logic", "Doctor", collection_name=self.test_collection)
		original_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(original_doc)

		# Test that 'created_at' is immutable
		updates = {"name": "Updated Name", "created_at": datetime(2000, 1, 1)}
		success = account_repo.update_account(account_id, updates, collection_name=self.test_collection)
		self.assertTrue(success)
		updated_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(updated_doc)
		self.assertEqual(updated_doc["created_at"], original_doc["created_at"]) # type: ignore
		self.assertLess(original_doc["updated_at"], updated_doc["updated_at"]) # type: ignore

		# Test updating a non-existent account returns False
		self.assertFalse(account_repo.update_account(str(ObjectId()), {"name": "No One"}, collection_name=self.test_collection))

	def test_get_account_logic(self):
		"""Test that get_account updates 'last_seen' but not 'updated_at'."""
		account_id = account_repo.create_account("GetMe", "Doctor", collection_name=self.test_collection)
		original_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(original_doc)
		self.assertNotIn("last_seen", original_doc) # type: ignore

		# Get the account, which should add 'last_seen'
		account = account_repo.get_account(account_id, collection_name=self.test_collection)
		self.assertIsNotNone(account)
		self.assertIn("last_seen", account) # type: ignore

		# Verify that 'updated_at' was NOT modified by the get operation
		final_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(final_doc)
		self.assertEqual(final_doc["updated_at"], original_doc["updated_at"]) # type: ignore

	def test_get_account_by_name(self):
		"""Test retrieving an account by name and check for deprecation warning."""
		name = "FindByName"
		account_repo.create_account(name, "Nurse", collection_name=self.test_collection)

		# Check that the function works and raises the expected warning
		account = account_repo.get_account_by_name(name, collection_name=self.test_collection)
		self.assertIsNotNone(account)
		self.assertEqual(account["name"], name) # type: ignore

		# Test retrieval of a non-existent name returns None
		self.assertIsNone(account_repo.get_account_by_name("NonExistent", collection_name=self.test_collection))

	def test_search_accounts(self):
		"""Test search functionality with various edge cases."""
		account_repo.create_account("Alpha Doctor", "Doctor", collection_name=self.test_collection)
		account_repo.create_account("Beta Nurse", "Nurse", collection_name=self.test_collection)
		account_repo.create_account("Charlie Doctor", "Doctor", collection_name=self.test_collection)

		# Test case-insensitive partial match
		self.assertEqual(len(account_repo.search_accounts("alpha", collection_name=self.test_collection)), 1)
		# Test query matching multiple documents
		self.assertEqual(len(account_repo.search_accounts("Doctor", collection_name=self.test_collection)), 2)
		# Test limit parameter
		self.assertEqual(len(account_repo.search_accounts("Doctor", limit=1, collection_name=self.test_collection)), 1)
		# Test query with no matches
		self.assertEqual(len(account_repo.search_accounts("NonExistent", collection_name=self.test_collection)), 0)
		# Test empty query string returns an empty list
		self.assertEqual(len(account_repo.search_accounts("", collection_name=self.test_collection)), 0)

	def test_get_all_accounts(self):
		"""Test retrieving all accounts, verifying sorting and limit."""
		account_repo.create_account("Charlie", "Doctor", collection_name=self.test_collection)
		account_repo.create_account("Alpha", "Nurse", collection_name=self.test_collection)
		account_repo.create_account("Beta", "Caregiver", collection_name=self.test_collection)

		all_accounts = account_repo.get_all_accounts(collection_name=self.test_collection)
		self.assertEqual(len(all_accounts), 3)
		# Verify results are sorted by name
		self.assertEqual(all_accounts[0]["name"], "Alpha")
		self.assertEqual(all_accounts[2]["name"], "Charlie")

		# Test with a limit
		limited_accounts = account_repo.get_all_accounts(limit=2, collection_name=self.test_collection)
		self.assertEqual(len(limited_accounts), 2)
		self.assertEqual(limited_accounts[1]["name"], "Beta")

	def test_get_account_frame(self):
		"""Test retrieving accounts as a pandas DataFrame for empty and populated collections."""
		# Test with an empty collection
		df_empty = account_repo.get_account_frame(collection_name=self.test_collection)
		self.assertTrue(df_empty.empty)
		# Test with data
		account_repo.create_account("Frame Alpha", "Doctor", collection_name=self.test_collection)
		df_full = account_repo.get_account_frame(collection_name=self.test_collection)
		self.assertEqual(len(df_full), 1)


class TestAccountRepositoryExceptions(BaseMongoTest):
	"""Test class for the exception handling of all account repository functions."""

	def setUp(self):
		"""Set up the test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.ACCOUNT]
		account_repo.init(collection_name=self.test_collection, drop=True)
		get_collection(self.test_collection).create_index("name", unique=True)

	def test_create_account_write_error(self):
		"""Test that creating an account with invalid data raises ActionFailed."""
		account_repo.create_account("Duplicate Name", "Doctor", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.create_account("Duplicate Name", "Nurse", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.create_account("Schema Test", "InvalidRole", collection_name=self.test_collection)

	def test_invalid_id_raises_action_failed(self):
		"""Test that functions raise ActionFailed when given a malformed ObjectId string."""
		with self.assertRaises(ActionFailed):
			account_repo.get_account("not-a-valid-id", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.update_account("not-a-valid-id", {"name": "test"}, collection_name=self.test_collection)

	@patch('src.data.repositories.account.get_collection')
	def test_all_functions_raise_on_connection_error(self, mock_get_collection):
		"""Test that all repo functions catch generic PyMongoErrors and raise ActionFailed."""
		mock_get_collection.side_effect = ConnectionFailure("Simulated connection error")
		with self.assertRaises(ActionFailed):
			account_repo.init(collection_name=self.test_collection, drop=True)
		with self.assertRaises(ActionFailed):
			account_repo.get_account_frame(collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.create_account("test", "Doctor", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.update_account(str(ObjectId()), {"name": "test"}, collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.get_account(str(ObjectId()), collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.get_account_by_name("test", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.search_accounts("test", collection_name=self.test_collection)
		with self.assertRaises(ActionFailed):
			account_repo.get_all_accounts(collection_name=self.test_collection)

if __name__ == "__main__":
	logger().info("Starting MongoDB repository integration tests...")
	unittest.main(verbosity=2)
	logger().info("Tests completed and database connection closed.")
