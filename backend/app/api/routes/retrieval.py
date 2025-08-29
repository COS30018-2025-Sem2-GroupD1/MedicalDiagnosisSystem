from fastapi import APIRouter

retrieval_route = APIRouter(
	prefix="/retrieval",
	tags=["retrieval"]
)

@retrieval_route.get("/search")
async def search():
	"""Idk what this is supposed to be for."""
	return {"result": "Not implemented"}
