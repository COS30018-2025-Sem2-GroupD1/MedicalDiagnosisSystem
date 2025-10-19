# src/data/repositories/information.py

"""
Contains all saved medical reference information to be used with RAG.
This may need to be renamed.

## Fields
	chunk_id:
	content:
	embedding:
	embedding_model:
	embedding_dim:
	metadata:
		metadata.parent_id:
		metadata.source:
		metadata.task:
		metadata.sequence:
		metadata.total_chunks:
		metadata.content_type:
		metadata.related_chunks:
		metadata.chunk_length:
		metadata.created_timestamp:
"""

from pymongo.errors import ConnectionFailure, PyMongoError

from src.data.connection import (ActionFailed, Collections, get_collection,
                                 setup_collection)
from src.models.information import InfoChunk
from src.utils.logger import logger


def init(
	*,
	collection_name: str = Collections.INFORMATION,
	validator_path: str = "schemas/information_validator.json",
	drop: bool = False
):
	"""Initializes the collection, applying schema and indexes."""
	try:
		if drop:
			get_collection(collection_name).drop()
		setup_collection(collection_name, validator_path)
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Failed to initialize collection '{collection_name}': {e}")
		raise ActionFailed(f"Database operation failed during initialization: {e}") from e

def get_chunk(
	chunk_id: str,
	*,
	collection_name: str = Collections.INFORMATION
) -> InfoChunk | None:
	"""Retrieves a single chunk by its unique ID."""
	try:
		collection = get_collection(collection_name)
		doc = collection.find_one({"chunk_id": chunk_id})
		return InfoChunk.model_validate(doc) if doc else None
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error getting chunk '{chunk_id}': {e}")
		raise ActionFailed("A database error occurred while retrieving chunk.") from e
	except Exception as e:
		logger().error(f"Failed to validate chunk data for '{chunk_id}': {e}")
		return None

def search_chunks_semantic(
	query_embedding: list[float],
	limit: int = 10,
	candidates: int = 100,
	*,
	collection_name: str = Collections.INFORMATION,
) -> list[InfoChunk]:
	"""
	Performs a semantic vector search on the information collection.

	NOTE: This function requires a Vector Search Index to be configured in
	MongoDB Atlas on the 'embedding' field.
	Example:
	{
		"name": "vector_index",
		"type": "vectorSearch",
		"fields": [
			{
				"type": "vector",
				"path": "embedding",
				"numDimensions": 1024, // MUST MATCH THE EMBEDDING DIMENSION
				"similarity": "cosine"
			}
		]
	}
	"""
	try:
		collection = get_collection(collection_name)
		pipeline = [
			{
				"$vectorSearch": {
					"index": "vector_index", # The name of the Atlas Vector Search index
					"path": "embedding",
					"queryVector": query_embedding,
					"numCandidates": candidates,
					"limit": limit,
				}
			},
			{
				"$project": {
					"_id": 0,
					"score": {"$meta": "vectorSearchScore"},
					"chunk_id": 1,
					"content": 1,
					"embedding": 1,
					"embedding_model": 1,
					"embedding_dim": 1,
					"metadata": 1,
				}
			},
		]
		results = list(collection.aggregate(pipeline))
		return [InfoChunk.model_validate(res) for res in results]
	except PyMongoError as e:
		# Specifically log if the index is missing, as it's a common setup error
		if "index not found" in str(e):
			logger().critical(
				"MongoDB Vector Search Index 'vector_index' not found! "
				"Semantic search will fail until the index is created in Atlas."
			)
		logger().error(f"Database error during semantic search: {e}")
		raise ActionFailed("A database error occurred during semantic search.") from e
	except Exception as e:
		logger().error(f"An unexpected error occurred during semantic search validation: {e}")
		return []
