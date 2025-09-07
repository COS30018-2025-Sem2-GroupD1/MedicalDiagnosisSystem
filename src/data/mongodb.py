# data/mongodb.py

"""
	Interface for mongodb using pymongo.
	Current code is simply a proof of concept and is not ready for implementation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from pandas import DataFrame
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from src.utils.logger import get_logger

logger = get_logger("MONGO")

# Global client instance
_mongo_client: MongoClient | None = None

# Collection Names
ACCOUNTS_COLLECTION = "accounts"
CHAT_SESSIONS_COLLECTION = "chat_sessions"
MEDICAL_RECORDS_COLLECTION = "medical_records"
MEDICAL_CONTEXT_COLLECTION = "medical_context"

# Base Database Operations
def get_database() -> Database:
	"""Get database instance with connection management"""
	global _mongo_client
	if _mongo_client is None:
		# TODO This needs to use an environment variable when deployed
		CONNECTION_STRING = "mongodb://127.0.0.1:27017/"
		try:
			logger.info("Initializing MongoDB connection")
			_mongo_client = MongoClient(CONNECTION_STRING)
		except Exception as e:
			logger.error(f"Failed to connect to MongoDB: {str(e)}")
			# Pass the error down, code that calls this function should handle it
			raise e
	return _mongo_client['medicaldiagnosissystem']

def close_connection():
	"""Close MongoDB connection"""
	global _mongo_client
	if _mongo_client is not None:
		logger.info("Closing MongoDB connection")
		_mongo_client.close()
		_mongo_client = None

def get_collection(name: str, /) -> Collection:
	"""Get a MongoDB collection by name"""
	db = get_database()
	return db.get_collection(name)


# Account Management
def get_account_frame(
	*,
	collection_name: str = ACCOUNTS_COLLECTION
) -> DataFrame:
	"""Get accounts as a pandas DataFrame"""
	return DataFrame(get_collection(collection_name).find())

def create_account(
	user_data: dict[str, Any],
	/, *,
	collection_name: str = ACCOUNTS_COLLECTION
) -> str:
	"""Create a new user account"""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	user_data["created_at"] = now
	user_data["updated_at"] = now
	try:
		result = collection.insert_one(user_data)
		logger.info(f"Created new account: {result.inserted_id}")
		return str(result.inserted_id)
	except DuplicateKeyError as e:
		logger.error(f"Failed to create account - duplicate key: {str(e)}")
		raise DuplicateKeyError(f"Account already exists: {e}") from e

def update_account(
	user_id: str,
	updates: dict[str, Any],
	/, *,
	collection_name: str = ACCOUNTS_COLLECTION
) -> bool:
	"""Update an existing user account"""
	collection = get_collection(collection_name)
	updates["updated_at"] = datetime.now(timezone.utc)
	result = collection.update_one(
		{"_id": user_id},
		{"$set": updates}
	)
	return result.modified_count > 0


# Chat Session Management
def create_chat_session(
	session_data: dict[str, Any],
	/, *,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> str:
	"""Create a new chat session"""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)

	try:
		# Log incoming data for debugging
		logger.debug(f"Creating session with data: {session_data}")

		# Ensure all required fields are present with proper types
		session_data.update({
			"created_at": now,
			"updated_at": now,
			"messages": session_data.get("messages", []),
			"title": str(session_data.get("title", "New Chat")),
			"user_id": str(session_data["user_id"])  # Will raise KeyError if missing
		})

		if "_id" not in session_data:
			session_data["_id"] = str(ObjectId())

		result = collection.insert_one(session_data)
		session_id = str(result.inserted_id)
		logger.info(f"Created new session: {session_id}")

		# Verify the session was created
		created_session = collection.find_one({"_id": session_data["_id"]})
		if not created_session:
			raise ValueError("Session was not created successfully")

		return session_id
	except Exception as e:
		logger.error(f"Failed to create chat session: {e}")
		logger.error(f"Session data: {session_data}")
		logger.error("Stack trace:", exc_info=True)
		raise

def get_user_sessions(
	user_id: str,
	/,
	limit: int = 20,
	*,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> list[dict[str, Any]]:
	"""Get chat sessions for a specific user"""
	collection = get_collection(collection_name)
	return list(collection.find(
		{"user_id": user_id}
	).sort("updated_at", DESCENDING).limit(limit))


# Message History
def add_message(
	session_id: str,
	message_data: dict[str, Any],
	/, *,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> str | None:
	"""Add a message to a chat session"""
	collection = get_collection(collection_name)

	# Verify session exists first
	session = collection.find_one({
		"$or": [
			{"_id": session_id},
			{"_id": ObjectId(session_id) if ObjectId.is_valid(session_id) else None}
		]
	})
	if not session:
		logger.error(f"Failed to add message - session not found: {session_id}")
		raise ValueError(f"Chat session not found: {session_id}")

	now = datetime.now(timezone.utc)
	message_data["timestamp"] = now
	result = collection.update_one(
		{"_id": session["_id"]},
		{
			"$push": {"messages": message_data},
			"$set": {"updated_at": now}
		}
	)
	return str(session_id) if result.modified_count > 0 else None

def get_session_messages(
	session_id: str,
	/,
	limit: int | None = None,
	*,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> list[dict[str, Any]]:
	"""Get messages from a specific chat session"""
	collection = get_collection(collection_name)
	pipeline = [
		{"$match": {"_id": session_id}},
		{"$unwind": "$messages"},
		{"$sort": {"messages.timestamp": -1}}
	]
	if limit:
		pipeline.append({"$limit": limit})
	return [doc["messages"] for doc in collection.aggregate(pipeline)]


# Medical Records
def create_medical_record(
	record_data: dict[str, Any],
	/, *,
	collection_name: str = MEDICAL_RECORDS_COLLECTION
) -> str:
	"""Create a new medical record"""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	record_data["created_at"] = now
	record_data["updated_at"] = now
	result = collection.insert_one(record_data)
	return str(result.inserted_id)

def get_user_medical_records(
	user_id: str,
	/, *,
	collection_name: str = MEDICAL_RECORDS_COLLECTION
) -> list[dict[str, Any]]:
	"""Get medical records for a specific user"""
	collection = get_collection(collection_name)
	return list(collection.find({"user_id": user_id}).sort("created_at", ASCENDING))


# User Preferences
def get_user_profile(
	user_id: str,
	/, *,
	collection_name: str = ACCOUNTS_COLLECTION
) -> dict[str, Any] | None:
	"""Get a user profile by ID and update last seen"""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	result = collection.find_one_and_update(
		{"_id": user_id},
		{"$set": {"last_seen": now}},
		return_document=True
	)
	return result

def set_user_preference(
	user_id: str,
	key: str,
	value: Any,
	/, *,
	collection_name: str = ACCOUNTS_COLLECTION
) -> bool:
	"""Set a user preference"""
	collection = get_collection(collection_name)
	result = collection.update_one(
		{"_id": user_id},
		{
			"$set": {
				f"preferences.{key}": value,
				"updated_at": datetime.now(timezone.utc)
			}
		}
	)
	return result.modified_count > 0

def delete_chat_session(
	session_id: str,
	/, *,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> bool:
	"""Delete a chat session"""
	collection = get_collection(collection_name)
	result = collection.delete_one({"_id": session_id})
	return result.deleted_count > 0

def update_session_title(
	session_id: str,
	title: str,
	/, *,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> bool:
	"""Update chat session title"""
	collection = get_collection(collection_name)
	result = collection.update_one(
		{"_id": session_id},
		{
			"$set": {
				"title": title,
				"updated_at": datetime.now(timezone.utc)
			}
		}
	)
	return result.modified_count > 0

def get_session(
	session_id: str,
	/, *,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> dict[str, Any] | None:
	"""Get a chat session by ID"""
	collection = get_collection(collection_name)
	try:
		# Try direct ID match first
		result = collection.find_one({"_id": session_id})
		if result:
			logger.debug(f"Found session with direct ID match: {session_id}")
			return result

		# Try ObjectId if direct match failed
		if ObjectId.is_valid(session_id):
			result = collection.find_one({"_id": ObjectId(session_id)})
			if result:
				logger.debug(f"Found session with ObjectId: {session_id}")
				return result

		logger.info(f"Session not found: {session_id}")
		return None
	except Exception as e:
		logger.error(f"Error retrieving session {session_id}: {e}")
		logger.error("Stack trace:", exc_info=True)
		raise


# Medical Context Management
def add_medical_context(
	user_id: str,
	summary: str,
	/, *,
	collection_name: str = MEDICAL_CONTEXT_COLLECTION
) -> str:
	"""Add a medical context summary"""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	doc = {
		"_id": str(ObjectId()),
		"user_id": user_id,
		"summary": summary,
		"timestamp": now
	}
	result = collection.insert_one(doc)
	return str(result.inserted_id)

def get_medical_context(
	user_id: str,
	/,
	limit: int | None = None,
	*,
	collection_name: str = MEDICAL_CONTEXT_COLLECTION
) -> list[dict[str, Any]]:
	"""Get medical context summaries for a user"""
	collection = get_collection(collection_name)
	query = {"user_id": user_id}
	cursor = collection.find(query).sort("timestamp", DESCENDING)
	if limit:
		cursor = cursor.limit(limit)
	return list(cursor)

def delete_old_medical_context(
	days: int = 30,
	*,
	collection_name: str = MEDICAL_CONTEXT_COLLECTION
) -> int:
	"""Delete medical context older than specified days"""
	collection = get_collection(collection_name)
	cutoff = datetime.now(timezone.utc) - timedelta(days=days)
	result = collection.delete_many({
		"timestamp": {"$lt": cutoff}
	})
	return result.deleted_count

# Utility Functions
def create_index(
	collection_name: str,
	field_name: str,
	/,
	unique: bool = False
) -> None:
	"""Create an index on a collection"""
	collection = get_collection(collection_name)
	collection.create_index([(field_name, ASCENDING)], unique=unique)

def delete_old_sessions(
	days: int = 30,
	*,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> int:
	"""Delete chat sessions older than specified days"""
	collection = get_collection(collection_name)
	cutoff = datetime.now(timezone.utc) - timedelta(days=days)
	result = collection.delete_many({
		"updated_at": {"$lt": cutoff}
	})
	if result.deleted_count > 0:
		logger.info(f"Deleted {result.deleted_count} old sessions (>{days} days)")
	return result.deleted_count

def backup_collection(collection_name: str) -> str:
	"""Create a backup of a collection"""
	collection = get_collection(collection_name)
	backup_name = f"{collection_name}_backup_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
	db = get_database()

	# Drop existing backup if it exists
	if backup_name in db.list_collection_names():
		logger.info(f"Removing existing backup: {backup_name}")
		db.drop_collection(backup_name)

	db.create_collection(backup_name)
	backup = db[backup_name]

	doc_count = 0
	for doc in collection.find():
		backup.insert_one(doc)
		doc_count += 1

	logger.info(f"Created backup {backup_name} with {doc_count} documents")
	return backup_name
