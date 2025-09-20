# data/session/operations.py
"""
Session management operations for MongoDB.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from ..connection import get_collection, CHAT_SESSIONS_COLLECTION, CHAT_MESSAGES_COLLECTION
from src.utils.logger import get_logger

logger = get_logger("SESSION_OPS")


def create_chat_session(
    session_data: dict[str, Any],
    /,
    *,
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


def delete_session(
    session_id: str,
    /,
    *,
    collection_name: str = CHAT_SESSIONS_COLLECTION
) -> bool:
    """Delete a chat session from MongoDB"""
    collection = get_collection(collection_name)
    result = collection.delete_one({"session_id": session_id})
    return result.deleted_count > 0


def delete_session_messages(
    session_id: str,
    /,
    *,
    collection_name: str = CHAT_MESSAGES_COLLECTION
) -> int:
    """Delete all messages for a session from MongoDB"""
    collection = get_collection(collection_name)
    result = collection.delete_many({"session_id": session_id})
    return result.deleted_count


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
