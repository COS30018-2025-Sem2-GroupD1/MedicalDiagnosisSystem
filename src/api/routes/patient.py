# api/routes/patient.py

from fastapi import APIRouter, HTTPException

from src.data.repositories.patient import (create_patient, get_patient_by_id,
                                           search_patients,
                                           update_patient_profile)
from src.data.repositories.session import list_patient_sessions
from src.models.user import PatientCreateRequest, PatientUpdateRequest
from src.utils.logger import logger

router = APIRouter(prefix="/patient", tags=["Patients"])

@router.post("")
async def create_patient_profile(req: PatientCreateRequest):
	try:
		logger().info(f"POST /patient name={req.name}")
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

@router.get("/search")
async def search_patients_route(q: str, limit: int = 20):
	try:
		logger().info(f"GET /patient/search q='{q}' limit={limit}")
		results = search_patients(q, limit=limit)
		logger().info(f"Search returned {len(results)} results")
		return {"results": results}
	except Exception as e:
		logger().error(f"Error searching patients: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/{patient_id}")
async def get_patient(patient_id: str):
	try:
		logger().info(f"GET /patient/{patient_id}")
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

@router.patch("/{patient_id}")
async def update_patient(patient_id: str, req: PatientUpdateRequest):
	try:
		payload = {k: v for k, v in req.model_dump().items() if v is not None}
		logger().info(f"PATCH /patient/{patient_id} fields={list(payload.keys())}")
		modified = update_patient_profile(patient_id, payload)
		if modified == 0:
			return {"message": "No changes"}
		return {"message": "Updated"}
	except Exception as e:
		logger().error(f"Error updating patient: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/{patient_id}/sessions")
async def list_sessions_for_patient(patient_id: str):
	"""List sessions for a patient from Mongo"""
	try:
		logger().info(f"GET /patient/{patient_id}/sessions")
		return {"sessions": list_patient_sessions(patient_id)}
	except Exception as e:
		logger().error(f"Error listing sessions: {e}")
		raise HTTPException(status_code=500, detail=str(e))
