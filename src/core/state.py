# core/state.py

from src.core.history import MedicalHistoryManager
from src.core.memory import MemoryLRU
from src.utils.embeddings import EmbeddingClient
from src.utils.rotator import APIKeyRotator


class MedicalState:
	"""Manages the global state of the application using a Singleton pattern."""
	_instance = None

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super(MedicalState, cls).__new__(cls)
			cls._instance._initialized = False
		return cls._instance

	def __init__(self):
		if self._initialized:
			return
		self.memory_system: MemoryLRU
		self.embedding_client: EmbeddingClient
		self.history_manager: MedicalHistoryManager
		self.gemini_rotator: APIKeyRotator
		self.nvidia_rotator: APIKeyRotator
		self._initialized = True

	def initialize(self):
		"""Initializes all core application components."""
		self.memory_system = MemoryLRU(max_sessions_per_user=20)
		self.embedding_client = EmbeddingClient(model_name="all-MiniLM-L6-v2", dimension=384)
		# Keep only 3 short-term summaries/messages in cache
		#self.memory_system = MemoryLRU(capacity=3, max_sessions_per_user=20)
		self.history_manager = MedicalHistoryManager(self.memory_system, self.embedding_client)
		self.gemini_rotator = APIKeyRotator("GEMINI_API_", max_slots=5)
		self.nvidia_rotator = APIKeyRotator("NVIDIA_API_", max_slots=5)

def get_state() -> MedicalState:
	"""Provides access to the application state, for use as a dependency."""
	return MedicalState()
