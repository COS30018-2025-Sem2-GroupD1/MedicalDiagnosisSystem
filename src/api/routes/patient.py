# api/routes/patient.py

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException

from src.data.repositories.patient import (create_patient, get_patient_by_id,
                                           search_patients,
                                           update_patient_profile)
from src.data.repositories.session import list_patient_sessions
from src.models.user import PatientCreateRequest, PatientUpdateRequest
from src.utils.logger import logger

router = APIRouter(prefix="/patient", tags=["Patient"])

@router.post("")
async def create_patient_profile(req: PatientCreateRequest):
	try:
		logger().info(f"POST /patient name={req.name}")
		patient_id = create_patient(
			req.name,
			req.age,
			req.sex,
			req.ethnicity,
			req.address,
			req.phone,
			req.email,
			req.medications,
			req.past_assessment_summary,
			req.assigned_doctor_id
		)
		#patient_id["_id"] = str(patient_id.get("_id")) if patient_id.get("_id") else None
		logger().info(f"Created patient {req.name} id={patient_id}")
		return { "patient_id": patient_id }
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
		try:
			# Validate ObjectId format
			if not ObjectId.is_valid(patient_id):
				raise HTTPException(status_code=400, detail="Invalid patient ID format")
		except InvalidId:
			raise HTTPException(status_code=400, detail="Invalid patient ID format")

		patient = get_patient_by_id(patient_id)
		if not patient:
			raise HTTPException(status_code=404, detail="Patient not found")

		# Convert ObjectId to string for JSON response
		patient["_id"] = str(patient["_id"])
		return patient
	except HTTPException:
		raise
	except Exception as e:
		logger().error(f"Error getting patient: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{patient_id}")
async def update_patient(patient_id: str, req: PatientUpdateRequest):
	try:
		# Validate ObjectId format
		if not ObjectId.is_valid(patient_id):
			raise HTTPException(status_code=400, detail="Invalid patient ID format")

		payload = {k: v for k, v in req.model_dump().items() if v is not None}
		logger().info(f"PATCH /patient/{patient_id} fields={list(payload.keys())}")
		modified = update_patient_profile(patient_id, payload)
		if modified == 0:
			return {"message": "No changes"}
		return {"message": "Updated"}
	except HTTPException:
		raise
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
