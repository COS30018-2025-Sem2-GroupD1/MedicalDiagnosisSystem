# utils/text_processing.py

import re


def sanitize_title(title: str, max_words: int) -> str:
	"""Cleans and truncates a string to be used as a title."""
	title = re.sub(r"[\n\r]+", " ", title.strip())
	title = re.sub(r"[\"'`]+", "", title)
	title = re.sub(r"\s+", " ", title)
	words = title.split()
	return " ".join(words[:max_words])

def heuristic_title(text: str, max_words: int) -> str:
	"""Generates a simple title from text as a fallback."""
	cleaned = (text or "New Chat").strip()
	cleaned = re.sub(r"[\n\r]+", " ", cleaned)
	cleaned = re.sub(r"[^\w\s]", "", cleaned)
	cleaned = re.sub(r"\s+", " ", cleaned)
	words = cleaned.split()
	return " ".join(words[:max_words]) if words else "New Chat"
