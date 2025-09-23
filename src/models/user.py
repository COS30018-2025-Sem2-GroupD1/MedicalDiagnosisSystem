# model/user.py

from pydantic import BaseModel


class UserProfileRequest(BaseModel):
	user_id: str
	name: str
	role: str
	specialty: str | None = None
	medical_roles: list[str] | None = None

class PatientCreateRequest(BaseModel):
	name: str
	age: int
	sex: str
	address: str | None = None
	phone: str | None = None
	email: str | None = None
	medications: list[str] | None = None
	past_assessment_summary: str | None = None
	assigned_doctor_id: str | None = None

class PatientUpdateRequest(BaseModel):
	name: str | None = None
	age: int | None = None
	sex: str | None = None
	address: str | None = None
	phone: str | None = None
	email: str | None = None
	medications: list[str] | None = None
	past_assessment_summary: str | None = None
	assigned_doctor_id: str | None = None

class DoctorCreateRequest(BaseModel):
	name: str
	role: str | None = None
	specialty: str | None = None
	medical_roles: list[str] | None = None
