# api/routes/user.py

from fastapi import APIRouter, Depends, HTTPException

from src.core.state import MedicalState, get_state
from src.utils.logger import logger
from src.models.user import UserProfileRequest, PatientCreateRequest, PatientUpdateRequest, DoctorCreateRequest
from src.data import create_account, create_doctor, get_doctor_by_name, search_doctors, get_all_doctors

router = APIRouter()

@router.post("/users")
async def create_user_profile(
	request: UserProfileRequest,
	state: MedicalState = Depends(get_state)
):
	"""Create or update user profile"""
	try:
		# Persist to in-memory profile (existing behavior)
		user = state.memory_system.create_user(request.user_id, request.name)
		user.set_preference("role", request.role)
		if request.specialty:
			user.set_preference("specialty", request.specialty)
		if request.medical_roles:
			user.set_preference("medical_roles", request.medical_roles)

		# Persist to MongoDB accounts collection
		account_doc = {
			"user_id": request.user_id,
			"name": request.name,
			"role": request.role,
			"medical_roles": request.medical_roles or [request.role] if request.role else [],
			"specialty": request.specialty or None,
		}
		account_id = create_account(account_doc)

		return {"message": "User profile created successfully", "user_id": request.user_id, "account_id": account_id}
	except Exception as e:
		logger().error(f"Error creating user profile: {e}")
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
				"medical_roles": user.preferences.get("medical_roles", []),
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
		logger().error(f"Error getting user profile: {e}")
		raise HTTPException(status_code=500, detail=str(e))

# -------------------- Patient APIs --------------------
from src.data import get_patient_by_id, create_patient, update_patient_profile, search_patients

@router.get("/patients/search")
async def search_patients_route(q: str, limit: int = 20):
	try:
		logger().info(f"GET /patients/search q='{q}' limit={limit}")
		results = search_patients(q, limit=limit)
		logger().info(f"Search returned {len(results)} results")
		return {"results": results}
	except Exception as e:
		logger().error(f"Error searching patients: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str):
	try:
		logger().info(f"GET /patients/{patient_id}")
		patient = get_patient_by_id(patient_id)
		if not patient:
			raise HTTPException(status_code=404, detail="Patient not found")
		patient["_id"] = str(patient.get("_id")) if patient.get("_id") else None
		return patient
	except HTTPException:
		raise
	except Exception as e:
		logger().error(f"Error getting patient: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.post("/patients")
async def create_patient_profile(req: PatientCreateRequest):
	try:
		logger().info(f"POST /patients name={req.name}")
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
		logger().info(f"Created patient {patient.get('name')} id={patient.get('patient_id')}")
		return patient
	except Exception as e:
		logger().error(f"Error creating patient: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.patch("/patients/{patient_id}")
async def update_patient(patient_id: str, req: PatientUpdateRequest):
	try:
		payload = {k: v for k, v in req.model_dump().items() if v is not None}
		logger().info(f"PATCH /patients/{patient_id} fields={list(payload.keys())}")
		modified = update_patient_profile(patient_id, payload)
		if modified == 0:
			return {"message": "No changes"}
		return {"message": "Updated"}
	except Exception as e:
		logger().error(f"Error updating patient: {e}")
		raise HTTPException(status_code=500, detail=str(e))

# -------------------- Doctor APIs --------------------
@router.post("/doctors")
async def create_doctor_profile(req: DoctorCreateRequest):
	try:
		logger().info(f"POST /doctors name={req.name}")
		doctor_id = create_doctor(
			name=req.name,
			role=req.role,
			specialty=req.specialty,
			medical_roles=req.medical_roles
		)
		logger().info(f"Created doctor {req.name} id={doctor_id}")
		return {"doctor_id": doctor_id, "name": req.name}
	except Exception as e:
		logger().error(f"Error creating doctor: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/doctors/{doctor_name}")
async def get_doctor(doctor_name: str):
	try:
		logger().info(f"GET /doctors/{doctor_name}")
		doctor = get_doctor_by_name(doctor_name)
		if not doctor:
			raise HTTPException(status_code=404, detail="Doctor not found")
		return doctor
	except HTTPException:
		raise
	except Exception as e:
		logger().error(f"Error getting doctor: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/doctors/search")
async def search_doctors_route(q: str, limit: int = 10):
	try:
		logger().info(f"GET /doctors/search q='{q}' limit={limit}")
		results = search_doctors(q, limit=limit)
		logger().info(f"Doctor search returned {len(results)} results")
		return {"results": results}
	except Exception as e:
		logger().error(f"Error searching doctors: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/doctors")
async def get_all_doctors_route(limit: int = 50):
	try:
		logger().info(f"GET /doctors limit={limit}")
		results = get_all_doctors(limit=limit)
		logger().info(f"Retrieved {len(results)} doctors")
		return {"results": results}
	except Exception as e:
		logger().error(f"Error getting all doctors: {e}")
		raise HTTPException(status_code=500, detail=str(e))
