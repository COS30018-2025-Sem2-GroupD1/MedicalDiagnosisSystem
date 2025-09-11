# services/summariser.py

from src.core import prompt_builder
from src.services.gemini import gemini_chat
from src.services.nvidia import nvidia_chat
from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator
from src.utils.text_processing import heuristic_title, sanitize_title


async def summarise_title_with_nvidia(
	text: str,
	rotator: APIKeyRotator | None,
	max_words: int = 5
) -> str:
	"""Generates a concise title for a conversation using the NVIDIA API."""
	max_words = max(3, min(max_words or 5, 7))
	prompt = prompt_builder.title_summary_nvidia_prompt(text)

	if rotator and rotator.get_key():
		try:
			title = await nvidia_chat("You generate extremely concise titles.", prompt, rotator)
			sanitized = sanitize_title(title, max_words)
			if sanitized:
				return sanitized
		except Exception as e:
			logger().warning(f"NVIDIA title summary failed: {e}")

	return heuristic_title(text, max_words)

async def summarise_qa_with_gemini(
	question: str,
	answer: str,
	rotator: APIKeyRotator
) -> str:
	"""Summarizes a Q&A pair into a 'q: ... a: ...' format using the Gemini API."""
	prompt = prompt_builder.qa_summary_gemini_prompt(question, answer)
	response = await gemini_chat(prompt, rotator)

	if response:
		# Parse the response to extract q: and a: lines
		lines = [ln.strip() for ln in response.splitlines() if ln.strip()]
		q_line = next((l for l in lines if l.lower().startswith('q:')), None)
		a_line = next((l for l in lines if l.lower().startswith('a:')), None)
		if q_line and a_line:
			return f"{q_line}\n{a_line}"

	logger().warning("Gemini summarization failed, using fallback.")
	return f"q: {question.strip()[:160]}\na: {answer.strip()[:220]}"

async def summarise_qa_with_nvidia(
	question: str,
	answer: str,
	rotator: APIKeyRotator
) -> str:
	"""Summarizes a Q&A pair into a 'q: ... a: ...' format using the NVIDIA API."""
	sys_prompt = "You are a terse summariser. Output exactly two lines:\nq: <short question summary>\na: <short answer summary>\nNo extra text."
	user_prompt = f"Question:\n{question}\n\nAnswer:\n{answer}"
	out = await nvidia_chat(sys_prompt, user_prompt, rotator)
	# Basic guard if the model returns extra prose
	lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
	q_line = next((l for l in lines if l.lower().startswith('q:')), None)
	a_line = next((l for l in lines if l.lower().startswith('a:')), None)

	if q_line and a_line:
		return f"{q_line}\n{a_line}"

	q_fallback = "q: " + (question.strip()[:160] + "…")
	a_fallback = "a: " + (answer.strip()[:220] + "…")
	return f"{q_fallback}\n{a_fallback}"
