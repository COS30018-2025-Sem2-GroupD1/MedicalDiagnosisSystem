# config/settings.py

class Settings:
	# Memory settings
	MAX_TITLE_LENGTH: int = 50
	DEFAULT_TOP_K: int = 5
	SEMANTIC_CONTEXT_SIZE: int = 17
	SIMILARITY_THRESHOLD: float = 0.15

	# API settings
	GEMINI_API_KEYS: list[str] = []
	NVIDIA_API_KEYS: list[str] = []
	API_TIMEOUT: int = 30

# Create singleton instance
settings = Settings()
