# api/routes/user.py

from fastapi import APIRouter, Depends, HTTPException

from src.core.state import MedicalState, get_state
from src.data.repositories.account import create_account
from src.models.user import UserProfileRequest
from src.utils.logger import logger

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("")
async def create_user_profile(
	request: UserProfileRequest,
	state: MedicalState = Depends(get_state)
):
	"""Create or update user profile"""
	try:
		# Persist to in-memory profile (existing behavior)
		user = state.memory_system.create_user(user_id=request.user_id, name=request.name)
		user.set_preference("role", request.role)
		if request.specialty:
			user.set_preference("specialty", request.specialty)
		if request.medical_roles:
			user.set_preference("medical_roles", request.medical_roles)

		# Persist to MongoDB accounts collection
		account_id = create_account(
			request.name,
			request.role,
			request.specialty or None,
			request.medical_roles or [request.role] if request.role else [],
			user_id=request.user_id
		)

		return {"message": "User profile created successfully", "user_id": request.user_id, "account_id": account_id}
	except Exception as e:
		logger().error(f"Error creating user profile: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
async def get_user_profile(
	user_id: str,
	state: MedicalState = Depends(get_state)
):
	"""Get user profile and sessions"""
	try:
		user = state.memory_system.get_user(user_id)
		if not user:
			raise HTTPException(status_code=404, detail="User not found")

		sessions = state.memory_system.get_user_sessions(user_id)

		return {
			"user": {
				"id": user.user_id,
				"name": user.name,
				"role": user.preferences.get("role", "Unknown"),
				"specialty": user.preferences.get("specialty", ""),
				"medical_roles": user.preferences.get("medical_roles", []),
				"created_at": user.created_at,
				"last_seen": user.last_seen
			},
			"sessions": [
				{
					"id": session.session_id,
					"title": session.title,
					"created_at": session.created_at,
					"last_activity": session.last_activity,
					"message_count": len(session.messages)
				}
				for session in sessions if session is not None
			]
		}
	except HTTPException:
		raise
	except Exception as e:
		logger().error(f"Error getting user profile: {e}")
		raise HTTPException(status_code=500, detail=str(e))
