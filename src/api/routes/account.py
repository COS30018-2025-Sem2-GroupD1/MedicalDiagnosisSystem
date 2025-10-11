# src/api/routes/account.py

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.state import AppState, get_state
from src.data.connection import ActionFailed
from src.models.account import Account, AccountCreateRequest
from src.utils.logger import logger

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("", response_model=list[Account])
async def get_all_accounts(
	limit: int = 50,
	state: AppState = Depends(get_state)
):
	"""
	Retrieves a list of all accounts.
	"""
	try:
		logger().info(f"GET /account limit={limit}")
		accounts = state.memory_manager.get_all_accounts(limit=limit)
		logger().info(f"Retrieved {len(accounts)} accounts")
		return accounts
	except ActionFailed as e:
		logger().error(f"Database error while getting accounts: {e}")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="A database error occurred.")


@router.get("/search", response_model=list[Account])
async def search_accounts(
	q: str,
	limit: int = 50,
	state: AppState = Depends(get_state)
):
	"""
	Searches for accounts by name.
	"""
	try:
		logger().info(f"GET /account/search?q='{q}' limit={limit}")
		accounts = state.memory_manager.search_accounts(q, limit=limit)
		logger().info(f"Retrieved {len(accounts)} accounts")
		return accounts
	except ActionFailed as e:
		logger().error(f"Database error while searching accounts: {e}")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="A database error occurred.")


@router.post("", response_model=Account, status_code=status.HTTP_201_CREATED)
async def create_account_profile(
	req: AccountCreateRequest,
	state: AppState = Depends(get_state)
):
	"""Creates a new account profile."""
	try:
		logger().info(f"POST /account name={req.name}")
		account_id = state.memory_manager.create_account(
			name=req.name,
			role=req.role,
			specialty=req.specialty
		)
		if not account_id:
			raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create account ID.")

		# Retrieve the full account object to return to the client
		new_account = state.memory_manager.get_account(account_id)
		if not new_account:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not find newly created account.")

		logger().info(f"Created account {req.name} id={account_id}")
		return new_account
	except ActionFailed as e:
		logger().error(f"Error creating account: {e}")
		# This could be a 409 Conflict if the name is a duplicate, but 400 is a safe bet for any data error.
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{account_id}", response_model=Account)
async def get_account_by_id(
	account_id: str,
	state: AppState = Depends(get_state)
):
	"""Retrieves a single account by its unique ID."""
	try:
		logger().info(f"GET /account/{account_id}")
		account = state.memory_manager.get_account(account_id)
		if not account:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
		return account
	except ActionFailed as e:
		logger().error(f"Error getting account '{account_id}': {e}")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="A database error occurred.")
