import time
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
#from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.api_base import api_route

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

## Add CORS middleware, required for frontend connection to work
#app.add_middleware(
#	CORSMiddleware,
#	allow_origins=["*"],  # URL frontend application
#	allow_credentials=True,
#	allow_methods=["*"],
#	allow_headers=["*"],
#)

@app.middleware("http")
async def log_requests(
	request: Request,
	call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
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
	response.headers["X-Process-Time"] = str(process_time)
	print(f"Request: {request.url} - Duration: {process_time} seconds")
	return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
	"""Handle HTTP exceptions."""
	return JSONResponse(
		status_code=exc.status_code,
		content={"Detail": exc.detail, "Error": "An error occurred"},
	)

# === API PATHS ===

app.include_router(api_route)
