# tests/routes/test_account_routes.py

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.api.routes.account import router as account_router
from src.core.state import get_state
from src.data.connection import ActionFailed
from src.models.account import Account

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
app.include_router(account_router)
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

# A sample account object that can be reused in tests.
fake_account_dict = {
	"_id": "60c72b2f9b1d8b3b3c9d8b1a",
	"name": "Dr. Test",
	"role": "Doctor",
	"specialty": "Testing",
	"created_at": datetime.now(timezone.utc).isoformat(),
	"updated_at": datetime.now(timezone.utc).isoformat(),
	"last_seen": datetime.now(timezone.utc).isoformat(),
}
# Use model_validate to handle the string-based datetimes from the dict.
fake_account = Account.model_validate(fake_account_dict)


# --- Tests for GET /account ---

def test_get_all_accounts_success(client: TestClient):
	"""Tests successfully retrieving all accounts when no query is provided."""
	mock_memory_manager.get_all_accounts.return_value = [fake_account]

	response = client.get("/account?limit=10")

	assert response.status_code == status.HTTP_200_OK
	assert len(response.json()) == 1
	assert response.json()[0]["name"] == "Dr. Test"
	mock_memory_manager.get_all_accounts.assert_called_once_with(limit=10)
	mock_memory_manager.search_accounts.assert_not_called()

def test_search_accounts_success(client: TestClient):
	"""Tests successfully searching for accounts with a query."""
	mock_memory_manager.search_accounts.return_value = [fake_account]

	response = client.get("/account?q=Test&limit=5")

	assert response.status_code == status.HTTP_200_OK
	assert response.json()[0]["name"] == "Dr. Test"
	mock_memory_manager.search_accounts.assert_called_once_with("Test", limit=5)
	mock_memory_manager.get_all_accounts.assert_not_called()

def test_get_accounts_db_error(client: TestClient):
	"""Tests that a 500 error is returned if the database fails."""
	mock_memory_manager.get_all_accounts.side_effect = ActionFailed("DB connection lost")

	response = client.get("/account")

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	assert response.json()["detail"] == "A database error occurred."


# --- Tests for POST /account ---

def test_create_account_success(client: TestClient):
	"""Tests successful creation of a new account."""
	new_account_id = "new_fake_id_123"
	mock_memory_manager.create_account.return_value = new_account_id
	mock_memory_manager.get_account.return_value = fake_account

	account_data = {"name": "Dr. Test", "role": "Doctor", "specialty": "Testing"}
	response = client.post("/account", json=account_data)

	assert response.status_code == status.HTTP_201_CREATED
	assert response.json()["name"] == "Dr. Test"
	mock_memory_manager.create_account.assert_called_once_with(
		name="Dr. Test", role="Doctor", specialty="Testing"
	)
	mock_memory_manager.get_account.assert_called_once_with(new_account_id)

def test_create_account_creation_fails(client: TestClient):
	"""Tests the case where the memory manager fails to return an ID."""
	mock_memory_manager.create_account.return_value = None

	account_data = {"name": "Dr. Fail", "role": "Doctor"}
	response = client.post("/account", json=account_data)

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	assert response.json()["detail"] == "Failed to create account ID."

def test_create_account_not_found_after_creation(client: TestClient):
	"""Tests the edge case where the account can't be retrieved after creation."""
	new_account_id = "new_fake_id_123"
	mock_memory_manager.create_account.return_value = new_account_id
	mock_memory_manager.get_account.return_value = None # Simulate not found

	account_data = {"name": "Dr. Ghost", "role": "Doctor"}
	response = client.post("/account", json=account_data)

	assert response.status_code == status.HTTP_404_NOT_FOUND
	assert response.json()["detail"] == "Could not find newly created account."

def test_create_account_action_failed(client: TestClient):
	"""Tests that a 400 error is returned for data-related creation failures."""
	error_message = "Account with this name already exists."
	mock_memory_manager.create_account.side_effect = ActionFailed(error_message)

	account_data = {"name": "Dr. Duplicate", "role": "Doctor"}
	response = client.post("/account", json=account_data)

	assert response.status_code == status.HTTP_400_BAD_REQUEST
	assert response.json()["detail"] == error_message


# --- Tests for GET /account/{account_id} ---

def test_get_account_by_id_success(client: TestClient):
	"""Tests successfully retrieving a single account by its ID."""
	mock_memory_manager.get_account.return_value = fake_account

	response = client.get(f"/account/{fake_account.id}")

	assert response.status_code == status.HTTP_200_OK
	assert response.json()["name"] == fake_account.name
	mock_memory_manager.get_account.assert_called_once_with(str(fake_account.id))

def test_get_account_by_id_not_found(client: TestClient):
	"""Tests that a 404 error is returned for a non-existent account ID."""
	mock_memory_manager.get_account.return_value = None

	response = client.get("/account/non_existent_id")

	assert response.status_code == status.HTTP_404_NOT_FOUND
	assert response.json()["detail"] == "Account not found"

def test_get_account_by_id_db_error(client: TestClient):
	"""Tests that a 500 error is returned if the database fails during retrieval."""
	mock_memory_manager.get_account.side_effect = ActionFailed("DB connection lost")

	response = client.get(f"/account/{fake_account.id}")

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	assert response.json()["detail"] == "A database error occurred."
