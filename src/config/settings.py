# src/config/settings.py
import os


class Settings:
	"""Application-wide settings."""
	# Memory settings
	MAX_TITLE_LENGTH: int = 50
	DEFAULT_TOP_K: int = 5
	SEMANTIC_CONTEXT_SIZE: int = 17
	SIMILARITY_THRESHOLD: float = 0.15
	EMBEDDING_MODEL_NAME: str = "MedEmbed-large-v0.1"
	NVIDIA_RERANKER_MODEL: str = "rerank-qa-mistral-4b"
	NVIDIA_RERANKER_ENDPOINT: str = "" # TODO

	# Safety Guard settings
	SAFETY_GUARD_ENABLED: bool = os.getenv("SAFETY_GUARD_ENABLED", "true").lower() == "true"
	SAFETY_GUARD_TIMEOUT: int = int(os.getenv("SAFETY_GUARD_TIMEOUT", "30"))
	SAFETY_GUARD_FAIL_OPEN: bool = os.getenv("SAFETY_GUARD_FAIL_OPEN", "true").lower() == "true"

# Create singleton instance
settings = Settings()
