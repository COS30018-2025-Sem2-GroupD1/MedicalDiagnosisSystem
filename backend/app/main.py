import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.core.model_route import model_route
from app.core.chat_route import chat_route
from app.utils.settings import API_PATH, SETTINGS

# === SETUP ===

@asynccontextmanager
async def lifespan(app: FastAPI):
	# Startup code here
	yield
	# Shutdown code here

app = FastAPI(
	lifespan=lifespan,
	title="Medical Diagnosis System",
	version="0.1.0"
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

	# Redirect root path to the OpenAPI docs
	if request.url.path == "/":
		request.scope["path"] = "/docs"
		headers = dict(request.scope['headers'])
		headers[b'custom-header'] = b'my custom header'
		request.scope['headers'] = [(k, v) for k, v in headers.items()]

	response = await call_next(request)

	# Log request time into console
	# TODO proper logging
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

# === REFERENCE ===

@app.get("/retrieval/search")
async def search():
	return {"Result": "Idk what this is."}

# === API PATHS ===

@app.get(API_PATH)
async def base_api():
	"""Displays a message when the api endpoint is reached."""
	routes: list[str] = []
	for route in app.routes:
		# Check if the route is an APIRoute before accessing its path
		if isinstance(route, APIRoute) and route.path.startswith(API_PATH):
			routes.append(route.path)

	return {
		"Result": {
			"Message:": "Welcome to the api! See the docs by redirecting to /docs or /redocs",
			"Endpoints": routes
		}
	}

app.include_router(model_route)
app.include_router(chat_route)
