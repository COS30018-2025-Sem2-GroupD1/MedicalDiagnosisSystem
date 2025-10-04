# data/repositories/account.py
"""
User account management operations for MongoDB.
Each account represents a doctor.

## Fields
	_id: index
	name: The name attached to the account
	role: What type of account this is
	specialty: Any extra information about the account
	created_at: The timestamp when the account was created
	updated_at: The timestamp when the account data was last modified
"""

import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pandas import DataFrame
from pymongo import ASCENDING
from pymongo.errors import (ConnectionFailure, DuplicateKeyError,
                            OperationFailure, PyMongoError)

from src.data.connection import (ActionFailed, Collections, EntryNotFound,
                                 get_collection, setup_collection)
from src.utils.logger import logger

VALID_ROLES = [
	"Doctor",
	"Healthcare Prof",
	"Nurse",
	"Caregiver",
	"Physicion",
	"Medical Student",
	"Other"
]

def init(
	*,
	collection_name: str = Collections.ACCOUNT,
	validator_path: str = "schemas/account_validator.json",
	drop: bool = False
):
	if drop:
		get_collection(collection_name).drop()
	setup_collection(collection_name, validator_path)

# TODO Use this for database-status
def get_account_frame(
	*,
	collection_name: str = Collections.ACCOUNT
) -> DataFrame:
	"""Get accounts as a pandas DataFrame"""
	return DataFrame(get_collection(collection_name).find())

def create_account(
	name: str,
	role: str,
	specialty: str | None = None,
	*,
	collection_name: str = Collections.ACCOUNT
) -> str:
	"""Creates a new user account."""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	user_data: dict[str, Any] = {
		"name": name,
		"role" : role,
		"created_at": now,
		"updated_at": now
	}
	if specialty:
		user_data["specialty"] = specialty

	try:
		result = collection.insert_one(user_data)
		logger().info(f"Created new account: {result.inserted_id}")
		return str(result.inserted_id)
	except DuplicateKeyError as e:
		logger().error(f"Failed to create account due to duplicate key: {e}")
		raise

# TODO Make this more rigidly typed, maybe merge with create_account?
def update_account(
	user_id: str,
	updates: dict[str, Any],
	*,
	collection_name: str = Collections.ACCOUNT
) -> bool:
	"""Updates an existing user account."""
	collection = get_collection(collection_name)
	if updates.get("created_at", None):
		logger().warning("Attempting to modify the 'created_at' attribute of an account. Do not do this.")
		updates.pop("created_at")
	updates["updated_at"] = datetime.now(timezone.utc)
	result = collection.update_one(
		{"_id": ObjectId(user_id)},
		{"$set": updates}
	)
	return result.modified_count > 0

def get_account(
	user_id: str,
	*,
	collection_name: str = Collections.ACCOUNT
) -> dict[str, Any] | None:
	"""Retrieves an account by ID and updates their last_seen timestamp."""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	account = collection.find_one_and_update(
		{"_id": ObjectId(user_id)},
		{
			"$set": {
				"last_seen": now
			}
		},
		return_document=True
	)

	if account:
		account["_id"] = str(account["_id"])

	return account

def get_account_by_name(
	name: str,
	*,
	collection_name: str = Collections.ACCOUNT
) -> dict[str, Any] | None:
	"""Get account by name from accounts collection"""
	logger().info("Trying to retrieve account: " + name)
	collection = get_collection(collection_name)
	account = collection.find_one({"name": name})
	# Convert _id from an object to a string
	if account and "_id" in account:
		account["_id"] = str(account["_id"])
	return account

def search_accounts(
	query: str,
	limit: int = 10,
	*,
	collection_name: str = Collections.ACCOUNT
) -> list[dict[str, Any]]:
	"""Search accounts by name (case-insensitive contains) from accounts collection"""
	collection = get_collection(collection_name)
	if not query:
		return []

	logger().info(f"Searching accounts with query: '{query}', limit: {limit}")

	# Build a regex for name search
	pattern = re.compile(re.escape(query), re.IGNORECASE)

	try:
		cursor = collection.find({
			"name": {"$regex": pattern}
		}).sort(
			"name", ASCENDING
		).limit(limit)

		results = []
		for account in cursor:
			if account:
				account["_id"] = str(account["_id"])
				results.append(account)

		logger().info(f"Found {len(results)} accounts matching query")
		return results
	except Exception as e:
		logger().error(f"Error in search_account: {e}")
		return []

def get_all_accounts(
	limit: int = 50,
	*,
	collection_name: str = Collections.ACCOUNT
) -> list[dict[str, Any]]:
	"""Get all doctors with optional limit from accounts collection"""
	collection = get_collection(collection_name)
	try:
		cursor = collection.find().sort(
			"name", ASCENDING
		).limit(limit)

		results = []
		for account in cursor:
			if account:
				account["_id"] = str(account["_id"])
				results.append(account)

		logger().info(f"Retrieved {len(results)} doctors")
		return results
	except Exception as e:
		logger().error(f"Error getting all doctors: {e}")
		return []
