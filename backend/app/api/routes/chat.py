from fastapi import APIRouter

chat_route = APIRouter(
	prefix="/chat",
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
