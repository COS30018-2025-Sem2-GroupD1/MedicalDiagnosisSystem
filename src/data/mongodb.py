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
import os

logger = get_logger("MONGO")

# Global client instance
_mongo_client: MongoClient | None = None

# Collection Names
ACCOUNTS_COLLECTION = "accounts"
CHAT_SESSIONS_COLLECTION = "chat_sessions"
MEDICAL_RECORDS_COLLECTION = "medical_records"
# DOCTORS_COLLECTION = "doctors"

# Base Database Operations
def get_database() -> Database:
	"""Get database instance with connection management"""
	global _mongo_client
	if _mongo_client is None:
		CONNECTION_STRING = os.getenv("MONGO_USER", "mongodb://127.0.0.1:27017/") # fall back to local host if no user is provided
		try:
			logger.info("Initializing MongoDB connection")
			_mongo_client = MongoClient(CONNECTION_STRING)
		except Exception as e:
			logger.error(f"Failed to connect to MongoDB: {str(e)}")
			# Pass the error down, code that calls this function should handle it
			raise e
	db_name = os.getenv("USER_DB", "medicaldiagnosissystem")
	return _mongo_client[db_name]

def close_connection():
	"""Close MongoDB connection"""
	global _mongo_client
	if _mongo_client is not None:
		# Close the connection and reset the client
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
	session_data["created_at"] = now
	session_data["updated_at"] = now
	if "_id" not in session_data:
		session_data["_id"] = str(ObjectId())
	result = collection.insert_one(session_data)
	return str(result.inserted_id)

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

# New: Chat and Medical Memory Persistence Helpers

CHAT_MESSAGES_COLLECTION = "chat_messages"
MEDICAL_MEMORY_COLLECTION = "medical_memory"
PATIENTS_COLLECTION = "patients"


