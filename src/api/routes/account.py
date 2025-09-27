# api/routes/account.py

from fastapi import APIRouter, HTTPException

from src.data.repositories.account import (create_account, get_account_by_name,
                                           get_all_accounts, search_accounts)
from src.models.user import AccountCreateRequest
from src.utils.logger import logger

router = APIRouter(prefix="/account", tags=["Account"])

@router.get("")
async def get_all_accounts_route(limit: int = 50):
	try:
		logger(tag="All").info(f"GET /account limit={limit}")
		results = get_all_accounts(limit=limit)
		logger().info(f"Retrieved {len(results)} accounts")
		return {"results": results}
	except Exception as e:
		logger().error(f"Error getting all accounts: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_account_profile(req: AccountCreateRequest):
	try:
		logger().info(f"POST /account name={req.name}")
		account_id = create_account(
			name=req.name,
			role=req.role,
			specialty=req.specialty
		)
		logger().info(f"Created account {req.name} id={account_id}")
		return {"account_id": account_id, "name": req.name}
	except Exception as e:
		logger().error(f"Error creating account: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/{account_name}")
async def get_account(account_name: str):
	try:
		logger(tag="By name").info(f"GET /account/{account_name}")
		account = get_account_by_name(account_name)
		if not account:
			raise HTTPException(status_code=404, detail="account not found")
		return account
	except HTTPException:
		raise
	except Exception as e:
		logger().error(f"Error getting account: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_accounts_route(q: str, limit: int = 10):
	try:
		logger().info(f"GET /account/search q='{q}' limit={limit}")
		results = search_accounts(q, limit=limit)
		logger().info(f"account search returned {len(results)} results")
		return {"results": results}
	except Exception as e:
		logger().error(f"Error searching accounts: {e}")
		raise HTTPException(status_code=500, detail=str(e))
