from utils.logger import get_logger
from utils.naming import summarize_title as nvidia_summarize_title
from utils.rotator import APIKeyRotator

logger = get_logger("SUMMARIZER", __name__)

async def summarize_title_with_nvidia(
	text: str, nvidia_rotator: APIKeyRotator,
	max_words: int = 5
) -> str:
	"""Use NVIDIA API via utils.naming with rotator. Includes internal fallback."""
	return await nvidia_summarize_title(text, nvidia_rotator, max_words)
