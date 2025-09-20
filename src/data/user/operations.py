# data/user/operations.py
"""
User management operations for MongoDB.
"""

from datetime import datetime, timezone
from typing import Any

import re
from pandas import DataFrame
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from ..connection import get_collection, ACCOUNTS_COLLECTION
from src.utils.logger import get_logger

logger = get_logger("USER_OPS")


def get_account_frame(
    *,
    collection_name: str = ACCOUNTS_COLLECTION
) -> DataFrame:
    """Get accounts as a pandas DataFrame"""
    return DataFrame(get_collection(collection_name).find())


def create_account(
    user_data: dict[str, Any],
    /,
    *,
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
    /,
    *,
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
