# emr/routes/emr.py

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends

from src.core.state import MedicalState, get_state
from src.emr.models.emr import EMRResponse, EMRSearchRequest, EMRUpdateRequest
from src.emr.services.service import EMRService
from src.utils.logger import logger

router = APIRouter(prefix="/emr", tags=["EMR"])


@router.get("/check/{message_id}", response_model=dict)
async def check_emr_exists(message_id: str):
    """Check if EMR extraction has already been done for a message."""
    try:
        from src.emr.repositories.emr import check_emr_exists
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


def get_emr_service(state: MedicalState = Depends(get_state)) -> EMRService:
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
                    "name": patient.get("name"),
                    "age": patient.get("age"),
                    "sex": patient.get("sex"),
                    "medications": patient.get("medications", []),
                    "past_assessment_summary": patient.get("past_assessment_summary")
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
                            "name": patient.get("name"),
                            "age": patient.get("age"),
                            "sex": patient.get("sex"),
                            "medications": patient.get("medications", []),
                            "past_assessment_summary": patient.get("past_assessment_summary")
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
