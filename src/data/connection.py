# data/repositories/base.py

import json
import os

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.utils.logger import logger

# TODO (Across all database files)
# Handle exceptions: `pymongo.errors.ConnectionFailure`, `pymongo.errors.OperationFailure`
# Handle cases where _id is not found

class ActionFailed(Exception):
	"""Raised when a database action fails."""

class EntryNotFound(Exception):
	"""Raised when an entry cannot be found in the database."""

_mongo_client: MongoClient | None = None

def get_database(db_name: str = "medicaldiagnosissystem") -> Database:
	"""Gets the database instance, managing a single connection."""
	global _mongo_client
	if _mongo_client is None:
		CONNECTION_STRING = os.getenv("MONGO_USER", "mongodb://127.0.0.1:27017/")  # Fall back to local host if no user is provided
		try:
			logger().info("Initializing MongoDB connection.")
			_mongo_client = MongoClient(CONNECTION_STRING)
		except Exception as e:
			logger().error(f"Failed to connect to MongoDB: {e}")
			# Pass the error down, code that calls this function should handle it
			raise
	return _mongo_client[db_name]

def close_connection():
	"""Closes the MongoDB connection."""
	global _mongo_client
	if _mongo_client:
		logger().info("Closing MongoDB connection.")
		_mongo_client.close()
		_mongo_client = None

def get_collection(name: str) -> Collection:
	"""Retrieves a MongoDB collection by name. Create it if it does not exist."""
	return get_database().get_collection(name)

def does_collection_exist(name: str) -> bool:
	return True if name in get_database().list_collection_names() else False

def create_collection(
	collection_name: str,
	validator_path: str,
	validation_level: str = "moderate"
):
	#get_collection(collection_name).drop()
	if does_collection_exist(collection_name):
		raise ActionFailed("Collection already exists")

	with open(validator_path, "r", encoding="utf-8") as f:
		validator = json.load(f)
	get_database().create_collection(
		collection_name,
		validator=validator,
		validationLevel=validation_level
	)

	logger(tag="create_collection").info(
		"Created '"
		+ collection_name
		+ "' collection with '"
		+ str(validator["$jsonSchema"]["title"]).lower()
		+ "'"
	)
