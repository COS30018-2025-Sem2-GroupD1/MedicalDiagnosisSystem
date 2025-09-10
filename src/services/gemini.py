# services/gemini.py

from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator


async def gemini_chat(
	prompt: str,
	rotator: APIKeyRotator,
	model: str = "gemini-2.5-flash-lite"
) -> str:
	"""
	Generates a response using the Gemini API with key rotation.
	Falls back to empty string on failure.
	"""
	try:
		from google import genai
		api_key = rotator.get_key()
		if not api_key:
			logger().warning("No Gemini API key available.")
			return ""

		client = genai.Client(api_key=api_key)
		response = client.models.generate_content(model=model, contents=prompt)
		return response.text or ""

	except Exception as e:
		logger().warning(f"Gemini chat failed: {e}")
		return ""
