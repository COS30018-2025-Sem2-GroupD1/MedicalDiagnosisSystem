import unittest
from datetime import datetime

from bson import ObjectId
from pandas import DataFrame
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from src.data.connection import Collections, get_collection
from src.data.repositories import account as Repo
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestAccountRepository(BaseMongoTest):

	def setUp(self):
		"""Set up the test environment before each test."""
		super().setUp()
		self.test_collection = self._collections[Collections.ACCOUNT]

		# Call the updated init function directly to set up the test collection
		Repo.init(collection_name=self.test_collection, drop=True)

		# Add a unique index on 'name' to test for duplicate key errors
		get_collection(self.test_collection).create_index(
			[("name", ASCENDING)], unique=True
		)

	def test_init_functionality(self):
		"""Test the init function's ability to create and drop collections."""
		# 1. Verify the collection exists after setUp
		self.assertIn(self.test_collection, self.db.list_collection_names())

		# 2. Test the drop functionality
		Repo.create_account("ToDelete", "Doctor", collection_name=self.test_collection)
		self.assertEqual(get_collection(self.test_collection).count_documents({}), 1)

		# Re-initialize with drop=True
		Repo.init(collection_name=self.test_collection, drop=True)

		# Assert the collection is now empty but still exists
		self.assertEqual(get_collection(self.test_collection).count_documents({}), 0)
		self.assertIn(self.test_collection, self.db.list_collection_names())

	def test_create_account(self):
		"""Test account creation with various parameters and constraints."""
		# Test basic creation
		name = "Test Doctor"
		role = "Doctor"
		account_id = Repo.create_account(
			name=name,
			role=role,
			collection_name=self.test_collection
		)
		self.assertIsInstance(account_id, str)
		doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(doc)
		self.assertEqual(doc["name"], name) # type: ignore
		self.assertEqual(doc["role"], role) # type: ignore
		self.assertIn("created_at", doc) # type: ignore
		self.assertIn("updated_at", doc) # type: ignore
		self.assertEqual(doc["created_at"], doc["updated_at"]) # type: ignore

		# Test creation with specialty
		account_id_spec = Repo.create_account(
			name="Specialist",
			role="Doctor",
			specialty="Cardiology",
			collection_name=self.test_collection
		)
		doc_spec = self.get_doc_by_id(Collections.ACCOUNT, account_id_spec)
		self.assertIsNotNone(doc_spec)
		self.assertEqual(doc_spec["specialty"], "Cardiology") # type: ignore

		# Test creating a user with a duplicate name raises an error
		with self.assertRaises(DuplicateKeyError):
			Repo.create_account(name=name, role="Nurse", collection_name=self.test_collection)

	def test_get_account(self):
		"""Test retrieving a single account by its ID."""
		account_id = Repo.create_account(
			"GetMe", "Doctor", collection_name=self.test_collection
		)
		original_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertNotIn("last_seen", original_doc) # type: ignore

		# Get the account and verify 'last_seen' is updated
		account = Repo.get_account(account_id, collection_name=self.test_collection)
		self.assertIsNotNone(account)
		self.assertEqual(account["_id"], account_id) # type: ignore
		self.assertEqual(account["name"], "GetMe") # type: ignore
		self.assertIn("last_seen", account) # type: ignore
		self.assertIsInstance(account["last_seen"], datetime) # type: ignore
		self.assertIsInstance(account["_id"], str) # type: ignore

		# Test retrieval of a non-existent account returns None
		non_existent_id = str(ObjectId())
		account = Repo.get_account(non_existent_id, collection_name=self.test_collection)
		self.assertIsNone(account)

	def test_get_account_by_name(self):
		"""Test retrieving an account by name."""
		name = "FindByName"
		Repo.create_account(name, "Nurse", collection_name=self.test_collection)

		account = Repo.get_account_by_name(name, collection_name=self.test_collection)
		self.assertIsNotNone(account)
		self.assertEqual(account["name"], name) # type: ignore
		self.assertIsInstance(account["_id"], str) # type: ignore

		# Test retrieval of a non-existent name returns None
		account = Repo.get_account_by_name("NonExistent", collection_name=self.test_collection)
		self.assertIsNone(account)

	def test_update_account(self):
		"""Test updating an existing account's data."""
		account_id = Repo.create_account(
			name="Update Test",
			role="Doctor",
			collection_name=self.test_collection
		)
		original_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(original_doc)

		updates = {"name": "Updated Name", "specialty": "Pediatrics"}
		success = Repo.update_account(account_id, updates, collection_name=self.test_collection)
		self.assertTrue(success)

		updated_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(updated_doc)
		self.assertEqual(updated_doc["name"], "Updated Name") # type: ignore
		self.assertEqual(updated_doc["specialty"], "Pediatrics") # type: ignore
		self.assertEqual(updated_doc["created_at"], original_doc["created_at"]) # type: ignore
		self.assertLess(original_doc["updated_at"], updated_doc["updated_at"]) # type: ignore

		# Test that updating a non-existent account returns False
		success = Repo.update_account(str(ObjectId()), {"name": "No One"}, collection_name=self.test_collection)
		self.assertFalse(success)

		# Test that 'created_at' is ignored in updates and does not change
		success = Repo.update_account(
			account_id,
			{"created_at": datetime(2000, 1, 1)},
			collection_name=self.test_collection
		)
		self.assertTrue(success)
		final_doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertEqual(final_doc["created_at"], original_doc["created_at"]) # type: ignore

	def test_search_accounts(self):
		"""Test account search functionality for various cases."""
		Repo.create_account("Alpha Doctor", "Doctor", collection_name=self.test_collection)
		Repo.create_account("Beta Doctor", "Doctor", collection_name=self.test_collection)
		Repo.create_account("Charlie Medical", "Medical Student", collection_name=self.test_collection)

		# Test case-insensitive partial match
		results = Repo.search_accounts("beta", collection_name=self.test_collection)
		self.assertEqual(len(results), 1)
		self.assertEqual(results[0]["name"], "Beta Doctor")

		# Test case-insensitive full match
		results = Repo.search_accounts("ALPHA DOCTOR", collection_name=self.test_collection)
		self.assertEqual(len(results), 1)

		# Test query that matches multiple entries with a limit
		results = Repo.search_accounts("Doctor", limit=2, collection_name=self.test_collection)
		self.assertEqual(len(results), 2)
		self.assertEqual(results[0]['name'], 'Alpha Doctor') # Assumes ascending sort by name
		self.assertEqual(results[1]['name'], 'Beta Doctor')

		# Test query with no matches
		results = Repo.search_accounts("NonExistent", collection_name=self.test_collection)
		self.assertEqual(len(results), 0)

		# Test empty query string returns an empty list
		results = Repo.search_accounts("", collection_name=self.test_collection)
		self.assertEqual(len(results), 0)

	def test_get_all_accounts(self):
		"""Test retrieving all accounts with limit and sorting."""
		Repo.create_account("Charlie", "Doctor", collection_name=self.test_collection)
		Repo.create_account("Alpha", "Nurse", collection_name=self.test_collection)
		Repo.create_account("Beta", "Caregiver", collection_name=self.test_collection)

		# Test getting all accounts, verifying ascending sort order by name
		all_accounts = Repo.get_all_accounts(collection_name=self.test_collection)
		self.assertEqual(len(all_accounts), 3)
		self.assertEqual(all_accounts[0]["name"], "Alpha")
		self.assertEqual(all_accounts[1]["name"], "Beta")
		self.assertEqual(all_accounts[2]["name"], "Charlie")

		# Test with a limit
		limited_accounts = Repo.get_all_accounts(limit=2, collection_name=self.test_collection)
		self.assertEqual(len(limited_accounts), 2)
		self.assertEqual(limited_accounts[0]["name"], "Alpha")
		self.assertEqual(limited_accounts[1]["name"], "Beta")

	def test_get_account_frame(self):
		"""Test retrieving accounts as a pandas DataFrame."""
		# Test with an empty collection
		df_empty = Repo.get_account_frame(collection_name=self.test_collection)
		self.assertIsInstance(df_empty, DataFrame)
		self.assertTrue(df_empty.empty)

		# Add data and test again
		id1 = Repo.create_account("Frame Alpha", "Doctor", collection_name=self.test_collection)
		Repo.create_account("Frame Beta", "Nurse", specialty="ICU", collection_name=self.test_collection)

		df = Repo.get_account_frame(collection_name=self.test_collection)
		self.assertIsInstance(df, DataFrame)
		self.assertEqual(len(df), 2)

		# Check if expected columns are present
		expected_cols = {"_id", "name", "role", "created_at", "updated_at"}
		self.assertTrue(expected_cols.issubset(set(df.columns)))

		# Verify content of a specific row
		alpha_row = df[df['_id'] == ObjectId(id1)]
		self.assertEqual(alpha_row.iloc[0]["name"], "Frame Alpha")

if __name__ == "__main__":
	try:
		logger().info("Starting MongoDB repository integration tests...")
		unittest.main(verbosity=2)
	finally:
		logger().info("Tests completed and database connection closed.")
