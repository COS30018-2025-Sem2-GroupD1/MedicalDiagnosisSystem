import unittest
from datetime import datetime

from src.data.connection import Collections
from src.data.repositories.account import (create_account, get_account,
                                           get_account_by_name,
                                           search_accounts, update_account)
from src.utils.logger import logger
from tests.base_test import BaseMongoTest


class TestAccountRepository(BaseMongoTest):
	def test_create_account(self):
		"""Test account creation with various parameters"""
		# Test basic creation
		account_id = create_account(
			name="Test Doctor",
			role="Doctor",
			collection_name=self._collections[Collections.ACCOUNT]
		)
		self.assertIsNotNone(account_id)

		# Test creation with specialty
		account_id = create_account(
			name="Specialist",
			role="Doctor",
			specialty="Cardiology",
			collection_name=self._collections[Collections.ACCOUNT]
		)
		doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(doc)
		self.assertEqual(doc["specialty"], "Cardiology") # type: ignore

	def test_update_account(self):
		"""Test account updates"""
		account_id = create_account(
			name="Update Test",
			role="Doctor",
			collection_name=self._collections[Collections.ACCOUNT]
		)

		# Test name update
		success = update_account(
			account_id,
			{"name": "Updated Name"},
			collection_name=self._collections[Collections.ACCOUNT]
		)
		self.assertTrue(success)

		# Verify created_at wasn't modified
		doc = self.get_doc_by_id(Collections.ACCOUNT, account_id)
		self.assertIsNotNone(doc)
		self.assertIsInstance(doc["created_at"], datetime) # type: ignore
		self.assertLess(doc["created_at"], doc["updated_at"]) # type: ignore

	def test_search_accounts(self):
		"""Test account search functionality"""
		# Create test accounts
		create_account("Alpha Doctor", "Doctor", collection_name=self._collections[Collections.ACCOUNT])
		create_account("Beta Doctor", "Doctor", collection_name=self._collections[Collections.ACCOUNT])
		create_account("Charlie Doctor", "Doctor", collection_name=self._collections[Collections.ACCOUNT])

		# Test search
		results = search_accounts("beta", collection_name=self._collections[Collections.ACCOUNT])
		self.assertEqual(len(results), 1)
		self.assertEqual(results[0]["name"], "Beta Doctor")

		# Test case insensitive
		results = search_accounts("ALPHA", collection_name=self._collections[Collections.ACCOUNT])
		self.assertEqual(len(results), 1)

		# Test limit
		results = search_accounts("Doctor", limit=2, collection_name=self._collections[Collections.ACCOUNT])
		self.assertEqual(len(results), 2)

if __name__ == "__main__":
	try:
		logger().info("Starting MongoDB repository integration tests...")
		unittest.main(verbosity=2)
	finally:
		logger().info("Tests completed and database connection closed.")
