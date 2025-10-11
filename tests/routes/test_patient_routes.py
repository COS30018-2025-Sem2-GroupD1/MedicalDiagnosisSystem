# tests/routes/test_patient_routes.py

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.api.routes.patient import router as patient_router
from src.core.state import get_state
from src.models.patient import Patient
from src.models.session import Session

# --- Test Setup: Mocking and Dependency Injection ---

# Mock the service layer that the API routes depend on.
mock_memory_manager = MagicMock()

# This mock AppState and override function will replace the real dependencies.
class MockAppState:
	def __init__(self):
		self.memory_manager = mock_memory_manager

def override_get_state() -> MockAppState:
	return MockAppState()

# Create a FastAPI app instance for testing and apply the dependency override.
app = FastAPI()
app.include_router(patient_router)
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

fake_patient_dict = {
	"_id": "patient123",
	"name": "Jane Doe",
	"age": 42,
	"sex": "Female",
	"ethnicity": "Caucasian",
	"created_at": datetime.now(timezone.utc).isoformat(),
	"updated_at": datetime.now(timezone.utc).isoformat(),
}
fake_patient = Patient.model_validate(fake_patient_dict)

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


# --- Tests for GET /patient ---

def test_search_patients_success(client: TestClient):
	"""Tests successfully searching for patients with a query."""
	mock_memory_manager.search_patients.return_value = [fake_patient]

	response = client.get("/patient?q=Jane&limit=5")

	assert response.status_code == status.HTTP_200_OK
	assert len(response.json()) == 1
	assert response.json()[0]["name"] == "Jane Doe"
	mock_memory_manager.search_patients.assert_called_once_with("Jane", limit=5)

def test_search_patients_requires_query(client: TestClient):
	"""Tests that a 400 error is returned if the search query 'q' is missing."""
	response = client.get("/patient")

	assert response.status_code == status.HTTP_400_BAD_REQUEST
	assert response.json()["detail"] == "A search query 'q' is required."


# --- Tests for POST /patient ---

def test_create_patient_success(client: TestClient):
	"""Tests successful creation of a new patient profile."""
	new_patient_id = "new_patient_abc"
	mock_memory_manager.create_patient.return_value = new_patient_id
	mock_memory_manager.get_patient_by_id.return_value = fake_patient

	patient_data = {"name": "Jane Doe", "age": 42, "sex": "Female", "ethnicity": "Caucasian"}
	response = client.post("/patient", json=patient_data)

	assert response.status_code == status.HTTP_201_CREATED
	assert response.json()["name"] == "Jane Doe"
	mock_memory_manager.create_patient.assert_called_once()
	mock_memory_manager.get_patient_by_id.assert_called_once_with(new_patient_id)

def test_create_patient_invalid_data(client: TestClient):
	"""Tests failure when the memory manager cannot create a patient (e.g., bad data)."""
	mock_memory_manager.create_patient.return_value = None

	patient_data = {"name": "Invalid", "age": -5, "sex": "F", "ethnicity": "Unknown"}
	response = client.post("/patient", json=patient_data)

	assert response.status_code == status.HTTP_400_BAD_REQUEST
	assert response.json()["detail"] == "Patient could not be created due to invalid data."

def test_create_patient_not_found_after_creation(client: TestClient):
	"""Tests the edge case where the patient can't be retrieved after creation."""
	new_patient_id = "new_patient_abc"
	mock_memory_manager.create_patient.return_value = new_patient_id
	mock_memory_manager.get_patient_by_id.return_value = None

	patient_data = {"name": "Jane Doe", "age": 42, "sex": "Female", "ethnicity": "Caucasian"}
	response = client.post("/patient", json=patient_data)

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	assert response.json()["detail"] == "Could not find newly created patient."


# --- Tests for GET /patient/{patient_id} ---

def test_get_patient_by_id_success(client: TestClient):
	"""Tests successfully retrieving a single patient by their ID."""
	mock_memory_manager.get_patient_by_id.return_value = fake_patient

	response = client.get(f"/patient/{fake_patient.id}")

	assert response.status_code == status.HTTP_200_OK
	assert response.json()["name"] == fake_patient.name
	mock_memory_manager.get_patient_by_id.assert_called_once_with(str(fake_patient.id))

def test_get_patient_by_id_not_found(client: TestClient):
	"""Tests that a 404 error is returned for a non-existent patient ID."""
	mock_memory_manager.get_patient_by_id.return_value = None

	response = client.get("/patient/non_existent_id")

	assert response.status_code == status.HTTP_404_NOT_FOUND
	assert response.json()["detail"] == "Patient not found"


# --- Tests for PATCH /patient/{patient_id} ---

def test_update_patient_success(client: TestClient):
	"""Tests a successful patient profile update."""
	mock_memory_manager.update_patient_profile.return_value = 1  # 1 document modified
	mock_memory_manager.get_patient_by_id.return_value = fake_patient

	update_data = {"age": 43}
	response = client.patch(f"/patient/{fake_patient.id}", json=update_data)

	assert response.status_code == status.HTTP_200_OK
	assert response.json()["name"] == fake_patient.name
	mock_memory_manager.update_patient_profile.assert_called_once_with(str(fake_patient.id), update_data)

def test_update_patient_no_fields_provided(client: TestClient):
	"""Tests that a 400 error is returned if the update request body is empty."""
	response = client.patch(f"/patient/{fake_patient.id}", json={})

	assert response.status_code == status.HTTP_400_BAD_REQUEST
	assert response.json()["detail"] == "No update fields provided."

def test_update_patient_not_found(client: TestClient):
	"""Tests updating a non-existent patient."""
	mock_memory_manager.update_patient_profile.return_value = 0
	# The route logic then checks if the patient exists. Simulate it not existing.
	mock_memory_manager.get_patient_by_id.return_value = None

	response = client.patch("/patient/non_existent_id", json={"age": 50})

	assert response.status_code == status.HTTP_404_NOT_FOUND
	assert response.json()["detail"] == "Patient not found"
	# Check that get_patient_by_id was called as part of the 404 check
	mock_memory_manager.get_patient_by_id.assert_called_once_with("non_existent_id")


# --- Tests for GET /patient/{patient_id}/session ---

def test_list_sessions_for_patient_success(client: TestClient):
	"""Tests successfully listing all sessions for a given patient."""
	mock_memory_manager.get_patient_by_id.return_value = fake_patient
	mock_memory_manager.list_patient_sessions.return_value = [fake_session]

	response = client.get(f"/patient/{fake_patient.id}/session")

	assert response.status_code == status.HTTP_200_OK
	assert len(response.json()) == 1
	assert response.json()[0]["title"] == "Checkup"
	# Verify it first checked that the patient exists
	mock_memory_manager.get_patient_by_id.assert_called_once_with(str(fake_patient.id))
	mock_memory_manager.list_patient_sessions.assert_called_once_with(str(fake_patient.id))

def test_list_sessions_for_patient_not_found(client: TestClient):
	"""Tests listing sessions for a non-existent patient."""
	mock_memory_manager.get_patient_by_id.return_value = None

	response = client.get("/patient/non_existent_id/session")

	assert response.status_code == status.HTTP_404_NOT_FOUND
	assert response.json()["detail"] == "Patient not found"
	mock_memory_manager.list_patient_sessions.assert_not_called()
