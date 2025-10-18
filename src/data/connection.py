# src/data/repositories/base.py

import json
import os

from pymongo import MongoClient
from pymongo.collection import Collection as pym_coll
from pymongo.database import Database as pym_db

from src.utils.logger import logger


class Collections:
	ACCOUNT = "accounts"
	PATIENT = "patients"
	SESSION = "sessions"
	MEDICAL_RECORDS = "medical_records"
	MEDICAL_MEMORY = "medical_memory"
	INFORMATION = "chunks"

class ActionFailed(Exception):
	"""
		Raised when a database action fails.
		Generic, non-specific exception that should be raised by any database access function when a more specific error has been caught.
	"""

_mongo_client: MongoClient | None = None

def get_database(db_name: str = "medicaldiagnosissystem") -> pym_db:
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

def get_collection(name: str) -> pym_coll:
	"""Retrieves a MongoDB collection by name. Create it if it does not exist."""
	return get_database().get_collection(name)

def does_collection_exist(name: str) -> bool:
	return name in get_database().list_collection_names()

def setup_collection(
	collection_name: str,
	validator_path: str,
	validation_level: str = "moderate"
):
	if not does_collection_exist(collection_name):
		get_database().create_collection(
			collection_name
		)
		logger(tag="setup_collection").info(f"Created '{collection_name}' collection")

	with open(validator_path, "r", encoding="utf-8") as f:
		validator = json.load(f)
	get_database().command({
		"collMod": collection_name,
		"validator": validator,
		"validationLevel": validation_level
	})

	lower_title = str(validator["$jsonSchema"]["title"]).lower()
	logger(tag="setup_collection").info(f"Applied '{lower_title}' to collection '{collection_name}'")
