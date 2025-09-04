import re
from typing import Optional

from .rotator import APIKeyRotator, robust_post_json
from .logger import get_logger

logger = get_logger("NAMING", __name__)


async def summarize_title(text: str, rotator: Optional[APIKeyRotator], max_words: int = 5) -> str:
    """
    Generate a concise 3-5 word title for the conversation using NVIDIA API when available.
    Falls back to a heuristic if the API is unavailable.
    """
    max_words = max(3, min(max_words or 5, 7))
    prompt = (
        "Summarize the user's first chat message into a very short title of 3-5 words. "
        "Only return the title text without quotes or punctuation. Message: " + (text or "New Chat")
    )

    if rotator and rotator.get_key():
        try:
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {rotator.get_key()}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "meta/llama-3.1-8b-instruct",
                "messages": [
                    {"role": "system", "content": "You generate extremely concise titles."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 16,
            }
            data = await robust_post_json(url, headers, payload, rotator, max_retries=5)
            # OpenAI-style response
            title = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            title = _sanitize_title(title, max_words)
            if title:
                return title
        except Exception as e:
            logger.warning(f"NVIDIA summarize failed, using fallback: {e}")

    # Fallback heuristic
    return _heuristic_title(text, max_words)


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


