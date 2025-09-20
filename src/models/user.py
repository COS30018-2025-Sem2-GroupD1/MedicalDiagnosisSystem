# model/user.py
from pydantic import BaseModel
from typing import Optional, List

class UserProfileRequest(BaseModel):
	user_id: str
	name: str
	role: str
	specialty: Optional[str] = None
	medical_roles: Optional[List[str]] = None

class PatientCreateRequest(BaseModel):
	name: str
	age: int
	sex: str
	address: Optional[str] = None
	phone: Optional[str] = None
	email: Optional[str] = None
	medications: Optional[List[str]] = None
	past_assessment_summary: Optional[str] = None
	assigned_doctor_id: Optional[str] = None

class PatientUpdateRequest(BaseModel):
	name: Optional[str] = None
	age: Optional[int] = None
	sex: Optional[str] = None
	address: Optional[str] = None
	phone: Optional[str] = None
	email: Optional[str] = None
	medications: Optional[List[str]] = None
	past_assessment_summary: Optional[str] = None
	assigned_doctor_id: Optional[str] = None

class DoctorCreateRequest(BaseModel):
	name: str
	role: Optional[str] = None
	specialty: Optional[str] = None
	medical_roles: Optional[List[str]] = None
