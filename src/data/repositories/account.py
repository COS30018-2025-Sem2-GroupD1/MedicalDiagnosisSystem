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
#from warnings import deprecated

from bson import ObjectId
from bson.errors import InvalidId
from pandas import DataFrame
from pymongo import ASCENDING
from pymongo.errors import ConnectionFailure, PyMongoError, WriteError

from src.data.connection import (ActionFailed, Collections, get_collection,
                                 setup_collection)
from src.utils.logger import logger

VALID_ROLES = [
	"Doctor",
	"Healthcare Prof",
	"Nurse",
	"Caregiver",
	"Physician",
	"Medical Student",
	"Other"
]

def init(
	*,
	collection_name: str = Collections.ACCOUNT,
	validator_path: str = "schemas/account_validator.json",
	drop: bool = False
):
	"""Initializes the collection, applying schema validation."""
	try:
		if drop:
			get_collection(collection_name).drop()
		setup_collection(collection_name, validator_path)
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to initialize collection '{collection_name}': {e}")
		raise ActionFailed(f"Database operation failed during initialization: {e}") from e

def get_account_frame(
	*,
	collection_name: str = Collections.ACCOUNT
) -> DataFrame:
	"""Get accounts as a pandas DataFrame, raising ActionFailed on error."""
	try:
		collection = get_collection(collection_name)
		return DataFrame(collection.find())
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to retrieve account frame: {e}")
		raise ActionFailed(f"Could not retrieve accounts for DataFrame: {e}") from e

def create_account(
	name: str,
	role: str,
	specialty: str | None = None,
	*,
	collection_name: str = Collections.ACCOUNT
) -> str:
	"""Creates a new user account, raising ActionFailed on error."""
	now = datetime.now(timezone.utc)
	user_data: dict[str, Any] = {
		"name": name,
		"role" : role,
		"created_at": now,
		"updated_at": now,
		"last_seen": now
	}
	if specialty:
		user_data["specialty"] = specialty

	try:
		collection = get_collection(collection_name)
		result = collection.insert_one(user_data)
		logger().info(f"Created new account: {result.inserted_id}")
		return str(result.inserted_id)
	except WriteError as e:
		logger().error(f"Failed to create account due to data conflict: {e}")
		raise ActionFailed(f"Account could not be created. Data is conflicting or invalid.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error while creating account: {e}")
		raise ActionFailed(f"A database error occurred while creating the account.") from e

def update_account(
	user_id: str,
	updates: dict[str, Any],
	*,
	collection_name: str = Collections.ACCOUNT
) -> bool:
	"""Updates an existing user account, raising ActionFailed on error."""
	try:
		obj_user_id = ObjectId(user_id)
		collection = get_collection(collection_name)

		if "created_at" in updates:
			logger().warning("Attempting to modify the 'created_at' attribute of an account. This is not allowed.")
			updates.pop("created_at")
		updates["updated_at"] = datetime.now(timezone.utc)

		result = collection.update_one(
			{"_id": obj_user_id},
			{"$set": updates}
		)
		return result.modified_count > 0
	except InvalidId as e:
		logger().error(f"Invalid user_id format for update: '{user_id}'")
		raise ActionFailed(f"The provided user ID '{user_id}' is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error while updating account '{user_id}': {e}")
		raise ActionFailed(f"A database error occurred while updating the account.") from e

def get_account(
	user_id: str,
	*,
	collection_name: str = Collections.ACCOUNT
) -> dict[str, Any] | None:
	"""Retrieves an account by ID. Returns None if not found, raises ActionFailed on error."""
	try:
		obj_user_id = ObjectId(user_id)
		collection = get_collection(collection_name)
		now = datetime.now(timezone.utc)

		account = collection.find_one_and_update(
			{"_id": obj_user_id},
			{"$set": {"last_seen": now}},
			return_document=True
		)
		if account:
			account["_id"] = str(account["_id"])
		return account
	except InvalidId as e:
		logger().error(f"Invalid user_id format for get: '{user_id}'")
		raise ActionFailed(f"The provided user ID '{user_id}' is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error while getting account '{user_id}': {e}")
		raise ActionFailed(f"A database error occurred while retrieving the account.") from e

#@deprecated("Inferior to search_accounts")
def get_account_by_name(
	name: str,
	*,
	collection_name: str = Collections.ACCOUNT
) -> dict[str, Any] | None:
	"""
	Gets an account by name. Returns None if not found, raises ActionFailed on error.

	@depreciated
	"""
	logger().info(f"Trying to retrieve account: {name}")
	try:
		collection = get_collection(collection_name)
		now = datetime.now(timezone.utc)
		account = collection.find_one_and_update(
			{"name": name},
			{"$set": {"last_seen": now}},
			return_document=True
		)
		if account:
			account["_id"] = str(account["_id"])
		return account
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error while getting account by name '{name}': {e}")
		raise ActionFailed(f"A database error occurred while retrieving the account by name.") from e

def search_accounts(
	query: str,
	limit: int = 10,
	*,
	collection_name: str = Collections.ACCOUNT
) -> list[dict[str, Any]]:
	"""Searches accounts by name, raising ActionFailed on error."""
	if not query:
		return []

	logger().info(f"Searching accounts with query: '{query}', limit: {limit}")
	pattern = re.compile(re.escape(query), re.IGNORECASE)

	try:
		collection = get_collection(collection_name)
		cursor = collection.find({
			"name": {"$regex": pattern}
		}).sort("name", ASCENDING).limit(limit)

		results = [
			{**account, "_id": str(account["_id"])} for account in cursor
		]

		logger().info(f"Found {len(results)} accounts matching query")
		return results
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error during account search for query '{query}': {e}")
		raise ActionFailed(f"A database error occurred during the account search.") from e

def get_all_accounts(
	limit: int = 50,
	*,
	collection_name: str = Collections.ACCOUNT
) -> list[dict[str, Any]]:
	"""Gets all accounts, raising ActionFailed on error."""
	try:
		collection = get_collection(collection_name)
		cursor = collection.find().sort("name", ASCENDING).limit(limit)

		results = [
			{**account, "_id": str(account["_id"])} for account in cursor
		]

		logger().info(f"Retrieved {len(results)} accounts")
		return results
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error while getting all accounts: {e}")
		raise ActionFailed(f"A database error occurred while retrieving all accounts.") from e
