# src/api/routes/chat.py

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.state import AppState, get_state
from src.models.session import (ChatRequest, ChatResponse, Message, Session,
                                SessionCreateRequest)
from src.services.medical_response import generate_medical_response
from src.services.guard import SafetyGuard
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

	# 0. Safety Guard: Validate user query
	try:
		safety_guard = SafetyGuard(state.nvidia_rotator)
		is_safe, safety_reason = safety_guard.check_user_query(req.message)
		if not is_safe:
			logger().warning(f"Safety guard blocked user query: {safety_reason}")
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST, 
				detail=f"Query blocked for safety reasons: {safety_reason}"
			)
		logger().info(f"User query passed safety validation: {safety_reason}")
	except Exception as e:
		logger().error(f"Safety guard error: {e}")
		# Fail open for now - allow query through if guard fails
		logger().warning("Safety guard failed, allowing query through")

	# 1. Get Enhanced Context
	try:
		medical_context = await state.memory_manager.get_enhanced_context(
			session_id=session_id,
			patient_id=req.patient_id,
			question=req.message,
			nvidia_rotator=state.nvidia_rotator
		)
	except Exception as e:
		logger().error(f"Error getting medical context: {e}")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to build medical context.")

	# 2. Generate AI Response
	try:
		# In a real app, user role/specialty would come from the authenticated user
		response_text = await generate_medical_response(
			user_message=req.message,
			user_role="Medical Professional",
			user_specialty="",
			rotator=state.gemini_rotator,
			medical_context=medical_context,
			nvidia_rotator=state.nvidia_rotator
		)
	except Exception as e:
		logger().error(f"Error generating medical response: {e}")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate AI response.")

	# 2.5. Safety Guard: Validate AI response
	try:
		is_safe, safety_reason = safety_guard.check_model_answer(req.message, response_text)
		if not is_safe:
			logger().warning(f"Safety guard blocked AI response: {safety_reason}")
			# Replace with safe fallback response
			response_text = "I apologize, but I cannot provide a response to that query as it may contain unsafe content. Please consult with a qualified healthcare professional for medical advice."
		else:
			logger().info(f"AI response passed safety validation: {safety_reason}")
	except Exception as e:
		logger().error(f"Safety guard error for response: {e}")
		# Fail open for now - allow response through if guard fails
		logger().warning("Safety guard failed for response, allowing through")

	# 3. Process and Store the Exchange
	summary = await state.memory_manager.process_medical_exchange(
		session_id=session_id,
		patient_id=req.patient_id,
		doctor_id=req.account_id,
		question=req.message,
		answer=response_text,
		gemini_rotator=state.gemini_rotator,
		nvidia_rotator=state.nvidia_rotator
	)
	if not summary:
		logger().warning(f"Failed to process and store medical exchange for session {session_id}")

	return ChatResponse(
		response=response_text,
		session_id=session_id,
		timestamp=datetime.now(timezone.utc),
		medical_context=medical_context
	)
