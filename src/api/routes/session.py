# src/api/routes/chat.py

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.response_pipeline import generate_chat_response
from src.core.state import AppState, get_state
from src.models.session import (ChatRequest, ChatResponse, Message, Session,
                                SessionCreateRequest)
from src.utils.logger import logger

router = APIRouter(prefix="/session", tags=["Session & Chat"])


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
	req: SessionCreateRequest,
	state: AppState = Depends(get_state)
):
	"""Creates a new, empty chat session."""
	logger().info(f"POST /session for patient_id={req.patient_id}")
	session = state.memory_manager.create_session(
		user_id=req.account_id,
		patient_id=req.patient_id,
		title=req.title or "New Chat"
	)
	if not session:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create session.")
	return session


@router.get("/{session_id}", response_model=Session)
async def get_chat_session(
	session_id: str,
	state: AppState = Depends(get_state)
):
	"""Retrieves a session's metadata and all its messages."""
	logger().info(f"GET /session/{session_id}")
	session = state.memory_manager.get_session(session_id)
	if not session:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
	return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
	session_id: str,
	state: AppState = Depends(get_state)
):
	"""Deletes a chat session permanently."""
	logger().info(f"DELETE /session/{session_id}")
	# UPDATED CALL
	success = state.memory_manager.delete_session(session_id)
	if not success:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or already deleted")
	return None


@router.get("/{session_id}/messages", response_model=list[Message])
async def list_messages_for_session(
	session_id: str,
	limit: int | None = None,
	state: AppState = Depends(get_state)
):
	"""Lists all messages for a specific session from the database."""
	logger().info(f"GET /session/{session_id}/messages limit={limit}")
	if not state.memory_manager.get_session(session_id):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

	# UPDATED CALL
	messages = state.memory_manager.get_session_messages(session_id, limit)
	return messages


@router.post("/{session_id}/messages", response_model=ChatResponse)
async def post_chat_message(
	session_id: str,
	req: ChatRequest,
	state: AppState = Depends(get_state)
):
	"""
	Posts a message to a session, gets a generated medical response,
	and persists the full exchange to long-term memory.
	"""
	logger().info(f"POST /session/{session_id}/messages")
	try:
		response = await generate_chat_response(
			state=state,
			message=req.message,
			session_id=session_id,
			patient_id=req.patient_id,
			account_id=req.account_id
		)
		return ChatResponse(response=response)
	except HTTPException as e:
		# Re-raise HTTPException to let FastAPI handle it
		raise e
	except Exception as e:
		logger().error(f"Unhandled error in chat pipeline: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="An unexpected error occurred."
		)
