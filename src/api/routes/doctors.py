# api/routes/doctors.py

from fastapi import APIRouter, HTTPException

from src.data.repositories.account import (create_account, get_all_accounts,
                                           get_account_by_name, search_accounts)
from src.models.user import DoctorCreateRequest
from src.utils.logger import logger

router = APIRouter(prefix="/doctors", tags=["Doctors"])

@router.get("")
async def get_all_doctors_route(limit: int = 50):
	try:
		logger().info(f"GET /doctors limit={limit}")
		results = get_all_accounts(limit=limit)
		logger().info(f"Retrieved {len(results)} doctors")
		return {"results": results}
	except Exception as e:
		logger().error(f"Error getting all doctors: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_doctor_profile(req: DoctorCreateRequest):
	try:
		logger().info(f"POST /doctors name={req.name}")
		doctor_id = create_account(
			name=req.name,
			role=req.role,
			specialty=req.specialty
		)
		logger().info(f"Created doctor {req.name} id={doctor_id}")
		return {"doctor_id": doctor_id, "name": req.name}
	except Exception as e:
		logger().error(f"Error creating doctor: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/{doctor_name}")
async def get_doctor(doctor_name: str):
	try:
		logger().info(f"GET /doctors/{doctor_name}")
		doctor = get_account_by_name(doctor_name)
		if not doctor:
			raise HTTPException(status_code=404, detail="Doctor not found")
		return doctor
	except HTTPException:
		raise
	except Exception as e:
		logger().error(f"Error getting doctor: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_doctors_route(q: str, limit: int = 10):
	try:
		logger().info(f"GET /doctors/search q='{q}' limit={limit}")
		results = search_accounts(q, limit=limit)
		logger().info(f"Doctor search returned {len(results)} results")
		return {"results": results}
	except Exception as e:
		logger().error(f"Error searching doctors: {e}")
		raise HTTPException(status_code=500, detail=str(e))
