from fastapi import APIRouter, Depends, HTTPException

from src.core.state import MedicalState, get_state
from src.models.chat import SessionRequest
from src.utils.logger import get_logger

logger = get_logger("SESSION_ROUTES", __name__)
router = APIRouter()

@router.post("/sessions")
async def create_chat_session(
	request: SessionRequest,
	state: MedicalState = Depends(get_state)
):
	"""Create a new chat session"""
	try:
		session_id = state.memory_system.create_session(request.user_id, request.title or "New Chat")
		return {"session_id": session_id, "message": "Session created successfully"}
	except Exception as e:
		logger.error(f"Error creating session: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}")
async def get_chat_session(
	session_id: str,
	state: MedicalState = Depends(get_state)
):
	"""Get chat session details and messages"""
	try:
		session = state.memory_system.get_session(session_id)
		if not session:
			raise HTTPException(status_code=404, detail="Session not found")

		return {
			"session_id": session.session_id,
			"user_id": session.user_id,
			"title": session.title,
			"created_at": session.created_at,
			"last_activity": session.last_activity,
			"messages": session.messages
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error getting session: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
	session_id: str,
	state: MedicalState = Depends(get_state)
):
	"""Delete a chat session"""
	try:
		state.memory_system.delete_session(session_id)
		return {"message": "Session deleted successfully"}
	except Exception as e:
		logger.error(f"Error deleting session: {e}")
		raise HTTPException(status_code=500, detail=str(e))
