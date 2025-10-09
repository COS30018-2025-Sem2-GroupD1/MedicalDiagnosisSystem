# tests/test_memory_manager.py
"""
Run locally: `SKIP_API_TESTS=1 python -m tests.test_memory_manager`
"""


import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.memory_manager import MemoryManager
from src.data.connection import ActionFailed
from src.models.account import Account
from src.models.medical import MedicalMemory, SemanticSearchResult
from src.models.patient import Patient
from src.models.session import Message, Session
from src.utils.embeddings import EmbeddingClient
from src.utils.rotator import APIKeyRotator

# Check an environment variable to see if API-dependent tests should be skipped
SKIP_API_TESTS = os.getenv('SKIP_API_TESTS', 'false').lower() in ('true', '1', 'yes')

# Use the modern unittest features for async code
class TestMemoryManager(unittest.IsolatedAsyncioTestCase):

	def setUp(self):
		"""Set up mocks and the MemoryManager instance before each test."""
		# 1. Mock the repository dependencies
		self.account_repo_patcher = patch('src.core.memory_manager.account_repo')
		self.patient_repo_patcher = patch('src.core.memory_manager.patient_repo')
		self.session_repo_patcher = patch('src.core.memory_manager.session_repo')
		self.memory_repo_patcher = patch('src.core.memory_manager.memory_repo')

		self.mock_account_repo = self.account_repo_patcher.start()
		self.mock_patient_repo = self.patient_repo_patcher.start()
		self.mock_session_repo = self.session_repo_patcher.start()
		self.mock_memory_repo = self.memory_repo_patcher.start()

		# 2. Mock the service dependencies, specifically using AsyncMock for async functions
		self.summarise_title_patcher = patch('src.core.memory_manager.summariser.summarise_title_with_nvidia', new_callable=AsyncMock)
		self.summarise_gemini_patcher = patch('src.core.memory_manager.summariser.summarise_qa_with_gemini', new_callable=AsyncMock)
		self.summarise_nvidia_patcher = patch('src.core.memory_manager.summariser.summarise_qa_with_nvidia', new_callable=AsyncMock)
		self.nvidia_chat_patcher = patch('src.core.memory_manager.nvidia_chat', new_callable=AsyncMock)

		self.mock_summarise_title = self.summarise_title_patcher.start()
		self.mock_summarise_gemini = self.summarise_gemini_patcher.start()
		self.mock_summarise_nvidia = self.summarise_nvidia_patcher.start()
		self.mock_nvidia_chat = self.nvidia_chat_patcher.start()

		# 3. Create instances of dependencies needed for MemoryManager
		self.mock_embedder = MagicMock(spec=EmbeddingClient)
		self.mock_gemini_rotator = MagicMock(spec=APIKeyRotator)
		self.mock_nvidia_rotator = MagicMock(spec=APIKeyRotator)

		# 4. Instantiate the class under test
		self.manager = MemoryManager(embedder=self.mock_embedder, max_sessions_per_user=20)

		# 5. Common test data
		self.user_id = "60c72b2f9b1d8b3b3c9d8b1a"
		self.patient_id = "60c72b2f9b1d8b3b3c9d8b1b"
		self.session_id = "60c72b2f9b1d8b3b3c9d8b1c"
		self.now = datetime.now(timezone.utc)

	def tearDown(self):
		"""Stop all patchers after each test."""
		patch.stopall()

	# --- Account Management Tests ---

	def test_create_account_success(self):
		self.mock_account_repo.create_account.return_value = self.user_id
		result = self.manager.create_account(name="Dr. Test", role="Doctor")
		self.assertEqual(result, self.user_id)
		self.mock_account_repo.create_account.assert_called_once_with(name="Dr. Test", role="Doctor", specialty=None)

	def test_create_account_failure(self):
		self.mock_account_repo.create_account.side_effect = ActionFailed("DB error")
		result = self.manager.create_account()
		self.assertIsNone(result)

	def test_get_account_success(self):
		mock_account = MagicMock(spec=Account)
		self.mock_account_repo.get_account.return_value = mock_account
		result = self.manager.get_account(self.user_id)
		self.assertEqual(result, mock_account)
		self.mock_account_repo.get_account.assert_called_once_with(self.user_id)

	def test_get_account_failure(self):
		self.mock_account_repo.get_account.side_effect = ActionFailed("DB error")
		result = self.manager.get_account(self.user_id)
		self.assertIsNone(result)

	def test_get_all_accounts_success(self):
		self.mock_account_repo.get_all_accounts.return_value = [MagicMock(spec=Account)]
		result = self.manager.get_all_accounts()
		self.assertEqual(len(result), 1)
		self.mock_account_repo.get_all_accounts.assert_called_once_with(limit=50)

	def test_get_all_accounts_failure(self):
		self.mock_account_repo.get_all_accounts.side_effect = ActionFailed("DB error")
		result = self.manager.get_all_accounts()
		self.assertEqual(result, [])

	def test_search_accounts_success(self):
		self.mock_account_repo.search_accounts.return_value = [MagicMock(spec=Account)]
		result = self.manager.search_accounts("query")
		self.assertEqual(len(result), 1)
		self.mock_account_repo.search_accounts.assert_called_once_with("query", limit=10)

	def test_search_accounts_failure(self):
		self.mock_account_repo.search_accounts.side_effect = ActionFailed("DB error")
		result = self.manager.search_accounts("query")
		self.assertEqual(result, [])

	# --- Patient Management Tests ---

	def test_create_patient_success(self):
		self.mock_patient_repo.create_patient.return_value = self.patient_id
		result = self.manager.create_patient(name="John Doe", age=40)
		self.assertEqual(result, self.patient_id)
		self.mock_patient_repo.create_patient.assert_called_once_with(name="John Doe", age=40)

	def test_create_patient_failure(self):
		self.mock_patient_repo.create_patient.side_effect = ActionFailed("DB error")
		result = self.manager.create_patient(name="John Doe")
		self.assertIsNone(result)

	def test_get_patient_by_id_success(self):
		mock_patient = MagicMock(spec=Patient)
		self.mock_patient_repo.get_patient_by_id.return_value = mock_patient
		result = self.manager.get_patient_by_id(self.patient_id)
		self.assertEqual(result, mock_patient)
		self.mock_patient_repo.get_patient_by_id.assert_called_once_with(self.patient_id)

	def test_get_patient_by_id_failure(self):
		self.mock_patient_repo.get_patient_by_id.side_effect = ActionFailed("DB error")
		result = self.manager.get_patient_by_id(self.patient_id)
		self.assertIsNone(result)

	def test_update_patient_profile_success(self):
		self.mock_patient_repo.update_patient_profile.return_value = 1
		updates = {"age": 41}
		result = self.manager.update_patient_profile(self.patient_id, updates)
		self.assertEqual(result, 1)
		self.mock_patient_repo.update_patient_profile.assert_called_once_with(self.patient_id, updates)

	def test_update_patient_profile_failure(self):
		self.mock_patient_repo.update_patient_profile.side_effect = ActionFailed("DB error")
		result = self.manager.update_patient_profile(self.patient_id, {})
		self.assertEqual(result, 0)

	# --- Session Management Tests ---

	def test_create_session_success(self):
		mock_session = MagicMock(spec=Session)
		self.mock_session_repo.create_session.return_value = mock_session
		result = self.manager.create_session(self.user_id, self.patient_id)
		self.assertEqual(result, mock_session)
		self.mock_session_repo.create_session.assert_called_once_with(self.user_id, self.patient_id, "New Chat")

	def test_create_session_failure(self):
		self.mock_session_repo.create_session.side_effect = ActionFailed("DB error")
		result = self.manager.create_session(self.user_id, self.patient_id)
		self.assertIsNone(result)

	def test_get_user_sessions_success(self):
		self.mock_session_repo.get_user_sessions.return_value = [MagicMock(spec=Session)]
		result = self.manager.get_user_sessions(self.user_id)
		self.assertEqual(len(result), 1)
		self.mock_session_repo.get_user_sessions.assert_called_once_with(self.user_id, limit=20)

	def test_delete_session_success(self):
		self.mock_session_repo.delete_session.return_value = True
		result = self.manager.delete_session(self.session_id)
		self.assertTrue(result)
		self.mock_session_repo.delete_session.assert_called_once_with(self.session_id)

	def test_delete_session_failure(self):
		self.mock_session_repo.delete_session.side_effect = ActionFailed("DB error")
		result = self.manager.delete_session(self.session_id)
		self.assertFalse(result)

	# --- Core Business Logic (Async) Tests ---

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_process_medical_exchange_success(self):
		question = "What are the side effects?"
		answer = "Common side effects include..."
		summary = "q: side effects a: common ones are..."
		embedding = [0.1, 0.2, 0.3]

		# Configure mocks
		self.mock_summarise_gemini.return_value = summary
		self.mock_embedder.embed.return_value = [embedding]
		self.manager._update_session_title_if_first_message = AsyncMock()

		# Call the method
		result = await self.manager.process_medical_exchange(
			self.session_id, self.patient_id, self.user_id, question, answer,
			self.mock_gemini_rotator, self.mock_nvidia_rotator
		)

		# Assertions
		self.assertEqual(result, summary)
		self.assertEqual(self.mock_session_repo.add_message.call_count, 2)
		self.mock_session_repo.add_message.assert_any_call(self.session_id, question, sent_by_user=True)
		self.mock_session_repo.add_message.assert_any_call(self.session_id, answer, sent_by_user=False)
		self.mock_summarise_gemini.assert_awaited_once()
		self.mock_embedder.embed.assert_called_once_with([summary])
		self.mock_memory_repo.create_memory.assert_called_once_with(
			patient_id=self.patient_id,
			doctor_id=self.user_id,
			session_id=self.session_id,
			summary=summary,
			embedding=embedding
		)
		self.manager._update_session_title_if_first_message.assert_awaited_once()

	async def test_process_medical_exchange_db_failure(self):
		self.mock_session_repo.add_message.side_effect = ActionFailed("DB write failed")
		result = await self.manager.process_medical_exchange(
			self.session_id, self.patient_id, self.user_id, "q", "a",
			self.mock_gemini_rotator, self.mock_nvidia_rotator
		)
		self.assertIsNone(result)

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_process_medical_exchange_embedding_failure(self):
		self.mock_embedder.embed.side_effect = Exception("Embedding model down")
		self.mock_summarise_gemini.return_value = "summary"
		self.manager._update_session_title_if_first_message = AsyncMock()

		await self.manager.process_medical_exchange(
			self.session_id, self.patient_id, self.user_id, "q", "a",
			self.mock_gemini_rotator, self.mock_nvidia_rotator
		)

		# Check that create_memory was still called, but with embedding=None
		self.mock_memory_repo.create_memory.assert_called_once()
		args, kwargs = self.mock_memory_repo.create_memory.call_args
		self.assertIsNone(kwargs.get("embedding"))

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_get_enhanced_context_full(self):
		question = "Is this medication safe?"
		# Mock data
		mock_stm = [MagicMock(spec=MedicalMemory, summary="STM summary 1")]
		mock_ltm = [MagicMock(spec=SemanticSearchResult, summary="LTM summary 1")]
		mock_messages = [MagicMock(spec=Message, sent_by_user=True, content="Previous question")]
		mock_session = MagicMock(spec=Session, messages=mock_messages)

		# Configure mocks
		self.mock_memory_repo.get_recent_memories.return_value = mock_stm
		self.mock_nvidia_chat.return_value = "STM summary 1"
		self.mock_embedder.embed.return_value = [[0.5]]
		self.mock_memory_repo.search_memories_semantic.return_value = mock_ltm
		self.mock_session_repo.get_session.return_value = mock_session

		# Call method
		context = await self.manager.get_enhanced_context(
			self.session_id, self.patient_id, question, self.mock_nvidia_rotator
		)

		# Assertions
		self.assertIn("Recent relevant medical context (STM)", context)
		self.assertIn("STM summary 1", context)
		self.assertIn("Semantically relevant medical history (LTM)", context)
		self.assertIn("LTM summary 1", context)
		self.assertIn("Current conversation", context)
		self.assertIn("User: Previous question", context)

		self.mock_memory_repo.get_recent_memories.assert_called_once_with(self.patient_id, limit=3)
		self.mock_nvidia_chat.assert_awaited_once()
		self.mock_memory_repo.search_memories_semantic.assert_called_once()
		self.mock_session_repo.get_session.assert_called_once_with(self.session_id)

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_get_enhanced_context_no_ltm(self):
		# Configure mocks for only STM and session context
		self.mock_memory_repo.get_recent_memories.return_value = [MagicMock(spec=MedicalMemory, summary="STM")]
		self.mock_nvidia_chat.return_value = "STM"
		self.mock_embedder.embed.return_value = [[0.5]]
		self.mock_memory_repo.search_memories_semantic.return_value = [] # No LTM results
		self.mock_session_repo.get_session.return_value = MagicMock(spec=Session, messages=[])

		context = await self.manager.get_enhanced_context(
			self.session_id, self.patient_id, "question", self.mock_nvidia_rotator
		)

		self.assertIn("Recent relevant medical context (STM)", context)
		self.assertNotIn("Semantically relevant medical history (LTM)", context)
		self.assertNotIn("Current conversation", context) # No messages

	# --- Private Helper (Async) Tests ---

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_update_session_title_if_first_message_success(self):
		question = "My leg hurts, what should I do?"
		mock_session = MagicMock(spec=Session, messages=[1, 2]) # Length is 2
		self.manager.get_session = MagicMock(return_value=mock_session)
		self.manager.update_session_title = MagicMock()
		self.mock_summarise_title.return_value = "Leg Pain Inquiry"

		await self.manager._update_session_title_if_first_message(
			self.session_id, question, self.mock_nvidia_rotator
		)

		self.manager.get_session.assert_called_once_with(self.session_id)
		self.mock_summarise_title.assert_awaited_once_with(question, self.mock_nvidia_rotator, max_words=5)
		self.manager.update_session_title.assert_called_once_with(self.session_id, "Leg Pain Inquiry")

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_update_session_title_not_first_message(self):
		mock_session = MagicMock(spec=Session, messages=[1, 2, 3]) # Length is not 2
		self.manager.get_session = MagicMock(return_value=mock_session)
		self.manager.update_session_title = MagicMock()

		await self.manager._update_session_title_if_first_message(
			self.session_id, "question", self.mock_nvidia_rotator
		)

		self.manager.get_session.assert_called_once_with(self.session_id)
		self.mock_summarise_title.assert_not_awaited()
		self.manager.update_session_title.assert_not_called()

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_generate_summary_gemini_success(self):
		self.mock_summarise_gemini.return_value = "Gemini summary"
		result = await self.manager._generate_summary("q", "a", self.mock_gemini_rotator, self.mock_nvidia_rotator)
		self.assertEqual(result, "Gemini summary")
		self.mock_summarise_gemini.assert_awaited_once()
		self.mock_summarise_nvidia.assert_not_awaited()

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_generate_summary_gemini_fails_nvidia_success(self):
		self.mock_summarise_gemini.return_value = None # Gemini fails
		self.mock_summarise_nvidia.return_value = "NVIDIA summary"
		result = await self.manager._generate_summary("q", "a", self.mock_gemini_rotator, self.mock_nvidia_rotator)
		self.assertEqual(result, "NVIDIA summary")
		self.mock_summarise_gemini.assert_awaited_once()
		self.mock_summarise_nvidia.assert_awaited_once()

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_generate_summary_all_fail(self):
		self.mock_summarise_gemini.return_value = None
		self.mock_summarise_nvidia.return_value = None
		result = await self.manager._generate_summary("question", "answer", self.mock_gemini_rotator, self.mock_nvidia_rotator)
		self.assertEqual(result, "Question: question\nAnswer: answer")

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_filter_summaries_for_relevance_success(self):
		summaries = ["Summary A", "Summary B", "Summary C"]
		self.mock_nvidia_chat.return_value = "Summary A\nSummary C"
		result = await self.manager._filter_summaries_for_relevance("question", summaries, self.mock_nvidia_rotator)
		self.assertEqual(result, ["Summary A", "Summary C"])
		self.mock_nvidia_chat.assert_awaited_once()

	@unittest.skipIf(SKIP_API_TESTS, "Skipping tests that require external APIs")
	async def test_filter_summaries_for_relevance_api_fails(self):
		summaries = ["Summary A", "Summary B"]
		self.mock_nvidia_chat.side_effect = Exception("API error")
		result = await self.manager._filter_summaries_for_relevance("question", summaries, self.mock_nvidia_rotator)
		# Should return all summaries as a fallback
		self.assertEqual(result, summaries)

if __name__ == '__main__':
	unittest.main()
