import re

from src.services.gemini import gemini_chat
from src.services.nvidia import nvidia_chat
from src.utils.logger import get_logger
from src.utils.rotator import APIKeyRotator

logger = get_logger("SUMMARIZER", __name__)

def _sanitize_title(title: str, max_words: int) -> str:
	title = title.strip()
	title = re.sub(r"[\n\r]+", " ", title)
	title = re.sub(r"[\"'`]+", "", title)
	title = re.sub(r"\s+", " ", title)
	words = title.split()
	if not words:
		return ""
	return " ".join(words[:max_words])

def _heuristic_title(text: str, max_words: int) -> str:
	cleaned = (text or "New Chat").strip()
	cleaned = re.sub(r"[\n\r]+", " ", cleaned)
	cleaned = re.sub(r"[^\w\s]", "", cleaned)
	cleaned = re.sub(r"\s+", " ", cleaned)
	words = cleaned.split()
	if not words:
		return "New Chat"
	return " ".join(words[:max_words])

async def summarise_title_with_nvidia(
	text: str,
	rotator: APIKeyRotator | None,
	max_words: int = 5
) -> str:
	"""
	Generate a concise 3-5 word title for the conversation using NVIDIA API when available.
	Falls back to a heuristic if the API is unavailable.
	"""
	max_words = max(3, min(max_words or 5, 7))
	prompt = (
		"Summarise the user's first chat message into a very short title of 3-5 words. "
		"Only return the title text without quotes or punctuation. Message: " + (text or "New Chat")
	)

	if rotator and rotator.get_key():
		try:
			title = await nvidia_chat("You generate extremely concise titles.", prompt, rotator)
			title = _sanitize_title(title, max_words)
			if title:
				return title
		except Exception as e:
			logger.warning(f"NVIDIA summarise failed, using fallback: {e}")

	# Fallback heuristic
	return _heuristic_title(text, max_words)

async def summarise_qa_with_gemini(question: str, answer: str, rotator) -> str:
	"""
	Returns a single line block using Gemini API:
	q: <concise>\na: <concise>
	No extra commentary.
	"""
	prompt = f"""You are a medical summariser. Create a concise summary of this Q&A exchange.

Question: {question}

Answer: {answer}

Please provide exactly two lines in this format:
q: <brief question summary>
a: <brief answer summary>

Keep each summary under 160 characters for question and 220 characters for answer."""

	response = await gemini_chat(prompt, rotator)

	if response:
		# Parse the response to extract q: and a: lines
		lines = [ln.strip() for ln in response.splitlines() if ln.strip()]
		ql = next((l for l in lines if l.lower().startswith('q:')), None)
		al = next((l for l in lines if l.lower().startswith('a:')), None)

		if ql and al:
			return f"{ql}\n{al}"

	# Fallback if parsing fails
	logger.warning("Failed to get valid Gemini summarization, using fallback")
	return f"q: {question.strip()[:160]}\na: {answer.strip()[:220]}"

async def summarise_qa_with_nvidia(question: str, answer: str, rotator) -> str:
	"""
	Returns a single line block:
	q: <concise>\na: <concise>
	No extra commentary.
	"""
	sys = "You are a terse summariser. Output exactly two lines:\nq: <short question summary>\na: <short answer summary>\nNo extra text."
	user = f"Question:\n{question}\n\nAnswer:\n{answer}"
	out = await nvidia_chat(sys, user, rotator)
	# Basic guard if the model returns extra prose
	lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
	ql = next((l for l in lines if l.lower().startswith('q:')), None)
	al = next((l for l in lines if l.lower().startswith('a:')), None)
	if not ql or not al:
		# Fallback truncate
		ql = "q: " + (question.strip()[:160] + ("…" if len(question.strip()) > 160 else ""))
		al = "a: " + (answer.strip()[:220] + ("…" if len(answer.strip()) > 220 else ""))
	return f"{ql}\n{al}"
