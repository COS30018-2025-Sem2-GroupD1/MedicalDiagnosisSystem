import time
import unittest
from datetime import datetime
from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import ConnectionFailure

from src.data.connection import ActionFailed, Collections, get_collection
from src.data.repositories import account as account_repo
from src.models.account import Account
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
		account_repo.create_account("Persist Test", "Doctor", collection_name=self.test_collection)
		account_repo.init(collection_name=self.test_collection, drop=False)
		self.assertEqual(get_collection(self.test_collection).count_documents({}), 1)
		account_repo.init(collection_name=self.test_collection, drop=True)
		self.assertEqual(get_collection(self.test_collection).count_documents({}), 0)

	def test_create_account(self):
		"""Test successful account creation, including optional fields."""
		name, role = "Test Doctor", "Doctor"
		account_id = account_repo.create_account(name=name, role=role, collection_name=self.test_collection)
		self.assertIsInstance(account_id, str)
		doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(doc)
		self.assertEqual(doc["name"], name) # type: ignore
		spec_id = account_repo.create_account("Spec", "Nurse", specialty="Cardiology", collection_name=self.test_collection)
		spec_doc = self.get_doc_by_id(Collections.ACCOUNT, spec_id)
		self.assertEqual(spec_doc["specialty"], "Cardiology") # type: ignore

	def test_update_account_logic(self):
		"""Test the specific business logic of the update_account function."""
		account_id = account_repo.create_account("Update Logic", "Doctor", collection_name=self.test_collection)
		original_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(original_doc)
		updates = {"name": "Updated Name", "created_at": datetime(2000, 1, 1)}
		success = account_repo.update_account(account_id, updates, collection_name=self.test_collection)
		self.assertTrue(success)
		updated_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(updated_doc)
		self.assertEqual(updated_doc["created_at"], original_doc["created_at"]) # type: ignore
		self.assertLess(original_doc["updated_at"], updated_doc["updated_at"]) # type: ignore
		self.assertFalse(account_repo.update_account(str(ObjectId()), {"name": "No One"}, collection_name=self.test_collection))

	def test_get_account_logic(self):
		"""Test that get_account updates 'last_seen' and returns a valid Account model."""
		account_id = account_repo.create_account("GetMe", "Doctor", collection_name=self.test_collection)
		original_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(original_doc)
		time.sleep(0.01) # Ensure timestamp will be different

		account = account_repo.get_account(account_id, collection_name=self.test_collection)
		self.assertIsNotNone(account)
		self.assertIsInstance(account, Account)
		self.assertLess(original_doc["last_seen"], account.last_seen) # type: ignore
		self.assertEqual(original_doc["updated_at"], account.updated_at) # type: ignore
		self.assertIsNone(account_repo.get_account(str(ObjectId()), collection_name=self.test_collection))

	def test_get_account_by_name(self):
		"""Test retrieving an account by name and check for deprecation warning."""
		name = "FindByName"
		account_repo.create_account(name, "Nurse", collection_name=self.test_collection)
		account = account_repo.get_account_by_name(name, collection_name=self.test_collection)
		self.assertIsNotNone(account)
		self.assertIsInstance(account, Account)
		self.assertEqual(account.name, name) # type: ignore
		self.assertIsNone(account_repo.get_account_by_name("NonExistent", collection_name=self.test_collection))

	def test_search_accounts(self):
		"""Test search functionality returns a list of Account models."""
		account_repo.create_account("Alpha Doctor", "Doctor", collection_name=self.test_collection)
		account_repo.create_account("Beta Nurse", "Nurse", collection_name=self.test_collection)
		results = account_repo.search_accounts("alpha", collection_name=self.test_collection)
		self.assertEqual(len(results), 1)
		self.assertIsInstance(results[0], Account)
		self.assertEqual(results[0].name, "Alpha Doctor")
		self.assertEqual(len(account_repo.search_accounts("NonExistent", collection_name=self.test_collection)), 0)

	def test_get_all_accounts(self):
		"""Test retrieving all accounts, verifying sorting and model type."""
		account_repo.create_account("Charlie", "Doctor", collection_name=self.test_collection)
		account_repo.create_account("Alpha", "Nurse", collection_name=self.test_collection)
		all_accounts = account_repo.get_all_accounts(collection_name=self.test_collection)
		self.assertEqual(len(all_accounts), 2)
		self.assertIsInstance(all_accounts[0], Account)
		self.assertEqual(all_accounts[0].name, "Alpha")
		self.assertEqual(all_accounts[1].name, "Charlie")

	def test_get_account_frame(self):
		"""Test retrieving accounts as a pandas DataFrame."""
		df_empty = account_repo.get_account_frame(collection_name=self.test_collection)
		self.assertTrue(df_empty.empty)
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
	logger().info("Tests completed.")
