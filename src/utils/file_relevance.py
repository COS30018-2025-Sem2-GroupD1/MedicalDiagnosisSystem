# utils/file_relevance.py

import json
from dataclasses import dataclass
from typing import Any, Sequence

from src.services.nvidia import nvidia_chat
from src.utils.logger import get_logger
from src.utils.rotator import APIKeyRotator

logger = get_logger("FILE_RELEVANCE", __name__)

@dataclass
class FileSummary:
	filename: str
	summary: str = ""

def _safe_json(text: str) -> dict[str, Any]:
	"""Safely extract JSON from text that may contain extra content."""
	try:
		return json.loads(text)
	except json.JSONDecodeError:
		# Try to extract JSON object from text
		start = text.find("{")
		end = text.rfind("}")
		if start != -1 and end != -1 and end > start:
			try:
				return json.loads(text[start:end+1])
			except json.JSONDecodeError:
				return {}
		return {}

async def files_relevance(
	question: str,
	file_summaries: Sequence[FileSummary],
	rotator: APIKeyRotator
) -> dict[str, bool]:
	"""Determine which files are relevant to the given question using AI."""
	sys_prompt = "You classify file relevance. Return STRICT JSON only with shape {\"relevance\":[{\"filename\":\"...\",\"relevant\":true|false}]}."
	items = [{"filename": f.filename, "summary": f.summary} for f in file_summaries]
	user_prompt = f"Question: {question}\n\nFiles:\n{json.dumps(items, ensure_ascii=False)}\n\nReturn JSON only."

	try:
		response = await nvidia_chat(sys_prompt, user_prompt, rotator)
		data = _safe_json(response)
		relevance = {}

		for item in data.get("relevance", []):
			filename = item.get("filename")
			is_relevant = item.get("relevant")
			if isinstance(filename, str) and isinstance(is_relevant, bool):
				relevance[filename] = is_relevant

		if not relevance and file_summaries:
			# Fallback: consider all files relevant if parsing fails
			relevance = {f.filename: True for f in file_summaries}

		return relevance

	except Exception as e:
		logger.warning(f"Error determining file relevance: {e}")
		return {f.filename: True for f in file_summaries}
