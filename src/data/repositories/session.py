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
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError, WriteError

from src.data.connection import (ActionFailed, Collections, get_collection,
                                 setup_collection)
from src.utils.logger import logger


def init(
	*,
	collection_name: str = Collections.SESSION,
	validator_path: str = "schemas/session_validator.json",
	drop: bool = False
):
	"""Initializes the collection, applying schema and indexes."""
	try:
		if drop:
			get_collection(collection_name).drop()
		setup_collection(collection_name, validator_path)
		get_collection(collection_name).create_index("messages._id")
		logger("Init").info(f"Created index on messages._id in '{collection_name}'")
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to initialize collection '{collection_name}': {e}")
		raise ActionFailed(f"Database operation failed during initialization: {e}") from e

def create_session(
	account_id: str,
	patient_id: str,
	title: str,
	*,
	collection_name: str = Collections.SESSION
) -> dict[str, Any]:
	"""Creates a new chat session, raising ActionFailed on error."""
	now = datetime.now(timezone.utc)
	try:
		collection = get_collection(collection_name)
		session_data: dict[str, Any] = {
			"account_id": ObjectId(account_id),
			"patient_id": ObjectId(patient_id),
			"title": title,
			"created_at": now,
			"updated_at": now,
			"messages": []
		}
		result = collection.insert_one(session_data)
		# Convert ObjectIds back to strings for the return value
		session_data["_id"] = str(result.inserted_id)
		session_data["patient_id"] = str(session_data["patient_id"])
		session_data["account_id"] = str(session_data["account_id"])
		return session_data
	except InvalidId as e:
		logger().error(f"Invalid ObjectId format provided for session creation: {e}")
		raise ActionFailed("Account ID or Patient ID is not a valid format.") from e
	except (WriteError, ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to create chat session: {e}")
		raise ActionFailed("A database error occurred while creating the session.") from e

def get_user_sessions(
	account_id: str,
	limit: int = 20,
	*,
	collection_name: str = Collections.SESSION
) -> list[dict[str, Any]]:
	"""Retrieves sessions for a user, raising ActionFailed on error."""
	try:
		obj_account_id = ObjectId(account_id)
		collection = get_collection(collection_name)
		cursor = collection.find(
			{"account_id": obj_account_id}
		).sort("updated_at", DESCENDING).limit(limit)

		results = []
		for session in cursor:
			session["_id"] = str(session["_id"])
			session["patient_id"] = str(session["patient_id"])
			session["account_id"] = str(session["account_id"])
			results.append(session)
		return results
	except InvalidId as e:
		logger().error(f"Invalid account_id format for get_user_sessions: '{account_id}'")
		raise ActionFailed("The provided account ID is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error listing sessions for account '{account_id}': {e}")
		raise ActionFailed("A database error occurred while retrieving user sessions.") from e

def list_patient_sessions(
	patient_id: str,
	limit: int = 20,
	*,
	collection_name: str = Collections.SESSION
) -> list[dict[str, Any]]:
	"""Retrieves sessions for a patient, raising ActionFailed on error."""
	try:
		obj_patient_id = ObjectId(patient_id)
		collection = get_collection(collection_name)
		cursor = collection.find(
			{"patient_id": obj_patient_id}
		).sort("updated_at", DESCENDING).limit(limit)

		results = []
		for session in cursor:
			session["_id"] = str(session["_id"])
			session["patient_id"] = str(session["patient_id"])
			session["account_id"] = str(session["account_id"])
			results.append(session)
		return results
	except InvalidId as e:
		logger().error(f"Invalid patient_id format for list_patient_sessions: '{patient_id}'")
		raise ActionFailed("The provided patient ID is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error listing sessions for patient '{patient_id}': {e}")
		raise ActionFailed("A database error occurred while retrieving patient sessions.") from e

def get_session(
	session_id: str,
	*,
	collection_name: str = Collections.SESSION
) -> dict[str, Any] | None:
	"""Retrieves a session. Returns None if not found, raises ActionFailed on error."""
	try:
		obj_session_id = ObjectId(session_id)
		collection = get_collection(collection_name)
		session = collection.find_one({"_id": obj_session_id})
		if session:
			session["_id"] = str(session["_id"])
			session["account_id"] = str(session["account_id"])
			session["patient_id"] = str(session["patient_id"])
		return session
	except InvalidId as e:
		logger().error(f"Invalid session_id format for get_session: '{session_id}'")
		raise ActionFailed("The provided session ID is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error retrieving session '{session_id}': {e}")
		raise ActionFailed("A database error occurred while retrieving the session.") from e

def get_session_messages(
	session_id: str,
	limit: int | None = None,
	*,
	collection_name: str = Collections.SESSION
) -> list[dict[str, Any]]:
	"""Gets messages from a session, raising ActionFailed on error."""
	try:
		obj_session_id = ObjectId(session_id)
		collection = get_collection(collection_name)
		pipeline = [
			{"$match": {"_id": obj_session_id}},
			{"$unwind": "$messages"},
			{"$sort": {"messages.timestamp": -1}}
		]
		if limit:
			pipeline.append({"$limit": limit})
		pipeline.append({"$replaceRoot": {"newRoot": "$messages"}})
		return list(collection.aggregate(pipeline))
	except InvalidId as e:
		logger().error(f"Invalid session_id format for get_session_messages: '{session_id}'")
		raise ActionFailed("The provided session ID is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error retrieving messages for session '{session_id}': {e}")
		raise ActionFailed("A database error occurred while retrieving messages.") from e

def update_session_title(
	session_id: str,
	title: str,
	*,
	collection_name: str = Collections.SESSION
) -> bool:
	"""Updates a session's title, raising ActionFailed on error."""
	try:
		obj_session_id = ObjectId(session_id)
		collection = get_collection(collection_name)
		result = collection.update_one(
			{"_id": obj_session_id},
			{
				"$set": {
					"title": title,
					"updated_at": datetime.now(timezone.utc)
				}
			}
		)
		return result.modified_count > 0
	except InvalidId as e:
		logger().error(f"Invalid session_id format for update_session_title: '{session_id}'")
		raise ActionFailed("The provided session ID is not a valid format.") from e
	except (WriteError, ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error updating title for session '{session_id}': {e}")
		raise ActionFailed("A database error occurred while updating the session title.") from e

def delete_session(
	session_id: str,
	*,
	collection_name: str = Collections.SESSION
) -> bool:
	"""Deletes a session, raising ActionFailed on error."""
	try:
		obj_session_id = ObjectId(session_id)
		collection = get_collection(collection_name)
		result = collection.delete_one({"_id": obj_session_id})
		return result.deleted_count > 0
	except InvalidId as e:
		logger().error(f"Invalid session_id format for delete_session: '{session_id}'")
		raise ActionFailed("The provided session ID is not a valid format.") from e
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error deleting session '{session_id}': {e}")
		raise ActionFailed("A database error occurred while deleting the session.") from e

def prune_old_sessions(
	days: int = 30,
	*,
	collection_name: str = Collections.SESSION
) -> int:
	"""Deletes old sessions, raising ActionFailed on error."""
	try:
		collection = get_collection(collection_name)
		cutoff = datetime.now(timezone.utc) - timedelta(days=days)
		result = collection.delete_many({"updated_at": {"$lt": cutoff}})
		if result.deleted_count > 0:
			logger().info(f"Deleted {result.deleted_count} old sessions (>{days} days)")
		return result.deleted_count
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error during session prune: {e}")
		raise ActionFailed("A database error occurred while pruning old sessions.") from e

def add_message(
	session_id: str,
	content: str,
	sent_by_user: bool,
	*,
	collection_name: str = Collections.SESSION
):
	"""Adds a message to a session, raising ActionFailed on error."""
	try:
		obj_session_id = ObjectId(session_id)
		collection = get_collection(collection_name)

		session = collection.find_one(
			{"_id": obj_session_id},
			{"messages": {"$slice": -1}} # Get last message only
		)
		if not session:
			raise ActionFailed(f"Chat session not found: {session_id}")

		messages = session.get("messages", [])
		next_id = messages[0]["_id"] + 1 if messages else 0
		now = datetime.now(timezone.utc)
		message_data: dict[str, Any] = {
			"_id": next_id,
			"sent_by_user": sent_by_user,
			"content": content,
			"timestamp": now
		}

		result = collection.update_one(
			{"_id": obj_session_id},
			{
				"$push": {"messages": message_data},
				"$set": {"updated_at": now}
			}
		)

		if result.modified_count == 0:
			# This could happen in a race condition or if the session was deleted mid-operation.
			raise ActionFailed(f"Failed to add message to session, no documents modified: {session_id}")

	except InvalidId as e:
		logger().error(f"Invalid session_id format for add_message: '{session_id}'")
		raise ActionFailed("The provided session ID is not a valid format.") from e
	except ActionFailed as e:
		# Re-raise the specific ActionFailed for "not found" or "not modified"
		logger().warning(str(e))
		raise
	except (WriteError, ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error adding message to session '{session_id}': {e}")
		raise ActionFailed("A database error occurred while adding the message.") from e
