# models/chat.py

from pydantic import BaseModel


class ChatRequest(BaseModel):
	user_id: str
	patient_id: str
	doctor_id: str
	session_id: str
	message: str
	user_role: str | None = "Medical Professional"
	user_specialty: str | None = ""
	title: str | None = "New Chat"

class ChatResponse(BaseModel):
	response: str
	session_id: str
	timestamp: str
	medical_context: str | None = None

class SessionRequest(BaseModel):
	user_id: str
	patient_id: str
	doctor_id: str
	title: str | None = "New Chat"

class SummariseRequest(BaseModel):
	text: str
	max_words: int | None = 5
