# data/utils.py
"""
Utility functions for MongoDB operations.
"""

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING

from .connection import get_collection, get_database
from src.utils.logger import get_logger

logger = get_logger("MONGO_UTILS")


def create_index(
    collection_name: str,
    field_name: str,
    /,
    unique: bool = False
) -> None:
    """Create an index on a collection"""
    collection = get_collection(collection_name)
    collection.create_index([(field_name, ASCENDING)], unique=unique)


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
