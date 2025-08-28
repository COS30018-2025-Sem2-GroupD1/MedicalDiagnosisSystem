from fastapi import APIRouter

from ..utils.settings import API_PATH, SETTINGS

retrieval_route = APIRouter(
	prefix=API_PATH + "/retrieval",
	tags=["retrieval"]
)

@retrieval_route.get("/search")
async def search():
	"""Idk what this is supposed to be for."""
	return {"Result": "Idk what this is."}
