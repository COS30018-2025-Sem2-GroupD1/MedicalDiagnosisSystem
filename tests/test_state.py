# tests/test_state.py

import unittest
from unittest.mock import MagicMock, patch

from src.core.state import AppState, get_state


class TestAppState(unittest.TestCase):
	"""Test suite for the AppState singleton and its initialization logic."""

	def tearDown(self):
		"""Resets the singleton after each test to ensure test isolation."""
		if hasattr(AppState, '_instance'):
			AppState._instance = None

	def test_singleton_instance_is_consistent(self):
		"""Tests that multiple calls to AppState() and get_state() return the same object instance."""
		instance1 = AppState()
		instance2 = AppState()
		instance3 = get_state()

		self.assertIs(instance1, instance2)
		self.assertIs(instance2, instance3)

	def test_init_logic_is_idempotent(self):
		"""Tests that the internal logic of __init__ does not re-run on subsequent calls."""
		state1 = AppState()
		self.assertTrue(state1._initialized)

		# Use a non-bool "marker" to verify the initialization logic is skipped on the next call.
		# The `# type: ignore` is needed because Pylance correctly infers _initialized as bool.
		state1._initialized = "marker"  # type: ignore

		state2 = AppState()

		self.assertIs(state1, state2)
		self.assertEqual(state2._initialized, "marker", "Initialization logic ran again when it should have been skipped.")

	@patch('src.core.state.MemoryManager')
	@patch('src.core.state.APIKeyRotator')
	@patch('src.core.state.EmbeddingClient')
	def test_initialize_creates_and_injects_dependencies(self, MockEmbeddingClient, MockAPIKeyRotator, MockMemoryManager):
		"""Tests that initialize() correctly instantiates and wires up all service dependencies."""
		mock_embedder_instance = MagicMock()
		mock_gemini_rotator_instance = MagicMock()
		mock_nvidia_rotator_instance = MagicMock()

		MockEmbeddingClient.return_value = mock_embedder_instance
		MockAPIKeyRotator.side_effect = [mock_gemini_rotator_instance, mock_nvidia_rotator_instance]

		state = get_state()
		state.initialize()

		MockEmbeddingClient.assert_called_once_with(model_name="all-MiniLM-L6-v2", dimension=384)
		MockAPIKeyRotator.assert_any_call("GEMINI_API_", max_slots=5)
		MockAPIKeyRotator.assert_any_call("NVIDIA_API_", max_slots=5)
		MockMemoryManager.assert_called_once_with(
			embedder=mock_embedder_instance,
			max_sessions_per_user=20
		)

		self.assertIs(state.embedding_client, mock_embedder_instance)
		self.assertIs(state.gemini_rotator, mock_gemini_rotator_instance)
		self.assertIs(state.nvidia_rotator, mock_nvidia_rotator_instance)

	def test_get_state_returns_appstate_instance(self):
		"""Tests that get_state() returns an object of type AppState."""
		state = get_state()
		self.assertIsInstance(state, AppState)

if __name__ == '__main__':
	unittest.main()
