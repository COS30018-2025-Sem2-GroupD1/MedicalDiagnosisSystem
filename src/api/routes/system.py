# api/routes/system.py

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
