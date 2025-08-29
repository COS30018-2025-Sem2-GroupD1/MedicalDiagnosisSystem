from fastapi import APIRouter

model_route = APIRouter(
	prefix="/model",
	tags=["model"]
)

@model_route.get("/student")
async def student():
	"""Returns the student model (I assume)."""
	return {
		"result" : "Not implemented."
	}
