# config/settings.py

class Settings:
	# Memory settings
	MAX_TITLE_LENGTH: int = 50
	DEFAULT_TOP_K: int = 5
	SEMANTIC_CONTEXT_SIZE: int = 17
	SIMILARITY_THRESHOLD: float = 0.15

# Create singleton instance
settings = Settings()
