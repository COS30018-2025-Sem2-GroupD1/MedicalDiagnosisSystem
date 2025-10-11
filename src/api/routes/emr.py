# src/api/routes/emr.py

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from src.models.emr import EMRResponse, EMRSearchRequest, EMRUpdateRequest, ExtractedData
from src.services.service import EMRService
from src.services.extractor import EMRExtractor
from src.data.emr_update import EMRUpdateService
from src.core.state import AppState, get_state
from src.utils.logger import logger

router = APIRouter(prefix="/emr", tags=["EMR"])


@router.get("/check/{message_id}", response_model=dict)
async def check_emr_exists(message_id: str):
    """Check if EMR extraction has already been done for a message."""
    try:
        from src.data.repositories.emr import check_emr_exists
        exists = check_emr_exists(message_id)
        return {
            "message_id": message_id,
            "emr_exists": exists
        }
    except Exception as e:
        logger().error(f"Error checking EMR existence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=dict)
async def emr_health_check():
    """Health check endpoint for EMR service."""
    try:
        from src.data.connection import get_collection
        collection = get_collection("emr")
        # Try to count documents to verify collection exists and is accessible
        count = collection.count_documents({})
        return {
            "status": "healthy",
            "collection": "emr",
            "document_count": count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger().error(f"EMR health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def get_emr_service(state: AppState = Depends(get_state)) -> EMRService:
    """Get EMR service instance."""
    return EMRService(state.gemini_rotator, state.embedding_client)


@router.post("/extract", response_model=dict)
async def extract_emr_from_message(
    patient_id: str,
    doctor_id: str,
    message_id: str,
    session_id: str,
    message: str,
    emr_service: EMRService = Depends(get_emr_service)
):
    """Extract and store EMR data from a chat message."""
    try:
        # Input validation
        if not patient_id or not patient_id.strip():
            raise HTTPException(status_code=400, detail="Patient ID is required")
        if not doctor_id or not doctor_id.strip():
            raise HTTPException(status_code=400, detail="Doctor ID is required")
        if not message_id or not message_id.strip():
            raise HTTPException(status_code=400, detail="Message ID is required")
        if not session_id or not session_id.strip():
            raise HTTPException(status_code=400, detail="Session ID is required")
        if not message or not message.strip():
            raise HTTPException(status_code=400, detail="Message content is required")

        logger().info(f"EMR extraction requested for patient {patient_id}, message {message_id}")

        # Get patient context if available
        patient_context = None
        try:
            from src.data.repositories.patient import get_patient_by_id
            patient = get_patient_by_id(patient_id)
            if patient:
                patient_context = {
                    "name": patient.name,
                    "age": patient.age,
                    "sex": patient.sex,
                    "medications": patient.medications or [],
                    "past_assessment_summary": patient.past_assessment_summary
                }
        except Exception as e:
            logger().warning(f"Could not fetch patient context: {e}")

        # Extract and store EMR data
        emr_id = await emr_service.extract_and_store_emr(
            patient_id=patient_id,
            doctor_id=doctor_id,
            message_id=message_id,
            session_id=session_id,
            message=message,
            patient_context=patient_context
        )

        return {
            "emr_id": emr_id,
            "message": "EMR data extracted and stored successfully"
        }

    except Exception as e:
        logger().error(f"Error in EMR extraction endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}", response_model=List[EMRResponse])
async def get_patient_emr(
    patient_id: str,
    limit: int = 20,
    offset: int = 0,
    emr_service: EMRService = Depends(get_emr_service)
):
    """Get EMR entries for a specific patient."""
    try:
        logger().info(f"Getting EMR entries for patient {patient_id}")

        entries = await emr_service.get_patient_emr(patient_id, limit, offset)
        return entries

    except Exception as e:
        logger().error(f"Error getting patient EMR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/{patient_id}", response_model=List[EMRResponse])
async def search_patient_emr(
    patient_id: str,
    query: str,
    limit: int = 10,
    emr_service: EMRService = Depends(get_emr_service)
):
    """Search EMR entries for a patient using semantic similarity."""
    try:
        logger().info(f"Searching EMR for patient {patient_id} with query: {query}")

        entries = await emr_service.search_emr_semantic(patient_id, query, limit)
        return entries

    except Exception as e:
        logger().error(f"Error searching patient EMR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{emr_id}", response_model=EMRResponse)
async def get_emr_by_id(
    emr_id: str,
    emr_service: EMRService = Depends(get_emr_service)
):
    """Get a specific EMR entry by ID."""
    try:
        logger().info(f"Getting EMR entry {emr_id}")

        entry = await emr_service.get_emr_by_id(emr_id)
        if not entry:
            raise HTTPException(status_code=404, detail="EMR entry not found")

        return entry

    except HTTPException:
        raise
    except Exception as e:
        logger().error(f"Error getting EMR by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{emr_id}", response_model=dict)
async def update_emr(
    emr_id: str,
    request: EMRUpdateRequest,
    emr_service: EMRService = Depends(get_emr_service)
):
    """Update an EMR entry."""
    try:
        logger().info(f"Updating EMR entry {emr_id}")

        updates = {}
        if request.extracted_data:
            updates["extracted_data"] = request.extracted_data.model_dump()
        if request.confidence_score is not None:
            updates["confidence_score"] = request.confidence_score

        success = await emr_service.update_emr(emr_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="EMR entry not found")

        return {"message": "EMR entry updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger().error(f"Error updating EMR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{emr_id}", response_model=dict)
async def delete_emr(
    emr_id: str,
    emr_service: EMRService = Depends(get_emr_service)
):
    """Delete an EMR entry."""
    try:
        logger().info(f"Deleting EMR entry {emr_id}")

        success = await emr_service.delete_emr(emr_id)
        if not success:
            raise HTTPException(status_code=404, detail="EMR entry not found")

        return {"message": "EMR entry deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger().error(f"Error deleting EMR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{patient_id}", response_model=dict)
async def get_emr_statistics(
    patient_id: str,
    emr_service: EMRService = Depends(get_emr_service)
):
    """Get EMR statistics for a patient."""
    try:
        logger().info(f"Getting EMR statistics for patient {patient_id}")

        stats = await emr_service.get_emr_statistics(patient_id)
        return stats

    except Exception as e:
        logger().error(f"Error getting EMR statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-extract", response_model=dict)
async def bulk_extract_emr(
    extractions: List[dict],
    emr_service: EMRService = Depends(get_emr_service)
):
    """Extract EMR data from multiple messages in bulk."""
    try:
        if not extractions or len(extractions) == 0:
            raise HTTPException(status_code=400, detail="No extractions provided")

        if len(extractions) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 extractions allowed per request")

        logger().info(f"Bulk EMR extraction requested for {len(extractions)} messages")

        results = []
        errors = []

        for i, extraction in enumerate(extractions):
            try:
                # Validate required fields
                required_fields = ['patient_id', 'doctor_id', 'message_id', 'session_id', 'message']
                for field in required_fields:
                    if field not in extraction or not extraction[field]:
                        raise ValueError(f"Missing or empty {field}")

                # Get patient context
                patient_context = None
                try:
                    from src.data.repositories.patient import get_patient_by_id
                    patient = get_patient_by_id(extraction['patient_id'])
                    if patient:
                        patient_context = {
                            "name": patient.name,
                            "age": patient.age,
                            "sex": patient.sex,
                            "medications": patient.medications or [],
                            "past_assessment_summary": patient.past_assessment_summary
                        }
                except Exception as e:
                    logger().warning(f"Could not fetch patient context for extraction {i}: {e}")

                # Extract and store EMR data
                emr_id = await emr_service.extract_and_store_emr(
                    patient_id=extraction['patient_id'],
                    doctor_id=extraction['doctor_id'],
                    message_id=extraction['message_id'],
                    session_id=extraction['session_id'],
                    message=extraction['message'],
                    patient_context=patient_context
                )

                results.append({
                    "index": i,
                    "message_id": extraction['message_id'],
                    "emr_id": emr_id,
                    "status": "success"
                })

            except Exception as e:
                logger().error(f"Error in bulk extraction {i}: {e}")
                errors.append({
                    "index": i,
                    "message_id": extraction.get('message_id', 'unknown'),
                    "error": str(e),
                    "status": "failed"
                })

        return {
            "message": f"Bulk extraction completed. {len(results)} successful, {len(errors)} failed.",
            "results": results,
            "errors": errors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger().error(f"Error in bulk EMR extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_emr_extractor(state: AppState = Depends(get_state)) -> EMRExtractor:
    """Get EMR extractor instance."""
    return EMRExtractor(state.gemini_rotator)


def get_emr_update_service() -> EMRUpdateService:
    """Get EMR update service instance."""
    return EMRUpdateService()


@router.post("/upload-document", response_model=dict)
async def upload_and_analyze_document(
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    emr_extractor: EMRExtractor = Depends(get_emr_extractor),
    emr_update_service: EMRUpdateService = Depends(get_emr_update_service)
):
    """Upload and analyze a medical document to extract EMR data."""
    try:
        # Validate patient ID
        if not patient_id or not patient_id.strip():
            raise HTTPException(status_code=400, detail="Patient ID is required")

        # Validate file
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Check file size (limit to 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Check file type
        allowed_extensions = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.tiff'}
        file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
            )

        logger().info(f"Document upload requested for patient {patient_id}, file: {file.filename}")

        # Get patient context if available
        patient_context = None
        try:
            from src.data.repositories.patient import get_patient_by_id
            patient = get_patient_by_id(patient_id)
            if patient:
                patient_context = {
                    "name": patient.name,
                    "age": patient.age,
                    "sex": patient.sex,
                    "medications": patient.medications or [],
                    "past_assessment_summary": patient.past_assessment_summary
                }
        except Exception as e:
            logger().warning(f"Could not fetch patient context: {e}")

        # Analyze the document
        extracted_data, confidence_score = await emr_extractor.analyze_document(
            file_content=file_content,
            filename=file.filename,
            patient_context=patient_context
        )

        # Save to database
        emr_id = await emr_update_service.save_document_analysis(
            patient_id=patient_id,
            filename=file.filename,
            file_content=file_content,
            extracted_data=extracted_data,
            confidence_score=confidence_score
        )

        return {
            "emr_id": emr_id,
            "filename": file.filename,
            "confidence_score": confidence_score,
            "extracted_data": {
                "overview": extracted_data.notes.split("Document Overview: ")[-1] if "Document Overview:" in extracted_data.notes else "",
                "diagnosis": extracted_data.diagnosis or [],
                "symptoms": extracted_data.symptoms or [],
                "medications": [
                    {
                        "name": med.name,
                        "dosage": med.dosage,
                        "frequency": med.frequency,
                        "duration": med.duration
                    }
                    for med in extracted_data.medications or []
                ],
                "vital_signs": {
                    "blood_pressure": extracted_data.vital_signs.blood_pressure if extracted_data.vital_signs else None,
                    "heart_rate": extracted_data.vital_signs.heart_rate if extracted_data.vital_signs else None,
                    "temperature": extracted_data.vital_signs.temperature if extracted_data.vital_signs else None,
                    "respiratory_rate": extracted_data.vital_signs.respiratory_rate if extracted_data.vital_signs else None,
                    "oxygen_saturation": extracted_data.vital_signs.oxygen_saturation if extracted_data.vital_signs else None
                } if extracted_data.vital_signs else None,
                "lab_results": [
                    {
                        "test_name": lab.test_name,
                        "value": lab.value,
                        "unit": lab.unit,
                        "reference_range": lab.reference_range
                    }
                    for lab in extracted_data.lab_results or []
                ],
                "procedures": extracted_data.procedures or [],
                "notes": extracted_data.notes or ""
            },
            "message": "Document analyzed and EMR data extracted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger().error(f"Error in document upload and analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-document", response_model=dict)
async def preview_document_analysis(
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    emr_extractor: EMRExtractor = Depends(get_emr_extractor)
):
    """Upload and analyze a medical document to preview extracted data before saving."""
    try:
        # Validate patient ID
        if not patient_id or not patient_id.strip():
            raise HTTPException(status_code=400, detail="Patient ID is required")

        # Validate file
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Check file size (limit to 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # Check file type
        allowed_extensions = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.tiff'}
        file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
            )

        logger().info(f"Document preview requested for patient {patient_id}, file: {file.filename}")

        # Get patient context if available
        patient_context = None
        try:
            from src.data.repositories.patient import get_patient_by_id
            patient = get_patient_by_id(patient_id)
            if patient:
                patient_context = {
                    "name": patient.name,
                    "age": patient.age,
                    "sex": patient.sex,
                    "medications": patient.medications or [],
                    "past_assessment_summary": patient.past_assessment_summary
                }
        except Exception as e:
            logger().warning(f"Could not fetch patient context: {e}")

        # Analyze the document
        extracted_data, confidence_score = await emr_extractor.analyze_document(
            file_content=file_content,
            filename=file.filename,
            patient_context=patient_context
        )

        return {
            "filename": file.filename,
            "confidence_score": confidence_score,
            "extracted_data": {
                "overview": extracted_data.notes.split("Document Overview: ")[-1] if "Document Overview:" in extracted_data.notes else "",
                "diagnosis": extracted_data.diagnosis or [],
                "symptoms": extracted_data.symptoms or [],
                "medications": [
                    {
                        "name": med.name,
                        "dosage": med.dosage,
                        "frequency": med.frequency,
                        "duration": med.duration
                    }
                    for med in extracted_data.medications or []
                ],
                "vital_signs": {
                    "blood_pressure": extracted_data.vital_signs.blood_pressure if extracted_data.vital_signs else None,
                    "heart_rate": extracted_data.vital_signs.heart_rate if extracted_data.vital_signs else None,
                    "temperature": extracted_data.vital_signs.temperature if extracted_data.vital_signs else None,
                    "respiratory_rate": extracted_data.vital_signs.respiratory_rate if extracted_data.vital_signs else None,
                    "oxygen_saturation": extracted_data.vital_signs.oxygen_saturation if extracted_data.vital_signs else None
                } if extracted_data.vital_signs else None,
                "lab_results": [
                    {
                        "test_name": lab.test_name,
                        "value": lab.value,
                        "unit": lab.unit,
                        "reference_range": lab.reference_range
                    }
                    for lab in extracted_data.lab_results or []
                ],
                "procedures": extracted_data.procedures or [],
                "notes": extracted_data.notes or ""
            },
            "message": "Document analyzed successfully. Review the data before saving."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger().error(f"Error in document preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-document-analysis", response_model=dict)
async def save_document_analysis(
    patient_id: str = Form(...),
    filename: str = Form(...),
    extracted_data: str = Form(...),  # JSON string
    confidence_score: float = Form(...),
    emr_update_service: EMRUpdateService = Depends(get_emr_update_service)
):
    """Save document analysis results to EMR database."""
    try:
        import json
        
        # Validate inputs
        if not patient_id or not patient_id.strip():
            raise HTTPException(status_code=400, detail="Patient ID is required")
        if not filename or not filename.strip():
            raise HTTPException(status_code=400, detail="Filename is required")
        if not extracted_data or not extracted_data.strip():
            raise HTTPException(status_code=400, detail="Extracted data is required")

        # Parse extracted data
        try:
            data_dict = json.loads(extracted_data)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in extracted data: {e}")

        # Convert to ExtractedData object
        extracted_data_obj = ExtractedData(
            diagnosis=data_dict.get('diagnosis', []),
            symptoms=data_dict.get('symptoms', []),
            medications=[
                {
                    "name": med.get('name', ''),
                    "dosage": med.get('dosage'),
                    "frequency": med.get('frequency'),
                    "duration": med.get('duration')
                }
                for med in data_dict.get('medications', [])
            ],
            vital_signs=data_dict.get('vital_signs'),
            lab_results=[
                {
                    "test_name": lab.get('test_name', ''),
                    "value": lab.get('value', ''),
                    "unit": lab.get('unit'),
                    "reference_range": lab.get('reference_range')
                }
                for lab in data_dict.get('lab_results', [])
            ],
            procedures=data_dict.get('procedures', []),
            notes=data_dict.get('notes', '') + (f"\n\nDocument Overview: {data_dict.get('overview', '')}" if data_dict.get('overview') else '')
        )

        logger().info(f"Saving document analysis for patient {patient_id}, file: {filename}")

        # Save to database (without file content for preview saves)
        emr_id = await emr_update_service.save_document_analysis(
            patient_id=patient_id,
            filename=filename,
            file_content=b"",  # Empty for preview saves
            extracted_data=extracted_data_obj,
            confidence_score=confidence_score
        )

        return {
            "emr_id": emr_id,
            "message": "Document analysis saved to EMR successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger().error(f"Error saving document analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
