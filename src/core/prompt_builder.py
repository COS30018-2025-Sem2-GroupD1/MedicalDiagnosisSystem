# core/prompts.py

def medical_response_prompt(user_role: str, user_specialty: str, medical_context: str, user_message: str) -> str:
	"""Generates the prompt for creating a medical response."""
	return f"""You are a knowledgeable medical AI assistant. Provide a comprehensive, accurate, and helpful response to this medical question.
**User Role:** {user_role}
**User Specialty:** {user_specialty if user_specialty else 'General'}
**Medical Context:** {medical_context if medical_context else 'No previous context'}
**Question:** {user_message}
**Instructions:**
1. Provide a detailed, medically accurate response.
2. Consider the user's role and specialty.
3. Include relevant medical information and guidance.
4. Mention when professional medical consultation is needed.
5. Use clear, professional language.
6. Include appropriate medical disclaimers.
**Response Format:**
- Start with a direct answer to the question.
- Provide relevant medical information.
- Include role-specific guidance.
- Add appropriate warnings and disclaimers.
- Keep the response comprehensive but focused.
Remember: This is for educational purposes only. Always emphasize consulting healthcare professionals for medical advice."""

def qa_summary_gemini_prompt(question: str, answer: str) -> str:
	"""Generates the prompt for summarizing a Q&A pair with Gemini."""

	return f"""You are a medical summariser. Create a concise summary of this Q&A exchange.

Question: {question}

Answer: {answer}

Please provide exactly two lines in this format:
q: <brief question summary>
a: <brief answer summary>

Keep each summary under 160 characters for question and 220 characters for answer."""

def title_summary_nvidia_prompt(text: str) -> str:
	"""Generates the prompt for summarizing a title with NVIDIA."""
	return (
		"Summarise the user's first chat message into a very short title of 3-5 words. "
		"Only return the title text without quotes or punctuation. Message: " + (text or "New Chat")
	)
