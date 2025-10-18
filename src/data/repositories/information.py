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

from src.data.connection import ActionFailed, Collections, get_collection
from src.models.information import InfoChunk, InfoChunkMetadata
from src.utils.logger import logger


def get_chunk(
	chunk_id: str,
	*,
	collection_name: str = Collections.INFORMATION
) -> InfoChunk:
	try:
		collection = get_collection(collection_name)
		cursor = collection.find(
			{"chunk_id": chunk_id}
		)

		return InfoChunk.model_validate(cursor[0])
	except (ConnectionFailure, PyMongoError) as e:
		logger().error(f"Database error listing sessions for chunk '{chunk_id}': {e}")
		raise ActionFailed("A database error occurred while retrieving chunk.") from e

# TODO Embedding search

# TODO Everything else :(
