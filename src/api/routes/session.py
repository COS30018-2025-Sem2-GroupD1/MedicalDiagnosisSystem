# api/routes/session.py

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.core.state import MedicalState, get_state
from src.data.repositories.session import delete_session, get_session_messages
from src.models.chat import SessionRequest
from src.utils.logger import logger

router = APIRouter(prefix="/session", tags=["Session"])

@router.post("")
async def create_chat_session(
	request: SessionRequest,
	state: MedicalState = Depends(get_state)
):
	"""Create a new chat session (cache + Mongo)"""
	try:
		logger().info(f"POST /session user_id={request.account_id} patient_id={request.patient_id}")
		session_id = state.memory_system.create_session(request.account_id, request.title or "New Chat")
		# Also ensure in Mongo with patient/doctor
		#ensure_session(session_id=session_id, patient_id=request.patient_id, doctor_id=request.doctor_id, title=request.title or "New Chat")
		return {"session_id": session_id, "message": "Session created successfully"}
	except Exception as e:
		logger().error(f"Error creating session: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}")
async def get_chat_session(
	session_id: str,
	state: MedicalState = Depends(get_state)
):
	"""Get session from cache (for quick preview)"""
	try:
		session = state.memory_system.get_session(session_id)
		if not session:
			raise HTTPException(status_code=404, detail="Session not found")

		return session.to_dict()
	except HTTPException:
		raise
	except Exception as e:
		logger().error(f"Error getting session: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/messages")
async def list_messages_for_session(session_id: str, limit: int | None = None):
	"""List messages for a session from Mongo, verified to belong to the patient"""
	try:
		logger().info(f"GET /session/{session_id}/messages limit={limit}")
		msgs = get_session_messages(session_id, limit)
		# ensure JSON-friendly timestamps
		for m in msgs:
			if isinstance(m.get("timestamp"), datetime):
				m["timestamp"] = m["timestamp"].isoformat()
			m["_id"] = str(m["_id"]) if "_id" in m else None
		return {"messages": msgs}
	except Exception as e:
		logger().error(f"Error listing messages: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_chat_session(
	session_id: str,
	state: MedicalState = Depends(get_state)
):
	"""Delete a chat session from both memory system and MongoDB"""
	try:
		logger().info(f"DELETE /session/{session_id}")

		# Delete from memory system
		state.memory_system.delete_session(session_id)

		# Delete from MongoDB
		session_deleted = delete_session(session_id)

		logger().info(f"Deleted session {session_id}: session={session_deleted}")

		return {
			"message": "Session deleted successfully",
			"session_deleted": session_deleted
		}
	except Exception as e:
		logger().error(f"Error deleting session: {e}")
		raise HTTPException(status_code=500, detail=str(e))
