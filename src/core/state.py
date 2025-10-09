# core/state.py

from src.core.memory_manager import MemoryManager
from src.utils.embeddings import EmbeddingClient
from src.utils.rotator import APIKeyRotator


class AppState:
	"""
	Manages the global state of the application's services using a Singleton pattern.
	This class acts as a dependency injection container.
	"""
	_instance = None

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super(AppState, cls).__new__(cls)
			cls._instance._initialized = False
		return cls._instance

	def __init__(self):
		if self._initialized:
			return
		# --- Core Services ---
		self.embedding_client: EmbeddingClient
		self.memory_manager: MemoryManager

		# --- API Key Rotators ---
		self.gemini_rotator: APIKeyRotator
		self.nvidia_rotator: APIKeyRotator

		self._initialized = True

	def initialize(self):
		"""Initializes all core application components in the correct order."""
		# Initialize components with no dependencies first
		self.embedding_client = EmbeddingClient(model_name="all-MiniLM-L6-v2", dimension=384)
		self.gemini_rotator = APIKeyRotator("GEMINI_API_", max_slots=5)
		self.nvidia_rotator = APIKeyRotator("NVIDIA_API_", max_slots=5)

		# Initialize the main service layer, injecting its dependencies
		self.memory_manager = MemoryManager(
			embedder=self.embedding_client,
			max_sessions_per_user=20
		)

def get_state() -> AppState:
	"""
	Provides access to the application state singleton.
	This function is designed for use as a dependency in an API framework.
	"""
	state = AppState()
	# The initialize method is idempotent, but it's good practice
	# to ensure it's called at least once on startup.
	# A web framework's startup event is the ideal place for this.
	return state
