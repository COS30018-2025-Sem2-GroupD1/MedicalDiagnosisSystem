# main.py
# Access via: https://medai-cos30018-medicaldiagnosissystem.hf.space/

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from src.utils.logger import logger, setup_logging

# Needs to be called before any logs are sent
setup_logging()

# Load environment variables from .env file
try:
	from dotenv import load_dotenv
	load_dotenv()
	logger(tag="env").info("Environment variables loaded from .env file")
except ImportError:
	logger(tag="env").warning("python-dotenv not available, using system environment variables")
except Exception as e:
	logger(tag="env").warning(f"Error loading .env file: {e}")

# Import project modules after trying to load environment variables
from src.api.routes import account as account_route
from src.api.routes import audio as audio_route
from src.api.routes import chat as chat_route
from src.api.routes import patients as patients_route
from src.api.routes import session as session_route
from src.api.routes import static as static_route
from src.api.routes import system as system_route
from src.core.state import MedicalState, get_state
from src.data.repositories import account as account_repo
from src.data.repositories import medical as medical_repo
from src.data.repositories import message as message_repo
from src.data.repositories import patient as patient_repo
from src.data.repositories import session as session_repo


def startup_event(state: MedicalState):
	"""Initialize application on startup"""
	logger(tag="startup").info("Starting Medical AI Assistant...")

	# Check system resources
	try:
		import psutil
		ram = psutil.virtual_memory()
		cpu = psutil.cpu_percent(interval=1)
		logger(tag="startup").info(f"System Resources – RAM: {ram.percent}%, CPU: {cpu}%")

		if ram.percent > 85:
			logger(tag="startup").warning("High RAM usage detected!")
		if cpu > 90:
			logger(tag="startup").warning("High CPU usage detected!")
	except ImportError:
		logger(tag="startup").info("psutil not available, skipping system resource check")

	# Check API keys
	gemini_keys = len([k for k in state.gemini_rotator.keys if k])
	if gemini_keys == 0:
		logger(tag="startup").warning("No Gemini API keys found! Set GEMINI_API_1, GEMINI_API_2, etc. environment variables.")
	else:
		logger(tag="startup").info(f"{gemini_keys} Gemini API keys available")

	nvidia_keys = len([k for k in state.nvidia_rotator.keys if k])
	if nvidia_keys == 0:
		logger(tag="startup").warning("No NVIDIA API keys found! Set NVIDIA_API_1, NVIDIA_API_2, etc. environment variables.")
	else:
		logger(tag="startup").info(f"{nvidia_keys} NVIDIA API keys available")

	# Check embedding client
	if state.embedding_client.is_available():
		logger(tag="startup").info("Embedding model loaded successfully")
	else:
		logger(tag="startup").info("Using fallback embedding mode")

	logger(tag="startup").info("Medical AI Assistant startup complete")

	# TODO On first startup, create all repositories if they don't exist
	#account_repo.create()
	#patient_repo.create()
	#session_repo.create()
	#message_repo.create()
	#medical_repo.create()

def shutdown_event():
	"""Cleanup on shutdown"""
	logger(tag="shutdown").info("Shutting down Medical AI Assistant...")

@asynccontextmanager
async def lifespan(app: FastAPI):
	# Initialize state
	state = get_state()
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(chat_route.router)
app.include_router(session_route.router)
app.include_router(patients_route.router)
app.include_router(account_route.router)
app.include_router(system_route.router)
app.include_router(static_route.router)
app.include_router(audio_route.router)

@app.get("/api/info")
async def get_api_info():
	"""Get API information and capabilities, lists all paths available in the api."""
	return {
		"name": "Medical Diagnosis System",
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
		"endpoints": [route.path for route in app.routes if isinstance(route, APIRoute)]
	}
