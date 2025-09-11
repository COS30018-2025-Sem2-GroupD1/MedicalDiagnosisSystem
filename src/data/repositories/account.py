# data/repositories/account.py

from datetime import datetime, timezone
from typing import Any

from pymongo.errors import (ConnectionFailure, DuplicateKeyError,
                            OperationFailure, PyMongoError)

from src.data.repositories.base import ActionFailed, get_collection
from src.utils.logger import logger

ACCOUNTS_COLLECTION = "accounts"

class UserNotFound(Exception):
	"""Raised when a user is not found in the database."""
	pass

def create_account(
	user_data: dict[str, Any],
	*,
	collection_name: str = ACCOUNTS_COLLECTION
) -> str:
	"""Creates a new user account."""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	user_data.update({"created_at": now, "updated_at": now})
	try:
		result = collection.insert_one(user_data)
		logger().info(f"Created new account: {result.inserted_id}")
		return str(result.inserted_id)
	except DuplicateKeyError as e:
		logger().error(f"Failed to create account due to duplicate key: {e}")
		raise

def update_account(
	user_id: str,
	/,
	updates: dict[str, Any],
	*,
	collection_name: str = ACCOUNTS_COLLECTION
) -> bool:
	"""Updates an existing user account."""
	collection = get_collection(collection_name)
	if updates.get("created_at", None):
		logger().warning("Attempting to modify the 'created_at' attribute of an account. Do not do this.")
		updates.pop("created_at")
	updates["updated_at"] = datetime.now(timezone.utc)
	result = collection.update_one(
		{"_id": user_id},
		{"$set": updates}
	)
	return result.modified_count > 0

def get_user_profile(
	user_id: str,
	/, *,
	collection_name: str = ACCOUNTS_COLLECTION
) -> dict[str, Any] | None:
	"""Retrieves a user profile by ID and updates their last_seen timestamp."""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	return collection.find_one_and_update(
		{"_id": user_id},
		{
			"$set": {
				"last_seen": now
			}
		},
		return_document=True
	)

def set_user_preferences(
	user_id: str,
	/,
	update_data: dict[str, Any],
	*,
	collection_name: str = ACCOUNTS_COLLECTION
) -> bool:
	"""Sets a preference for a user."""
	try:
		collection = get_collection(collection_name)
		update_data = {f"preferences.{key}": value for key, value in update_data}
		update_data["updated_at"] = datetime.now(timezone.utc)
		result = collection.update_one(
			{"_id": user_id},
			{
				"$set": update_data
			}
		)
		if result.matched_count == 0:
			raise UserNotFound(f"User with ID '{user_id}' not found.")

		return result.modified_count > 0
	except PyMongoError as e:
		logger().error(f"An error occurred with the database operation: {e}")
		return False
	except UserNotFound as e:
		logger().error(e)
		return False
