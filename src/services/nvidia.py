# services/nvidia.py

import os

from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator, robust_post_json

NVIDIA_SMALL = os.getenv("NVIDIA_SMALL", "meta/llama-3.1-8b-instruct")

async def nvidia_chat(system_prompt: str, user_prompt: str, rotator: APIKeyRotator) -> str:
	"""Performs a minimal NVIDIA Chat API call."""
	url = "https://integrate.api.nvidia.com/v1/chat/completions"
	payload = {
		"model": NVIDIA_SMALL,
		"temperature": 0.0,
		"messages": [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		]
	}
	headers = {
		"Content-Type": "application/json",
		"Authorization": f"Bearer {rotator.get_key() or ''}"
	}
	try:
		data = await robust_post_json(url, headers, payload, rotator)
		return data["choices"][0]["message"]["content"]
	except Exception as e:
		logger().warning(f"NVIDIA chat error: {e}")
		return ""
