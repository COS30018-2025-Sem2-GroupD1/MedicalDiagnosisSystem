from app.utils.settings import SETTINGS
from fastapi import APIRouter
from google import genai
from google.genai import types

chat_route = APIRouter(
	prefix="/chat",
	tags=["chat"]
)

@chat_route.post("/")
async def send(query):
	"""Send a message to the model."""

	model="gemma-3n-e2b-it"

	client = genai.Client(
		api_key=SETTINGS.google_api_key,
		http_options=types.HttpOptions(api_version="v1alpha")
	)

	response = client.models.generate_content(
		model=model, contents=query
	)

	return {"response": response}
