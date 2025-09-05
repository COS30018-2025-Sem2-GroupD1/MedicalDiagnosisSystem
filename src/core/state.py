from src.core.memory.history import MedicalHistoryManager
from src.core.memory.memory import MemoryLRU
from src.utils.embeddings import EmbeddingClient, create_embedding_client
from src.utils.rotator import APIKeyRotator


class MedicalState:
	"""Global state management for Medical AI system"""
	_instance: 'MedicalState | None' = None

	def __init__(self):
		self.memory_system: MemoryLRU
		self.embedding_client: EmbeddingClient
		self.history_manager: MedicalHistoryManager
		self.gemini_rotator: APIKeyRotator
		self.nvidia_rotator: APIKeyRotator

	def initialize(self):
		"""Initialize all core components"""
		self.memory_system = MemoryLRU(capacity=50, max_sessions_per_user=20)
		self.embedding_client = create_embedding_client("all-MiniLM-L6-v2", dimension=384)
		self.history_manager = MedicalHistoryManager(self.memory_system, self.embedding_client)
		self.gemini_rotator = APIKeyRotator("GEMINI_API_", max_slots=5)
		self.nvidia_rotator = APIKeyRotator("NVIDIA_API_", max_slots=5)

	@classmethod
	def get_instance(cls) -> 'MedicalState':
		if cls._instance is None:
			cls._instance = MedicalState()
		return cls._instance

def get_state() -> MedicalState:
	"""FastAPI dependency for getting application state"""
	return MedicalState.get_instance()
