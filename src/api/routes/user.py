# api/routes/user.py

from fastapi import APIRouter, Depends, HTTPException

from src.core.state import MedicalState, get_state
from src.models.user import UserProfileRequest
from src.utils.logger import get_logger

logger = get_logger("USER_ROUTES", __name__)
router = APIRouter()

@router.post("/users")
async def create_user_profile(
	request: UserProfileRequest,
	state: MedicalState = Depends(get_state)
):
	"""Create or update user profile"""
	try:
		user = state.memory_system.create_user(request.user_id, request.name)
		user.set_preference("role", request.role)
		if request.specialty:
			user.set_preference("specialty", request.specialty)

		return {"message": "User profile created successfully", "user_id": request.user_id}
	except Exception as e:
		logger.error(f"Error creating user profile: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}")
async def get_user_profile(
	user_id: str,
	state: MedicalState = Depends(get_state)
):
	"""Get user profile and sessions"""
	try:
		user = state.memory_system.get_user(user_id)
		if not user:
			raise HTTPException(status_code=404, detail="User not found")

		sessions = state.memory_system.get_user_sessions(user_id)

		return {
			"user": {
				"id": user.user_id,
				"name": user.name,
				"role": user.preferences.get("role", "Unknown"),
				"specialty": user.preferences.get("specialty", ""),
				"created_at": user.created_at,
				"last_seen": user.last_seen
			},
			"sessions": [
				{
					"id": session.session_id,
					"title": session.title,
					"created_at": session.created_at,
					"last_activity": session.last_activity,
					"message_count": len(session.messages)
				}
				for session in sessions if session is not None
			]
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error getting user profile: {e}")
		raise HTTPException(status_code=500, detail=str(e))

# -------------------- Patient APIs --------------------
from pydantic import BaseModel
from src.data.mongodb import get_patient_by_id, create_patient, update_patient_profile, search_patients

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

@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str):
	try:
		logger.info(f"GET /patients/{patient_id}")
		patient = get_patient_by_id(patient_id)
		if not patient:
			raise HTTPException(status_code=404, detail="Patient not found")
		patient["_id"] = str(patient.get("_id")) if patient.get("_id") else None
		return patient
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error getting patient: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.post("/patients")
async def create_patient_profile(req: PatientCreateRequest):
	try:
		logger.info(f"POST /patients name={req.name}")
		patient = create_patient(
			name=req.name,
			age=req.age,
			sex=req.sex,
			address=req.address,
			phone=req.phone,
			email=req.email,
			medications=req.medications,
			past_assessment_summary=req.past_assessment_summary,
			assigned_doctor_id=req.assigned_doctor_id
		)
		patient["_id"] = str(patient.get("_id")) if patient.get("_id") else None
		logger.info(f"Created patient {patient.get('name')} id={patient.get('patient_id')}")
		return patient
	except Exception as e:
		logger.error(f"Error creating patient: {e}")
		raise HTTPException(status_code=500, detail=str(e))

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

@router.patch("/patients/{patient_id}")
async def update_patient(patient_id: str, req: PatientUpdateRequest):
	try:
		payload = {k: v for k, v in req.model_dump().items() if v is not None}
		logger.info(f"PATCH /patients/{patient_id} fields={list(payload.keys())}")
		modified = update_patient_profile(patient_id, payload)
		if modified == 0:
			return {"message": "No changes"}
		return {"message": "Updated"}
	except Exception as e:
		logger.error(f"Error updating patient: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/patients/search")
async def search_patients_route(q: str, limit: int = 10):
	try:
		logger.info(f"GET /patients/search q='{q}' limit={limit}")
		return {"results": search_patients(q, limit=limit)}
	except Exception as e:
		logger.error(f"Error searching patients: {e}")
		raise HTTPException(status_code=500, detail=str(e))
