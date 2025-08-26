import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.model_route import model_route
from app.utils.settings import API_PATH, SETTINGS

# === SETUP ===

@asynccontextmanager
async def lifespan(app: FastAPI):
	yield

app = FastAPI(
	lifespan=lifespan,
)

# Add CORS middleware, required for frontend connection to work
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # URL of React application
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
	"""Log HTTP requests into the console."""
	start_time = time.time()
	if request.url.path == "/":
		request.scope["path"] = "/docs"
		headers = dict(request.scope['headers'])
		headers[b'custom-header'] = b'my custom header'
		request.scope['headers'] = [(k, v) for k, v in headers.items()]
	response = await call_next(request)
	process_time = time.time() - start_time
	print(f"Request: {request.url} - Duration: {process_time} seconds")
	return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
	"""Handle HTTP exceptions."""
	return JSONResponse(
		status_code=exc.status_code,
		content={"Detail": exc.detail, "Error": "An error occurred"},
	)

# === WEB PAGES ===

@app.get("/chat")
async def chat(query):
	"""Chat window."""
	return {
		"Result": {
			"Chat": "yes",
			"Query": query,
			"Result": "N/A"
		}
	}

@app.get("/retrieval/search")
async def search():
	return

# === API PATHS ===

@app.get(API_PATH)
async def base_api():
	"""Displays a message when the api endpoint is reached."""
	return { "Result": "Welcome to the api" }

app.include_router(model_route)
