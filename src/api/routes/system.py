import time

from fastapi import APIRouter, Depends

from src.core.state import MedicalState, get_state

router = APIRouter()

@router.get("/health")
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

@router.get("/api/info")
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
