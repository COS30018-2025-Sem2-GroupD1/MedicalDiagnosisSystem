# src/data/repositories/utils.py

from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING
from pymongo.errors import ConnectionFailure, PyMongoError

from src.data.connection import ActionFailed, get_collection, get_database
from src.utils.logger import logger


def create_index(
	collection_name: str,
	field_name: str,
	*,
	unique: bool = False
) -> None:
	"""
	Creates an index on a specified collection.

	Raises:
		ActionFailed: If a database error occurs.
	"""
	try:
		collection = get_collection(collection_name)
		collection.create_index([(field_name, ASCENDING)], unique=unique)
		logger().info(f"Ensured index exists on '{field_name}' for collection '{collection_name}'.")
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to create index on '{collection_name}': {e}")
		raise ActionFailed("A database error occurred while creating an index.") from e

def delete_old_data(
	collection_name: str,
	timestamp_field: str = "updated_at",
	*,
	days: int = 30
) -> int:
	"""
	Deletes documents from a collection older than a specified number of days.

	Args:
		collection_name: The name of the collection to prune.
		timestamp_field: The name of the datetime field to check. Defaults to "updated_at".
		days: The age in days beyond which documents will be deleted.

	Returns:
		The number of documents deleted.

	Raises:
		ActionFailed: If a database error occurs.
	"""
	try:
		collection = get_collection(collection_name)
		cutoff = datetime.now(timezone.utc) - timedelta(days=days)
		result = collection.delete_many({
			timestamp_field: {"$lt": cutoff}
		})
		if result.deleted_count > 0:
			logger().info(f"Deleted {result.deleted_count} old documents from '{collection_name}'.")
		return result.deleted_count
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to delete old data from '{collection_name}': {e}")
		raise ActionFailed("A database error occurred while deleting old data.") from e

def backup_collection(collection_name: str) -> str:
	"""
	Creates a timestamped backup of a collection using an aggregation pipeline.

	Returns:
		The name of the newly created backup collection.

	Raises:
		ActionFailed: If a database error occurs.
	"""
	try:
		db = get_database()
		backup_name = f"{collection_name}_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

		# This operation is idempotent, so no need to check for existence first.
		# The $out stage will automatically replace the collection if it exists.
		source_collection = get_collection(collection_name)
		pipeline = [{"$match": {}}, {"$out": backup_name}]
		source_collection.aggregate(pipeline)

		doc_count = db[backup_name].count_documents({})
		logger().info(f"Created backup '{backup_name}' with {doc_count} documents.")
		return backup_name
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to back up collection '{collection_name}': {e}")
		raise ActionFailed("A database error occurred during collection backup.") from e
