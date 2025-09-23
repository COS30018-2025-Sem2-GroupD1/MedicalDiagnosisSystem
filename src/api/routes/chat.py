# api/routes/chat.py

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.core.state import MedicalState, get_state
from src.data.repositories.session import ensure_session
from src.models.chat import ChatRequest, ChatResponse, SummariseRequest
from src.services.medical_response import generate_medical_response
from src.services.summariser import summarise_title_with_nvidia
from src.utils.logger import logger

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
	request: ChatRequest,
	state: MedicalState = Depends(get_state)
):
	"""
	Process a chat message, generate response, and persist short-term cache + long-term Mongo.
	"""
	start_time = time.time()

	try:
		logger().info(f"POST /chat user={request.user_id} session={request.session_id} patient={request.patient_id} doctor={request.doctor_id}")
		logger().info(f"Message: {request.message[:100]}...")  # Log first 100 chars of message

		# Get or create user profile (doctor as current user profile)
		user_profile = state.memory_system.get_user(request.user_id)
		if not user_profile:
			state.memory_system.create_user(request.user_id, request.user_role or "Anonymous")
			if request.user_specialty:
				state.memory_system.set_user_preferences(
					request.user_id,
					{"specialty": request.user_specialty}
				)

		# Get or create session (cache)
		session = state.memory_system.get_session(request.session_id)
		if not session:
			session_id = state.memory_system.create_session(request.user_id, request.title or "New Chat")
			request.session_id = session_id  # Update session ID if new session created
			session = state.memory_system.get_session(session_id)
			logger().info(f"Created new session: {session_id}")

		# Ensure session exists in Mongo with patient/doctor context
		ensure_session(session_id=request.session_id, patient_id=request.patient_id, doctor_id=request.doctor_id, title=request.title or "New Chat", last_activity=datetime.now(timezone.utc))

		# Get enhanced medical context with STM + LTM semantic search + NVIDIA reasoning
		medical_context = await state.history_manager.get_enhanced_conversation_context(
			request.user_id,
			request.session_id,
			request.message,
			state.nvidia_rotator,
			patient_id=request.patient_id
		)

		# Generate response using Gemini AI
		logger().info(f"Generating medical response using Gemini AI for user {request.user_id}")
		response = await generate_medical_response(
			request.message,
			request.user_role or "Medical Professional",
			request.user_specialty or "",
			state.gemini_rotator,
			medical_context
		)

		# Process and store the exchange
		try:
			await state.history_manager.process_medical_exchange(
				request.user_id,
				request.session_id,
				request.message,
				response,
				state.gemini_rotator,
				state.nvidia_rotator,
				patient_id=request.patient_id,
				doctor_id=request.doctor_id,
				session_title=request.title or "New Chat"
			)
		except Exception as e:
			logger().warning(f"Failed to process medical exchange: {e}")
			# Continue without storing if there's an error

		# Calculate response time
		response_time = time.time() - start_time

		logger().info(f"Generated response in {response_time:.2f}s for user {request.user_id}")
		logger().info(f"Response length: {len(response)} characters")

		return ChatResponse(
			response=response,
			session_id=request.session_id,
			timestamp=datetime.now(timezone.utc).isoformat(),
			medical_context=medical_context if medical_context else None
		)

	except Exception as e:
		logger().error(f"Error in chat endpoint: {e}")
		logger().error(f"Request data: {request.model_dump()}")
		raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/summarise")
async def summarise_endpoint(
	req: SummariseRequest,
	state: MedicalState = Depends(get_state)
):
	"""Summarise a text into a short 3-5 word title using NVIDIA if available."""
	try:
		title = await summarise_title_with_nvidia(req.text, state.nvidia_rotator, max_words=min(max(req.max_words or 5, 3), 7))
		return {"title": title}
	except Exception as e:
		logger().error(f"Error summarising title: {e}")
		raise HTTPException(status_code=500, detail=str(e))
