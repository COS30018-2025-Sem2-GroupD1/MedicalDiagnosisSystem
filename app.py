# app.py
# Access via: https://medai-cos30018-medicaldiagnosissystem.hf.space/

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env file
try:
	from dotenv import load_dotenv
	load_dotenv()
	print("✅ Environment variables loaded from .env file")
except ImportError:
	print("⚠️ python-dotenv not available, using system environment variables")
except Exception as e:
	print(f"⚠️ Error loading .env file: {e}")

from api.routes import chat, session, system, user
from core.state import MedicalState
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

# Include routers
app.include_router(chat.router)
app.include_router(user.router)
app.include_router(session.router)
app.include_router(system.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

#if __name__ == "__main__":
#	logger.info("Starting Medical AI Assistant server...")
#	try:
#		uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", reload=True)
#	except Exception as e:
#		logger.error(f"❌ Server startup failed: {e}")
#		exit(1)