def ensure_session(
	*,
	session_id: str,
	patient_id: str,
	doctor_id: str,
	title: str,
	last_activity: datetime | None = None,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> None:
	collection = get_collection(collection_name)
	now = datetime.now(timezone.utc)
	collection.update_one(
		{"session_id": session_id},
		{"$set": {
			"session_id": session_id,
			"patient_id": patient_id,
			"doctor_id": doctor_id,
			"title": title,
			"last_activity": (last_activity or now),
			"updated_at": now
		}, "$setOnInsert": {"created_at": now}},
		upsert=True
	)


def save_chat_message(
	*,
	session_id: str,
	patient_id: str,
	doctor_id: str,
	role: str,
	content: str,
	timestamp: datetime | None = None,
	collection_name: str = CHAT_MESSAGES_COLLECTION
) -> ObjectId:
	collection = get_collection(collection_name)
	ts = timestamp or datetime.now(timezone.utc)
	doc = {
		"session_id": session_id,
		"patient_id": patient_id,
		"doctor_id": doctor_id,
		"role": role,
		"content": content,
		"timestamp": ts,
		"created_at": ts
	}
	result = collection.insert_one(doc)
	return result.inserted_id


def list_session_messages(
	session_id: str,
	/,
	*,
	limit: int | None = None,
	collection_name: str = CHAT_MESSAGES_COLLECTION
) -> list[dict[str, Any]]:
	collection = get_collection(collection_name)
	cursor = collection.find({"session_id": session_id}).sort("timestamp", ASCENDING)
	if limit is not None:
		cursor = cursor.limit(limit)
	return list(cursor)


def save_memory_summary(
	*,
	patient_id: str,
	doctor_id: str,
	summary: str,
	embedding: list[float] | None = None,
	created_at: datetime | None = None,
	collection_name: str = MEDICAL_MEMORY_COLLECTION
) -> ObjectId:
	collection = get_collection(collection_name)
	ts = created_at or datetime.now(timezone.utc)
	doc = {
		"patient_id": patient_id,
		"doctor_id": doctor_id,
		"summary": summary,
		"created_at": ts
	}
	if embedding is not None:
		doc["embedding"] = embedding
	result = collection.insert_one(doc)
	return result.inserted_id


def get_recent_memory_summaries(
	patient_id: str,
	/,
	*,
	limit: int = 20,
	collection_name: str = MEDICAL_MEMORY_COLLECTION
) -> list[str]:
	collection = get_collection(collection_name)
	docs = list(collection.find({"patient_id": patient_id}).sort("created_at", DESCENDING).limit(limit))
	return [d.get("summary", "") for d in docs]

def search_memory_summaries_semantic(
	patient_id: str,
	query_embedding: list[float],
	/,
	*,
	limit: int = 5,
	similarity_threshold: float = 0.5, # >= 50% semantic similarity
	collection_name: str = MEDICAL_MEMORY_COLLECTION
) -> list[dict[str, Any]]:
	"""
	Search memory summaries using semantic similarity with embeddings.
	Returns list of {summary, similarity_score, created_at} sorted by similarity.
	"""
	collection = get_collection(collection_name)
	
	# Get all summaries with embeddings for this patient
	docs = list(collection.find({
		"patient_id": patient_id,
		"embedding": {"$exists": True}
	}))
	
	if not docs:
		return []
	
	# Calculate similarities
	import numpy as np
	query_vec = np.array(query_embedding, dtype="float32")
	results = []
	
	for doc in docs:
		embedding = doc.get("embedding")
		if not embedding:
			continue
			
		# Calculate cosine similarity
		doc_vec = np.array(embedding, dtype="float32")
		dot_product = np.dot(query_vec, doc_vec)
		norm_query = np.linalg.norm(query_vec)
		norm_doc = np.linalg.norm(doc_vec)
		
		if norm_query == 0 or norm_doc == 0:
			similarity = 0.0
		else:
			similarity = float(dot_product / (norm_query * norm_doc))
		
		if similarity >= similarity_threshold:
			results.append({
				"summary": doc.get("summary", ""),
				"similarity_score": similarity,
				"created_at": doc.get("created_at"),
				"session_id": doc.get("session_id")  # if we add this field later
			})
	
	# Sort by similarity (highest first) and return top results
	results.sort(key=lambda x: x["similarity_score"], reverse=True)
	return results[:limit]


def list_patient_sessions(
	patient_id: str,
	/,
	*,
	collection_name: str = CHAT_SESSIONS_COLLECTION
) -> list[dict[str, Any]]:
	collection = get_collection(collection_name)
	sessions = list(collection.find({"patient_id": patient_id}).sort("last_activity", DESCENDING))
	# Convert ObjectId to string for JSON serialization
	for session in sessions:
		if "_id" in session:
			session["_id"] = str(session["_id"])
	return sessions

# Patients helpers

def _generate_patient_id() -> str:
	# Generate zero-padded 8-digit ID
	import random
	return f"{random.randint(0, 99999999):08d}"

def get_patient_by_id(patient_id: str) -> dict[str, Any] | None:
	collection = get_collection(PATIENTS_COLLECTION)
	return collection.find_one({"patient_id": patient_id})

def create_patient(
	*,
	name: str,
	age: int,
	sex: str,
	address: str | None = None,
	phone: str | None = None,
	email: str | None = None,
	medications: list[str] | None = None,
	past_assessment_summary: str | None = None,
	assigned_doctor_id: str | None = None
) -> dict[str, Any]:
	collection = get_collection(PATIENTS_COLLECTION)
	now = datetime.now(timezone.utc)
	# Ensure unique 8-digit id
	for _ in range(10):
		pid = _generate_patient_id()
		if not collection.find_one({"patient_id": pid}):
			break
	else:
		raise RuntimeError("Failed to generate unique patient ID")
	doc = {
		"patient_id": pid,
		"name": name,
		"age": age,
		"sex": sex,
		"address": address,
		"phone": phone,
		"email": email,
		"medications": medications or [],
		"past_assessment_summary": past_assessment_summary or "",
		"assigned_doctor_id": assigned_doctor_id,
		"created_at": now,
		"updated_at": now
	}
	collection.insert_one(doc)
	return doc

def update_patient_profile(patient_id: str, updates: dict[str, Any]) -> int:
	collection = get_collection(PATIENTS_COLLECTION)
	updates["updated_at"] = datetime.now(timezone.utc)
	result = collection.update_one({"patient_id": patient_id}, {"$set": updates})
	return result.modified_count

def search_patients(query: str, limit: int = 10) -> list[dict[str, Any]]:
	"""Search patients by name (case-insensitive starts-with/contains) or partial patient_id."""
	collection = get_collection(PATIENTS_COLLECTION)
	if not query:
		return []
	
	logger.info(f"Searching patients with query: '{query}', limit: {limit}")
	
	# Build a regex for name search and patient_id partial match
	import re
	pattern = re.compile(re.escape(query), re.IGNORECASE)
	
	try:
		cursor = collection.find({
			"$or": [
				{"name": {"$regex": pattern}},
				{"patient_id": {"$regex": pattern}}
			]
		}).sort("name", ASCENDING).limit(limit)
		results = []
		for p in cursor:
			p["_id"] = str(p.get("_id")) if p.get("_id") else None
			results.append(p)
		logger.info(f"Found {len(results)} patients matching query")
		return results
	except Exception as e:
		logger.error(f"Error in search_patients: {e}")
		return []

# Doctor Management
def create_doctor(
	*,
	name: str,
	role: str | None = None,
	specialty: str | None = None,
	medical_roles: list[str] | None = None
) -> str:
	"""Create a new doctor profile"""
	collection = get_collection(ACCOUNTS_COLLECTION)
	now = datetime.now(timezone.utc)
	doctor_doc = {
		"name": name,
		"role": role,
		"specialty": specialty,
		"medical_roles": medical_roles or [],
		"created_at": now,
		"updated_at": now
	}
	try:
		result = collection.insert_one(doctor_doc)
		logger.info(f"Created new doctor: {name} with id {result.inserted_id}")
		return str(result.inserted_id)
	except Exception as e:
		logger.error(f"Error creating doctor: {e}")
		raise e

def get_doctor_by_name(name: str) -> dict[str, Any] | None:
	"""Get doctor by name from accounts collection"""
	collection = get_collection(ACCOUNTS_COLLECTION)
	doctor = collection.find_one({
		"name": name,
		"role": {"$in": ["Doctor", "Healthcare Prof", "General Practitioner", "Cardiologist", "Pediatrician", "Neurologist", "Dermatologist"]}
	})
	if doctor:
		doctor["_id"] = str(doctor.get("_id")) if doctor.get("_id") else None
	return doctor

def search_doctors(query: str, limit: int = 10) -> list[dict[str, Any]]:
	"""Search doctors by name (case-insensitive contains) from accounts collection"""
	collection = get_collection(ACCOUNTS_COLLECTION)
	if not query:
		return []
	
	logger.info(f"Searching doctors with query: '{query}', limit: {limit}")
	
	# Build a regex for name search
	import re
	pattern = re.compile(re.escape(query), re.IGNORECASE)
	
	try:
		cursor = collection.find({
			"name": {"$regex": pattern},
			"role": {"$in": ["Doctor", "Healthcare Prof", "General Practitioner", "Cardiologist", "Pediatrician", "Neurologist", "Dermatologist"]}
		}).sort("name", ASCENDING).limit(limit)
		results = []
		for d in cursor:
			d["_id"] = str(d.get("_id")) if d.get("_id") else None
			results.append(d)
		logger.info(f"Found {len(results)} doctors matching query")
		return results
	except Exception as e:
		logger.error(f"Error in search_doctors: {e}")
		return []

def get_all_doctors(limit: int = 50) -> list[dict[str, Any]]:
	"""Get all doctors with optional limit from accounts collection"""
	collection = get_collection(ACCOUNTS_COLLECTION)
	try:
		cursor = collection.find({
			"role": {"$in": ["Doctor", "Healthcare Prof", "General Practitioner", "Cardiologist", "Pediatrician", "Neurologist", "Dermatologist"]}
		}).sort("name", ASCENDING).limit(limit)
		results = []
		for d in cursor:
			d["_id"] = str(d.get("_id")) if d.get("_id") else None
			results.append(d)
		logger.info(f"Retrieved {len(results)} doctors")
		return results
	except Exception as e:
		logger.error(f"Error getting all doctors: {e}")
		return []
