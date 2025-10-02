# emr/repositories/emr.py

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError

from src.data.connection import ActionFailed, setup_collection, get_collection
from src.utils.logger import logger
from src.emr.models.emr import EMRCreateRequest, EMRResponse, ExtractedData

EMR_COLLECTION = "emr"


def init():
    """Create the EMR collection with validation schema."""
    try:
        setup_collection(EMR_COLLECTION, "schemas/emr_validator.json")
        # Create indexes for better performance
        collection = get_collection(EMR_COLLECTION)
        collection.create_index("patient_id")
        collection.create_index("doctor_id")
        collection.create_index("session_id")
        collection.create_index("message_id")
        collection.create_index("created_at")
        collection.create_index([("patient_id", ASCENDING), ("created_at", DESCENDING)])
        collection.create_index([("patient_id", ASCENDING), ("doctor_id", ASCENDING)])
        collection.create_index([("session_id", ASCENDING), ("created_at", DESCENDING)])
        collection.create_index("confidence_score")
        logger().info("EMR collection created successfully with indexes")
    except Exception as e:
        logger().error(f"Error creating EMR collection: {e}")
        raise


def create_emr_entry(emr_data: EMRCreateRequest, embeddings: List[float]) -> str:
    """Create a new EMR entry in the database."""
    try:
        collection = get_collection(EMR_COLLECTION)

        # Check if EMR entry already exists for this message
        existing = collection.find_one({"message_id": emr_data.message_id})
        if existing:
            logger().warning(f"EMR entry already exists for message {emr_data.message_id}")
            return str(existing["_id"])

        now = datetime.now(timezone.utc)

        doc = {
            "patient_id": emr_data.patient_id,
            "doctor_id": emr_data.doctor_id,
            "message_id": emr_data.message_id,
            "session_id": emr_data.session_id,
            "original_message": emr_data.original_message,
            "extracted_data": emr_data.extracted_data.model_dump(),
            "embeddings": embeddings,
            "confidence_score": emr_data.confidence_score,
            "created_at": now,
            "updated_at": now
        }

        result = collection.insert_one(doc)
        logger().info(f"Created EMR entry for patient {emr_data.patient_id}, message {emr_data.message_id}")
        return str(result.inserted_id)

    except Exception as e:
        logger().error(f"Error creating EMR entry: {e}")
        raise


def get_emr_by_id(emr_id: str) -> Optional[Dict[str, Any]]:
    """Get an EMR entry by its ID."""
    try:
        collection = get_collection(EMR_COLLECTION)
        result = collection.find_one({"_id": ObjectId(emr_id)})
        if result:
            result["_id"] = str(result["_id"])
        return result
    except Exception as e:
        logger().error(f"Error getting EMR by ID {emr_id}: {e}")
        return None


