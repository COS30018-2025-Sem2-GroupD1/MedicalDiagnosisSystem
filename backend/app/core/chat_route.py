from fastapi import APIRouter

from ..utils.settings import API_PATH, SETTINGS

chat_route = APIRouter(
	prefix=API_PATH + "/chat",
	tags=["chat"]
)

@chat_route.post("/")
async def send(query):
	"""Send a message to the model."""
	return {
		"Result": {
			"Chat": "yes",
			"Query": query,
			"Result": "N/A"
		}
	}
