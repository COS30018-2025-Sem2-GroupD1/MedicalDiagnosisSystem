# models/chat.py

from pydantic import BaseModel


class ChatRequest(BaseModel):
	account_id: str
	patient_id: str
	session_id: str | None = None
	message: str

class ChatResponse(BaseModel):
	response: str
	session_id: str
	timestamp: str
	medical_context: str | None = None

class SessionRequest(BaseModel):
	account_id: str
	patient_id: str
	title: str | None = "New Chat"

class SummariseRequest(BaseModel):
	text: str
	max_words: int | None = 5
