# data/repositories/utils.py

from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING
from pymongo.errors import (ConnectionFailure, DuplicateKeyError,
                            OperationFailure, PyMongoError)

from src.data.repositories.base import (ActionFailed, get_collection,
                                        get_database)
from src.utils.logger import logger


def create_index(
	collection_name: str,
	field_name: str,
	*,
	unique: bool = False
) -> None:
	"""Creates an index on a specified collection."""
	collection = get_collection(collection_name)
	collection.create_index([(field_name, ASCENDING)], unique=unique)

def delete_old_data(
	collection_name: str,
	*,
	days: int = 30
) -> int:
	"""Deletes data older than a specified number of days."""
	collection = get_collection(collection_name)
	cutoff = datetime.now(timezone.utc) - timedelta(days=days)
	result = collection.delete_many({
		"updated_at": {"$lt": cutoff}
	})
	return result.deleted_count

def backup_collection(collection_name: str) -> str:
	"""Creates a timestamped backup of a collection using an aggregation pipeline."""
	db = get_database()
	backup_name = f"{collection_name}_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

	if backup_name in db.list_collection_names():
		db.drop_collection(backup_name)

	source_collection = get_collection(collection_name)
	pipeline = [{"$match": {}}, {"$out": backup_name}]
	source_collection.aggregate(pipeline)

	doc_count = db[backup_name].count_documents({})
	logger().info(f"Created backup '{backup_name}' with {doc_count} documents.")
	return backup_name
