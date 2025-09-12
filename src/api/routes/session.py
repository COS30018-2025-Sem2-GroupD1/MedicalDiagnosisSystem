# api/routes/session.py

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from src.core.state import MedicalState, get_state
from src.models.chat import SessionRequest
from src.utils.logger import get_logger
from src.data.mongodb import list_patient_sessions, list_session_messages, ensure_session

logger = get_logger("SESSION_ROUTES", __name__)
router = APIRouter()

@router.post("/sessions")
async def create_chat_session(
	request: SessionRequest,
	state: MedicalState = Depends(get_state)
):
	"""Create a new chat session (cache + Mongo)"""
	try:
		logger.info(f"POST /sessions user_id={request.user_id} patient_id={request.patient_id} doctor_id={request.doctor_id}")
		session_id = state.memory_system.create_session(request.user_id, request.title or "New Chat")
		# Also ensure in Mongo with patient/doctor
		ensure_session(session_id=session_id, patient_id=request.patient_id, doctor_id=request.doctor_id, title=request.title or "New Chat")
		return {"session_id": session_id, "message": "Session created successfully"}
	except Exception as e:
		logger.error(f"Error creating session: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}")
async def get_chat_session(
	session_id: str,
	state: MedicalState = Depends(get_state)
):
	"""Get session from cache (for quick preview)"""
	try:
		session = state.memory_system.get_session(session_id)
		if not session:
			raise HTTPException(status_code=404, detail="Session not found")

		# Convert datetime objects to ISO format strings for JSON serialization
		return {
			"session_id": session.session_id,
			"user_id": session.user_id,
			"title": session.title,
			"created_at": session.created_at.isoformat(),
			"last_activity": session.last_activity.isoformat(),
			"messages": [{
				**msg,
				"timestamp": msg["timestamp"].isoformat() if isinstance(msg["timestamp"], datetime) else msg["timestamp"]
			} for msg in session.messages]
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error getting session: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/patients/{patient_id}/sessions")
async def list_sessions_for_patient(patient_id: str):
	"""List sessions for a patient from Mongo"""
	try:
		logger.info(f"GET /patients/{patient_id}/sessions")
		return {"sessions": list_patient_sessions(patient_id)}
	except Exception as e:
		logger.error(f"Error listing sessions: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages")
async def list_messages_for_session(session_id: str, patient_id: str, limit: int | None = None):
	"""List messages for a session from Mongo, verified to belong to the patient"""
	try:
		logger.info(f"GET /sessions/{session_id}/messages patient_id={patient_id} limit={limit}")
		msgs = list_session_messages(session_id, patient_id=patient_id, limit=limit)
		# ensure JSON-friendly timestamps
		for m in msgs:
			if isinstance(m.get("timestamp"), datetime):
				m["timestamp"] = m["timestamp"].isoformat()
			m["_id"] = str(m["_id"]) if "_id" in m else None
		return {"messages": msgs}
	except Exception as e:
		logger.error(f"Error listing messages: {e}")
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
