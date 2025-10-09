# tests/routes/test_session_routes.py

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.api.routes.session import router as session_router
from src.core.state import get_state
from src.models.session import Message, Session

# --- Test Setup: Mocking and Dependency Injection ---

mock_memory_manager = MagicMock()

class MockAppState:
	def __init__(self):
		self.memory_manager = mock_memory_manager
		# Add mock rotators for the session endpoint
		self.gemini_rotator = MagicMock()
		self.nvidia_rotator = MagicMock()

def override_get_state() -> MockAppState:
	return MockAppState()

app = FastAPI()
app.include_router(session_router)
app.dependency_overrides[get_state] = override_get_state


# --- Fixtures ---

@pytest.fixture
def client():
	"""Provides a TestClient for making requests to the app."""
	with TestClient(app) as c:
		yield c

@pytest.fixture(autouse=True)
def reset_mocks():
	"""Resets mocks before each test to ensure test isolation."""
	mock_memory_manager.reset_mock()


# --- Test Data ---

fake_session_dict = {
	"_id": "session456",
	"account_id": "doctor789",
	"patient_id": "patient123",
	"title": "Checkup",
	"created_at": datetime.now(timezone.utc).isoformat(),
	"updated_at": datetime.now(timezone.utc).isoformat(),
	"messages": [],
}
fake_session = Session.model_validate(fake_session_dict)

fake_message_dict = {
	"_id": 1,
	"sent_by_user": True,
	"content": "Hello",
	"timestamp": datetime.now(timezone.utc).isoformat(),
}
fake_message = Message.model_validate(fake_message_dict)


# --- Tests for POST /session ---

def test_create_session_success(client: TestClient):
	"""Tests successful creation of a new chat session."""
	mock_memory_manager.create_session.return_value = fake_session

	session_data = {"account_id": "doctor789", "patient_id": "patient123", "title": "Checkup"}
	response = client.post("/session", json=session_data)

	assert response.status_code == status.HTTP_201_CREATED
	assert response.json()["title"] == "Checkup"
	mock_memory_manager.create_session.assert_called_once_with(
		user_id="doctor789", patient_id="patient123", title="Checkup"
	)

def test_create_session_failure(client: TestClient):
	"""Tests that a 500 error is returned if session creation fails."""
	mock_memory_manager.create_session.return_value = None

	session_data = {"account_id": "doctor789", "patient_id": "patient123"}
	response = client.post("/session", json=session_data)

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	assert response.json()["detail"] == "Failed to create session."


# --- Tests for GET /session/{session_id} ---

def test_get_session_success(client: TestClient):
	"""Tests successfully retrieving a session by its ID."""
	mock_memory_manager.get_session.return_value = fake_session

	response = client.get(f"/session/{fake_session.id}")

	assert response.status_code == status.HTTP_200_OK
	assert response.json()["title"] == fake_session.title
	mock_memory_manager.get_session.assert_called_once_with(str(fake_session.id))

def test_get_session_not_found(client: TestClient):
	"""Tests that a 404 error is returned for a non-existent session."""
	mock_memory_manager.get_session.return_value = None

	response = client.get("/session/non_existent_id")

	assert response.status_code == status.HTTP_404_NOT_FOUND
	assert response.json()["detail"] == "Session not found"


# --- Tests for DELETE /session/{session_id} ---

def test_delete_session_success(client: TestClient):
	"""Tests successful deletion of a session."""
	mock_memory_manager.delete_session.return_value = True

	response = client.delete(f"/session/{fake_session.id}")

	assert response.status_code == status.HTTP_204_NO_CONTENT
	mock_memory_manager.delete_session.assert_called_once_with(str(fake_session.id))

def test_delete_session_not_found(client: TestClient):
	"""Tests that a 404 is returned when trying to delete a non-existent session."""
	mock_memory_manager.delete_session.return_value = False

	response = client.delete("/session/non_existent_id")

	assert response.status_code == status.HTTP_404_NOT_FOUND
	assert response.json()["detail"] == "Session not found or already deleted"


# --- Tests for GET /session/{session_id}/messages ---

def test_list_messages_success(client: TestClient):
	"""Tests successfully listing messages for a session."""
	mock_memory_manager.get_session.return_value = fake_session
	mock_memory_manager.get_session_messages.return_value = [fake_message]

	response = client.get(f"/session/{fake_session.id}/messages?limit=10")

	assert response.status_code == status.HTTP_200_OK
	assert len(response.json()) == 1
	assert response.json()[0]["content"] == "Hello"
	mock_memory_manager.get_session.assert_called_once_with(str(fake_session.id))
	mock_memory_manager.get_session_messages.assert_called_once_with(str(fake_session.id), 10)

def test_list_messages_session_not_found(client: TestClient):
	"""Tests listing messages for a non-existent session."""
	mock_memory_manager.get_session.return_value = None

	response = client.get("/session/non_existent_id/messages")

	assert response.status_code == status.HTTP_404_NOT_FOUND
	assert response.json()["detail"] == "Session not found"


# --- Tests for POST /session/{session_id}/messages ---

@patch('src.api.routes.session.generate_medical_response', new_callable=AsyncMock)
def test_post_chat_message_success(mock_generate_response: AsyncMock, client: TestClient):
	"""Tests the full, successful flow of posting a message and getting a response."""
	# Arrange: Mock all async dependencies
	mock_memory_manager.get_enhanced_context = AsyncMock(return_value="Enhanced context.")
	mock_memory_manager.process_medical_exchange = AsyncMock(return_value="Generated summary.")
	mock_generate_response.return_value = "This is the AI response."

	chat_data = {"account_id": "doc1", "patient_id": "pat1", "message": "Patient has a fever."}
	response = client.post(f"/session/{fake_session.id}/messages", json=chat_data)

	assert response.status_code == status.HTTP_200_OK
	json_response = response.json()
	assert json_response["response"] == "This is the AI response."
	assert json_response["medical_context"] == "Enhanced context."

	# Assert that all async functions were called correctly
	mock_memory_manager.get_enhanced_context.assert_awaited_once()
	mock_generate_response.assert_awaited_once()
	mock_memory_manager.process_medical_exchange.assert_awaited_once()

@patch('src.api.routes.session.generate_medical_response', new_callable=AsyncMock)
def test_post_chat_message_context_error(mock_generate_response: AsyncMock, client: TestClient):
	"""Tests failure during the context generation step."""
	mock_memory_manager.get_enhanced_context = AsyncMock(side_effect=Exception("Context DB failed"))

	chat_data = {"account_id": "doc1", "patient_id": "pat1", "message": "Patient has a fever."}
	response = client.post(f"/session/{fake_session.id}/messages", json=chat_data)

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	assert response.json()["detail"] == "Failed to build medical context."
	mock_generate_response.assert_not_awaited() # Should fail before this is called

@patch('src.api.routes.session.generate_medical_response', new_callable=AsyncMock)
def test_post_chat_message_generation_error(mock_generate_response: AsyncMock, client: TestClient):
	"""Tests failure during the AI response generation step."""
	mock_memory_manager.get_enhanced_context = AsyncMock(return_value="Context")
	mock_generate_response.side_effect = Exception("AI model API is down")

	chat_data = {"account_id": "doc1", "patient_id": "pat1", "message": "Patient has a fever."}
	response = client.post(f"/session/{fake_session.id}/messages", json=chat_data)

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	assert response.json()["detail"] == "Failed to generate AI response."
