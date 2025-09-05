import time

from fastapi import APIRouter, Depends, HTTPException

from src.core.state import MedicalState, get_state
from src.models.chat import ChatRequest, ChatResponse, SummarizeRequest
from src.services.medical_response import generate_medical_response_with_gemini
from src.services.summariser import summarize_title_with_nvidia
from src.utils.logger import get_logger

logger = get_logger("CHAT_ROUTES", __name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
	request: ChatRequest,
	state: MedicalState = Depends(get_state)
):
	"""Handle chat messages and generate medical responses"""
	start_time = time.time()

	try:
		logger.info(f"Chat request from user {request.user_id} in session {request.session_id}")
		logger.info(f"Message: {request.message[:100]}...")  # Log first 100 chars of message

		# Get or create user profile
		user_profile = state.memory_system.get_user(request.user_id)
		if not user_profile:
			state.memory_system.create_user(request.user_id, request.user_role or "Anonymous")
			if request.user_specialty:
				user = state.memory_system.get_user(request.user_id)
				if user:
					user.set_preference("specialty", request.user_specialty)
				else:
					logger.warning("Failued to retrieve user")

		# Get or create session
		session = state.memory_system.get_session(request.session_id)
		if not session:
			session_id = state.memory_system.create_session(request.user_id, request.title or "New Chat")
			session = state.memory_system.get_session(session_id)
			logger.info(f"Created new session: {session_id}")

		# Get medical context from memory
		medical_context = state.history_manager.get_conversation_context(
			request.user_id,
			request.session_id,
			request.message
		)

		# Generate response using Gemini AI
		logger.info(f"Generating medical response using Gemini AI for user {request.user_id}")
		response = await generate_medical_response_with_gemini(
			request.message,
			request.user_role or "Medical Professional",
			request.user_specialty or "",
			medical_context,
			state.gemini_rotator
		)

		# Process and store the exchange
		try:
			await state.history_manager.process_medical_exchange(
				request.user_id,
				request.session_id,
				request.message,
				response,
				state.gemini_rotator,
				state.nvidia_rotator
			)
		except Exception as e:
			logger.warning(f"Failed to process medical exchange: {e}")
			# Continue without storing if there's an error

		# Calculate response time
		response_time = time.time() - start_time

		logger.info(f"Generated response in {response_time:.2f}s for user {request.user_id}")
		logger.info(f"Response length: {len(response)} characters")

		return ChatResponse(
			response=response,
			session_id=request.session_id,
			timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
			medical_context=medical_context if medical_context else None
		)

	except Exception as e:
		logger.error(f"Error in chat endpoint: {e}")
		logger.error(f"Request data: {request.dict()}")
		raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/summarize")
async def summarize_endpoint(
	req: SummarizeRequest,
	state: MedicalState = Depends(get_state)
):
	"""Summarize a text into a short 3-5 word title using NVIDIA if available."""
	try:
		title = await summarize_title_with_nvidia(req.text, state.nvidia_rotator, max_words=min(max(req.max_words or 5, 3), 7))
		return {"title": title}
	except Exception as e:
		logger.error(f"Error summarizing title: {e}")
		raise HTTPException(status_code=500, detail=str(e))
