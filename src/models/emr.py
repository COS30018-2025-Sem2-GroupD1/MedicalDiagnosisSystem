# emr/models/emr.py

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Medication(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None


class VitalSigns(BaseModel):
    blood_pressure: Optional[str] = None
    heart_rate: Optional[str] = None
    temperature: Optional[str] = None
    respiratory_rate: Optional[str] = None
    oxygen_saturation: Optional[str] = None


class LabResult(BaseModel):
    test_name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None


class ExtractedData(BaseModel):
    diagnosis: List[str] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)
    vital_signs: Optional[VitalSigns] = None
    lab_results: List[LabResult] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class EMRCreateRequest(BaseModel):
    patient_id: str
    doctor_id: str
    message_id: str
    session_id: str
    original_message: str
    extracted_data: ExtractedData
    confidence_score: float = Field(ge=0, le=1)


class EMRResponse(BaseModel):
    emr_id: str
    patient_id: str
    doctor_id: str
    message_id: str
    session_id: str
    original_message: str
    extracted_data: ExtractedData
    confidence_score: float
    created_at: datetime
    updated_at: datetime


class EMRSearchRequest(BaseModel):
    patient_id: str
    query: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class EMRUpdateRequest(BaseModel):
    extracted_data: Optional[ExtractedData] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
