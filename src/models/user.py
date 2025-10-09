# src/model/user.py

from pydantic import BaseModel


class PatientCreateRequest(BaseModel):
	name: str
	age: int
	sex: str
	ethnicity: str
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
	ethnicity: str | None = None
	address: str | None = None
	phone: str | None = None
	email: str | None = None
	medications: list[str] | None = None
	past_assessment_summary: str | None = None
	assigned_doctor_id: str | None = None
