# app.py
# Access via: https://medai-cos30018-medicaldiagnosissystem.hf.space/

import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from core.state import MedicalState, get_state
from models.chat import (ChatRequest, ChatResponse, SessionRequest,
                         SummarizeRequest)
from models.user import UserProfileRequest
from services.medical_response import generate_medical_response_with_gemini
from services.summariser import summarize_title_with_nvidia

# Load environment variables from .env file
try:
	from dotenv import load_dotenv
	load_dotenv()
	print("✅ Environment variables loaded from .env file")
except ImportError:
	print("⚠️ python-dotenv not available, using system environment variables")
except Exception as e:
	print(f"⚠️ Error loading .env file: {e}")

from utils.logger import get_logger

# Configure logging
logger = get_logger("MEDICAL_APP", __name__)

# Startup event
def startup_event(state: MedicalState):
	"""Initialize application on startup"""
	logger.info("🚀 Starting Medical AI Assistant...")

	# Check system resources
	try:
		import psutil
		memory = psutil.virtual_memory()
		cpu = psutil.cpu_percent(interval=1)
		logger.info(f"System Resources - RAM: {memory.percent}%, CPU: {cpu}%")

		if memory.percent > 85:
			logger.warning("⚠️ High RAM usage detected!")
		if cpu > 90:
			logger.warning("⚠️ High CPU usage detected!")
	except ImportError:
		logger.info("psutil not available, skipping system resource check")

	# Check API keys
	gemini_keys = len([k for k in state.gemini_rotator.keys if k])
	if gemini_keys == 0:
		logger.warning("⚠️ No Gemini API keys found! Set GEMINI_API_1, GEMINI_API_2, etc. environment variables.")
	else:
		logger.info(f"✅ {gemini_keys} Gemini API keys available")

	nvidia_keys = len([k for k in state.nvidia_rotator.keys if k])
	if nvidia_keys == 0:
		logger.warning("⚠️ No NVIDIA API keys found! Set NVIDIA_API_1, NVIDIA_API_2, etc. environment variables.")
	else:
		logger.info(f"✅ {nvidia_keys} NVIDIA API keys available")

	# Check embedding client
	if state.embedding_client.is_available():
		logger.info("✅ Embedding model loaded successfully")
	else:
		logger.info("⚠️ Using fallback embedding mode")

	logger.info("✅ Medical AI Assistant startup complete")

# Shutdown event
def shutdown_event():
	"""Cleanup on shutdown"""
	logger.info("🛑 Shutting down Medical AI Assistant...")

@asynccontextmanager
async def lifespan(app: FastAPI):
	# Initialize state
	state = MedicalState.get_instance()
	state.initialize()

	# Startup code here
	startup_event(state)
	yield
	# Shutdown code here
	shutdown_event()

# Initialize FastAPI app
app = FastAPI(
	lifespan=lifespan,
	title="Medical AI Assistant",
	description="AI-powered medical chatbot with memory and context awareness",
	version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def get_medical_chatbot():
	"""Serve the medical chatbot UI"""
	try:
		with open("static/index.html", "r", encoding="utf-8") as f:
			html_content = f.read()
		return HTMLResponse(content=html_content)
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Medical chatbot UI not found")

@app.post("/chat", response_model=ChatResponse)
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
					state.memory_system.get_user(request.user_id).set_preference("specialty", request.user_specialty)

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
		logger.info(f"Gemini response generated successfully, length: {len(response)} characters")

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

@app.post("/users")
async def create_user_profile(
	request: UserProfileRequest,
	state: MedicalState = Depends(get_state)
):
	"""Create or update user profile"""
	try:
		user = state.memory_system.create_user(request.user_id, request.name)
		user.set_preference("role", request.role)
		if request.specialty:
			user.set_preference("specialty", request.specialty)

		return {"message": "User profile created successfully", "user_id": request.user_id}
	except Exception as e:
		logger.error(f"Error creating user profile: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}")
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
				for session in sessions
			]
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error getting user profile: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions")
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

@app.get("/sessions/{session_id}")
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

@app.delete("/sessions/{session_id}")
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

@app.get("/health")
async def health_check(state: MedicalState = Depends(get_state)):
	"""Health check endpoint"""
	return {
		"status": "healthy",
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
		"components": {
			"memory_system": "operational",
			"embedding_client": "operational" if state.embedding_client.is_available() else "fallback_mode",
			"api_rotator": "operational",
			"gemini_keys_available": len([k for k in state.gemini_rotator.keys if k]) > 0,
			"nvidia_keys_available": len([k for k in state.nvidia_rotator.keys if k]) > 0
		}
	}

@app.get("/api/info")
async def get_api_info():
	"""Get API information and capabilities"""
	return {
		"name": "Medical AI Assistant",
		"version": "1.0.0",
		"description": "AI-powered medical chatbot with memory and context awareness",
		"features": [
			"Multi-user support with profiles",
			"Chat session management",
			"Medical context memory",
			"API key rotation",
			"Embedding-based similarity search",
			"Medical knowledge base integration"
		],
		"endpoints": [
			"POST /chat - Send chat message",
			"POST /users - Create user profile",
			"GET /users/{user_id} - Get user profile and sessions",
			"POST /sessions - Create chat session",
			"GET /sessions/{session_id} - Get session details",
			"DELETE /sessions/{session_id} - Delete session",
			"GET /health - Health check",
			"GET /api/info - API information"
		]
	}

@app.post("/summarize")
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
	logger.info("Starting Medical AI Assistant server...")
	try:
		uvicorn.run(
			app,
			host="0.0.0.0",
			port=8000,
			log_level="info",
			reload=True
		)
	except Exception as e:
		logger.error(f"❌ Server startup failed: {e}")
		exit(1)
