# data/message/operations.py
"""
Message management operations for MongoDB.
"""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING

from ..connection import get_collection, CHAT_SESSIONS_COLLECTION, CHAT_MESSAGES_COLLECTION
from src.utils.logger import get_logger

logger = get_logger("MESSAGE_OPS")


def add_message(
    session_id: str,
    message_data: dict[str, Any],
    /,
    *,
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
    patient_id: str | None = None,
    limit: int | None = None,
    collection_name: str = CHAT_MESSAGES_COLLECTION
) -> list[dict[str, Any]]:
    collection = get_collection(collection_name)
    
    # First verify the session belongs to the patient
    if patient_id:
        session_collection = get_collection(CHAT_SESSIONS_COLLECTION)
        session = session_collection.find_one({
            "session_id": session_id,
            "patient_id": patient_id
        })
        if not session:
            logger.warning(f"Session {session_id} not found for patient {patient_id}")
            return []
    
    # Query messages with patient_id filter if provided
    query = {"session_id": session_id}
    if patient_id:
        query["patient_id"] = patient_id
        
    cursor = collection.find(query).sort("timestamp", ASCENDING)
    if limit is not None:
        cursor = cursor.limit(limit)
    return list(cursor)
