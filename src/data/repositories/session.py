# data/repositories/session.py
"""
Chat session management operations for MongoDB.
A session is owned by an account and is related to a patient.
A session contains many messages.

## Fields
	_id: index
	account_id: The user account who owns this session
	patient_id: The patient being discussed in this session
	title: The title of this session
	created_at: When this session was created
	updated_at: When this session was updated, new message or title
	messages: An array of messages sent in this session
		messages._id: index, the order the messages were sent
		messages.sent_by_user: Whether or not this was sent by the user or the ai
		messages.content: The actual contents of the message
		messages.timestamp: When the message was sent
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.errors import (ConnectionFailure, DuplicateKeyError,
                            OperationFailure, PyMongoError)

from src.data.connection import (ActionFailed, Collections, get_collection,
                                 setup_collection)
from src.utils.logger import logger


def init(
	*,
	collection_name: str = Collections.SESSION,
	validator_path: str = "schemas/session_validator.json",
	drop: bool = False
):
	if drop:
		get_collection(collection_name).drop()
	setup_collection(collection_name, validator_path)
	get_collection(Collections.SESSION).create_index("messages._id")
	logger("Init").info("Created index on messages._id")

def create_session(
	account_id: str,
	patient_id: str,
	title: str,
	*,
	collection_name: str = Collections.SESSION
) -> dict[str, Any]:
	"""Creates a new chat session."""
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	session_data: dict[str, Any] = {
		"account_id": ObjectId(account_id),
		"patient_id": ObjectId(patient_id),
		"title": title,
		"created_at": now,
		"updated_at": now,
		"messages": []  # Initialize empty messages array
	}
	try:
		result = collection.insert_one(session_data)
		session_data["_id"] = str(result.inserted_id)
		session_data["patient_id"] = str(session_data["patient_id"])
		session_data["account_id"] = str(session_data["account_id"])
		return session_data
	except Exception as e:
		logger().error(f"Failed to create chat session with data {session_data}: {e}")
		raise

def get_user_sessions(
	account_id: str,
	limit: int = 20,
	*,
	collection_name: str = Collections.SESSION
) -> list[dict[str, Any]]:
	"""Retrieves the most recent chat sessions for a specific user."""
	collection = get_collection(collection_name)
	cursor = collection.find(
		{"account_id": ObjectId(account_id)}
	).sort(
		"updated_at", DESCENDING
	).limit(limit)

	results = []
	for session in cursor:
		if session:
			session["_id"] = str(session["_id"])
			session["patient_id"] = str(session["patient_id"])
			session["account_id"] = str(session["account_id"])
			results.append(session)

	return results

def list_patient_sessions(
	patient_id: str,
	limit: int = 20,
	*,
	collection_name: str = Collections.SESSION
) -> list[dict[str, Any]]:
	collection = get_collection(collection_name)
	try:
		cursor = collection.find({
			"patient_id": ObjectId(patient_id)
		}).sort(
			"updated_at", DESCENDING
		).limit(limit)

		results = []
		for session in cursor:
			if session:
				session["_id"] = str(session["_id"])
				session["patient_id"] = str(session["patient_id"])
				session["account_id"] = str(session["account_id"])
				results.append(session)

		return results
	except Exception as e:
		logger().error(f"Error listing patient sessions for patient_id {patient_id}: {e}")
		# Re-raise the exception to be handled by the route
		raise

def get_session(
	session_id: str,
	*,
	collection_name: str = Collections.SESSION
) -> dict[str, Any] | None:
	"""Retrieves a single chat session by its ID."""
	collection = get_collection(collection_name)
	try:
		session = collection.find_one({"_id": ObjectId(session_id)})
		if session:
			session["_id"] = str(session["_id"])  # Convert ObjectId to string
		return session
	except Exception as e:
		logger().error(f"Error retrieving session {session_id}: {e}")
		return None

def get_session_messages(
	session_id: str,
	limit: int | None = None,
	*,
	collection_name: str = Collections.SESSION
) -> list[dict[str, Any]]:
	"""Get messages from a specific chat session"""
	collection = get_collection(collection_name)
	pipeline = [
		{"$match": {"_id": ObjectId(session_id)}},
		{"$unwind": "$messages"},
		{"$sort": {"messages.timestamp": -1}}
	]
	if limit:
		pipeline.append({"$limit": limit})
	return [doc["messages"] for doc in collection.aggregate(pipeline)]

def update_session_title(
	session_id: str,
	title: str,
	*,
	collection_name: str = Collections.SESSION
) -> bool:
	"""Updates the title of a chat session."""
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

def delete_session(
	session_id: str,
	*,
	collection_name: str = Collections.SESSION
) -> bool:
	"""Deletes a chat session."""
	collection = get_collection(collection_name)
	result = collection.delete_one({"_id": ObjectId(session_id)})
	return result.deleted_count > 0

def prune_old_sessions(
	days: int = 30,
	*,
	collection_name: str = Collections.SESSION
) -> int:
	"""Delete chat sessions older than specified days"""
	collection = get_collection(collection_name)
	cutoff = datetime.now(timezone.utc) - timedelta(days=days)
	result = collection.delete_many({
		"updated_at": {"$lt": cutoff}
	})
	if result.deleted_count > 0:
		logger().info(f"Deleted {result.deleted_count} old sessions (>{days} days)")
	return result.deleted_count

def add_message(
	session_id: str,
	content: str,
	sent_by_user: bool,
	*,
	collection_name: str = Collections.SESSION
):
	"""Add a message to a chat session"""
	collection = get_collection(collection_name)

	try:
		# Get current highest message ID
		session = collection.find_one(
			{"_id": ObjectId(session_id)},
			{"messages": {"$slice": -1}}  # Get last message only
		)
		if not session:
			raise ActionFailed(f"Chat session not found: {session_id}")

		messages = session.get("messages", [])
		next_id = messages[0]["_id"] + 1 if messages else 0

		now = datetime.now(timezone.utc)
		message_data: dict[str, Any] = {
			"_id": next_id,  # Required by schema
			"sent_by_user": sent_by_user,
			"content": content,
			"timestamp": now
		}

		result = collection.update_one(
			{"_id": ObjectId(session_id)},
			{
				"$push": {"messages": message_data},
				"$set": {"updated_at": now}
			}
		)

		if result.modified_count == 0:
			raise ActionFailed(f"Failed to add message to session: {session_id}")

	except Exception as e:
		logger().error(f"Failed to add message: {e}")
		raise ActionFailed("Failed to add message")
