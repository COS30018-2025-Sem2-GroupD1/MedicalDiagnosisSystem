# src/api/routes/patient.py

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.state import AppState, get_state
from src.models.patient import (Patient, PatientCreateRequest,
                                PatientUpdateRequest)
from src.models.session import Session
from src.utils.logger import logger

router = APIRouter(prefix="/patient", tags=["Patient"])


@router.get("", response_model=list[Patient])
async def search_or_get_all_patients(
	q: str | None = None,
	limit: int = 20,
	state: AppState = Depends(get_state)
):
	"""
	Searches for patients by name if a query 'q' is provided.
	Otherwise, this endpoint would list all patients (functionality not yet in repo).
	"""
	logger().info(f"GET /patient?q='{q}' limit={limit}")
	if not q:
		# In the future, you could add a get_all_patients method here.
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A search query 'q' is required.")

	patients = state.memory_manager.search_patients(q, limit=limit)
	logger().info(f"Search returned {len(patients)} results")
	return patients


@router.post("", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient_profile(
	req: PatientCreateRequest,
	state: AppState = Depends(get_state)
):
	"""Creates a new patient profile."""
	logger().info(f"POST /patient name={req.name}")
	patient_id = state.memory_manager.create_patient(**req.model_dump())

	if not patient_id:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient could not be created due to invalid data.")

	new_patient = state.memory_manager.get_patient_by_id(patient_id)
	if not new_patient:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not find newly created patient.")

	logger().info(f"Created patient {req.name} id={patient_id}")
	return new_patient


@router.get("/{patient_id}", response_model=Patient)
async def get_patient_by_id(
	patient_id: str,
	state: AppState = Depends(get_state)
):
	"""Retrieves a single patient by their unique ID."""
	logger().info(f"GET /patient/{patient_id}")
	patient = state.memory_manager.get_patient_by_id(patient_id)
	if not patient:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
	return patient


@router.patch("/{patient_id}", response_model=Patient)
async def update_patient(
	patient_id: str,
	req: PatientUpdateRequest,
	state: AppState = Depends(get_state)
):
	"""Updates a patient's profile with the provided fields."""
	# Get only the fields that the client actually sent
	updates = req.model_dump(exclude_unset=True)
	if not updates:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided.")

	logger().info(f"PATCH /patient/{patient_id} fields={list(updates.keys())}")
	modified_count = state.memory_manager.update_patient_profile(patient_id, updates)

	if modified_count == 0:
		# Check if the patient exists to differentiate between "not found" and "no changes made"
		if not state.memory_manager.get_patient_by_id(patient_id):
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

	# Return the full, updated patient object
	updated_patient = state.memory_manager.get_patient_by_id(patient_id)
	if not updated_patient:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not find patient after update.")

	return updated_patient


@router.get("/{patient_id}/session", response_model=list[Session])
async def list_sessions_for_patient(
	patient_id: str,
	state: AppState = Depends(get_state)
):
	"""Lists all chat sessions associated with a specific patient."""
	logger().info(f"GET /patient/{patient_id}/session")
	# First, verify the patient exists
	if not state.memory_manager.get_patient_by_id(patient_id):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

	sessions = state.memory_manager.list_patient_sessions(patient_id)
	return sessions