def get_patient_emr_entries(
    patient_id: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get EMR entries for a specific patient, ordered by creation date."""
    try:
        collection = get_collection(EMR_COLLECTION)
        cursor = collection.find(
            {"patient_id": patient_id}
        ).sort("created_at", DESCENDING).skip(offset).limit(limit)

        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        logger().info(f"Retrieved {len(results)} EMR entries for patient {patient_id}")
        return results

    except Exception as e:
        logger().error(f"Error getting patient EMR entries: {e}")
        return []


def search_emr_by_semantic_similarity(
    patient_id: str,
    query_embeddings: List[float],
    limit: int = 10,
    threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """Search EMR entries using semantic similarity with embeddings."""
    try:
        collection = get_collection(EMR_COLLECTION)

        # Use MongoDB's vector search capabilities if available
        # For now, we'll implement a simple cosine similarity search
        pipeline = [
            {"$match": {"patient_id": patient_id}},
            {
                "$addFields": {
                    "similarity": {
                        "$let": {
                            "vars": {
                                "dotProduct": {
                                    "$reduce": {
                                        "input": {"$range": [0, {"$size": "$embeddings"}]},
                                        "initialValue": 0,
                                        "in": {
                                            "$add": [
                                                "$$value",
                                                {
                                                    "$multiply": [
                                                        {"$arrayElemAt": ["$embeddings", "$$this"]},
                                                        {"$arrayElemAt": [query_embeddings, "$$this"]}
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                },
                                "magnitudeA": {
                                    "$sqrt": {
                                        "$reduce": {
                                            "input": "$embeddings",
                                            "initialValue": 0,
                                            "in": {"$add": ["$$value", {"$multiply": ["$$this", "$$this"]}]}
                                        }
                                    }
                                },
                                "magnitudeB": {
                                    "$sqrt": {
                                        "$reduce": {
                                            "input": query_embeddings,
                                            "initialValue": 0,
                                            "in": {"$add": ["$$value", {"$multiply": ["$$this", "$$this"]}]}
                                        }
                                    }
                                }
                            },
                            "in": {
                                "$divide": [
                                    "$$dotProduct",
                                    {"$multiply": ["$$magnitudeA", "$$magnitudeB"]}
                                ]
                            }
                        }
                    }
                }
            },
            {"$match": {"similarity": {"$gte": threshold}}},
            {"$sort": {"similarity": DESCENDING}},
            {"$limit": limit}
        ]

        results = list(collection.aggregate(pipeline))
        for doc in results:
            doc["_id"] = str(doc["_id"])

        logger().info(f"Found {len(results)} similar EMR entries for patient {patient_id}")
        return results

    except Exception as e:
        logger().error(f"Error searching EMR by similarity: {e}")
        return []


def update_emr_entry(emr_id: str, updates: Dict[str, Any]) -> bool:
    """Update an EMR entry."""
    try:
        collection = get_collection(EMR_COLLECTION)
        updates["updated_at"] = datetime.now(timezone.utc)

        result = collection.update_one(
            {"_id": ObjectId(emr_id)},
            {"$set": updates}
        )

        success = result.modified_count > 0
        if success:
            logger().info(f"Updated EMR entry {emr_id}")
        else:
            logger().warning(f"No EMR entry found with ID {emr_id}")

        return success

    except Exception as e:
        logger().error(f"Error updating EMR entry {emr_id}: {e}")
        return False


def delete_emr_entry(emr_id: str) -> bool:
    """Delete an EMR entry."""
    try:
        collection = get_collection(EMR_COLLECTION)
        result = collection.delete_one({"_id": ObjectId(emr_id)})

        success = result.deleted_count > 0
        if success:
            logger().info(f"Deleted EMR entry {emr_id}")
        else:
            logger().warning(f"No EMR entry found with ID {emr_id}")

        return success

    except Exception as e:
        logger().error(f"Error deleting EMR entry {emr_id}: {e}")
        return False


def check_emr_exists(message_id: str) -> bool:
    """Check if an EMR entry already exists for a message."""
    try:
        collection = get_collection(EMR_COLLECTION)
        existing = collection.find_one({"message_id": message_id})
        return existing is not None
    except Exception as e:
        logger().error(f"Error checking EMR existence: {e}")
        return False


def get_emr_statistics(patient_id: str) -> Dict[str, Any]:
    """Get EMR statistics for a patient."""
    try:
        collection = get_collection(EMR_COLLECTION)

        pipeline = [
            {"$match": {"patient_id": patient_id}},
            {
                "$group": {
                    "_id": None,
                    "total_entries": {"$sum": 1},
                    "avg_confidence": {"$avg": "$confidence_score"},
                    "latest_entry": {"$max": "$created_at"},
                    "diagnosis_count": {
                        "$sum": {"$size": "$extracted_data.diagnosis"}
                    },
                    "medication_count": {
                        "$sum": {"$size": "$extracted_data.medications"}
                    }
                }
            }
        ]

        result = list(collection.aggregate(pipeline))
        if result:
            return result[0]
        else:
            return {
                "total_entries": 0,
                "avg_confidence": 0,
                "latest_entry": None,
                "diagnosis_count": 0,
                "medication_count": 0
            }

    except Exception as e:
        logger().error(f"Error getting EMR statistics: {e}")
        return {}
