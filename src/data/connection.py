# data/connection.py
"""
MongoDB connection management and base database operations.
"""

import os
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.utils.logger import get_logger

logger = get_logger("MONGO")

# Global client instance
_mongo_client: MongoClient | None = None

# Collection Names
ACCOUNTS_COLLECTION = "accounts"
CHAT_SESSIONS_COLLECTION = "chat_sessions"
CHAT_MESSAGES_COLLECTION = "chat_messages"
MEDICAL_RECORDS_COLLECTION = "medical_records"
MEDICAL_MEMORY_COLLECTION = "medical_memory"
PATIENTS_COLLECTION = "patients"


def get_database() -> Database:
    """Get database instance with connection management"""
    global _mongo_client
    if _mongo_client is None:
        CONNECTION_STRING = os.getenv("MONGO_USER", "mongodb://127.0.0.1:27017/")  # fall back to local host if no user is provided
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
