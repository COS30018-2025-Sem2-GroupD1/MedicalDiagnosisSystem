# data/repositories/base.py

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.utils.logger import logger

# TODO (Across all database files)
# Handle exceptions: `pymongo.errors.ConnectionFailure`, `pymongo.errors.OperationFailure`
# Handle cases where _id is not found

class ActionFailed(Exception):
	"""Raised when a database action fails."""
	pass

_mongo_client: MongoClient | None = None

def get_database(db_name: str = 'medicaldiagnosissystem') -> Database:
	"""Gets the database instance, managing a single connection."""
	global _mongo_client
	if _mongo_client is None:
		# TODO: Use an environment variable for the connection string.
		CONNECTION_STRING = "mongodb://127.0.0.1:27017/"
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
	"""Retrieves a MongoDB collection by name."""
	db = get_database()
	return db.get_collection(name)
