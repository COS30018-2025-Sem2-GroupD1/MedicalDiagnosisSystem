# utils/file_relevance.py

import json
from dataclasses import dataclass
from typing import Any

from src.services.nvidia import nvidia_chat
from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator


@dataclass
class FileSummary:
	filename: str
	summary: str = ""

def _safe_json(text: str) -> dict[str, Any]:
	"""Safely extracts a JSON object from a string that may contain other text."""
	try:
		return json.loads(text)
	except json.JSONDecodeError:
		# Try to extract JSON object from text
		start = text.find("{")
		end = text.rfind("}")
		if -1 < start < end:
			try:
				return json.loads(text[start:end + 1])
			except json.JSONDecodeError:
				pass

	return {}

async def files_relevance(
	question: str,
	file_summaries: list[FileSummary],
	rotator: APIKeyRotator
) -> dict[str, bool]:
	"""Determines which files are relevant to a given question using an AI model."""
	sys_prompt = "You classify file relevance. Return STRICT JSON of shape {\"relevance\":[{\"filename\":\"...\",\"relevant\":true|false}]}."
	items = [{"filename": f.filename, "summary": f.summary} for f in file_summaries]
	user_prompt = f"Question: {question}\n\nFiles:\n{json.dumps(items, ensure_ascii=False)}\n\nReturn JSON only."

	try:
		response = await nvidia_chat(sys_prompt, user_prompt, rotator)
		data = _safe_json(response)
		relevance = {
			item["filename"]: item["relevant"]
			for item in data.get("relevance", [])
			if isinstance(item.get("filename"), str) and isinstance(item.get("relevant"), bool)
		}

		# Fallback if parsing fails but files were provided
		if not relevance and file_summaries:
			return {f.filename: True for f in file_summaries}

		return relevance

	except Exception as e:
		logger().warning(f"Error determining file relevance: {e}")
		return {f.filename: True for f in file_summaries}
