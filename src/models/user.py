# model/user.py

from pydantic import BaseModel

class UserProfileRequest(BaseModel):
	user_id: str
	name: str
	role: str
	specialty: str | None = ""
