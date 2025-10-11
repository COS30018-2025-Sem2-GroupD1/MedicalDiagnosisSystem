# src/services/service.py

from typing import Any, Dict, List, Optional

from src.data.repositories.emr import (create_emr_entry, delete_emr_entry,
                                       get_emr_by_id, get_emr_statistics,
                                       get_patient_emr_entries,
                                       search_emr_by_semantic_similarity,
                                       update_emr_entry)
from src.models.emr import EMRCreateRequest, EMRResponse, ExtractedData
from src.services.extractor import EMRExtractor
from src.utils.embeddings import EmbeddingClient
from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator


class EMRService:
    """Main service for EMR operations including extraction, storage, and retrieval."""

    def __init__(self, gemini_rotator: APIKeyRotator, embedding_client: EmbeddingClient):
        self.gemini_rotator = gemini_rotator
        self.embedding_client = embedding_client
        self.extractor = EMRExtractor(gemini_rotator)

    async def extract_and_store_emr(
        self,
        patient_id: str,
        doctor_id: str,
        message_id: str,
        session_id: str,
        message: str,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Extract medical data from a message and store it as an EMR entry.

        Args:
            patient_id: ID of the patient
            doctor_id: ID of the doctor
            message_id: ID of the message being analyzed
            session_id: ID of the chat session
            message: The message content to analyze
            patient_context: Optional patient context information

        Returns:
            ID of the created EMR entry
        """
        try:
            logger().info(f"Starting EMR extraction for patient {patient_id}, message {message_id}")

            # Extract medical data using Gemini AI
            extracted_data, confidence = await self.extractor.extract_medical_data(
                message, patient_context
            )

            # Generate embeddings for the extracted data
            embeddings = await self._generate_embeddings(extracted_data, message)

            # Create EMR entry
            emr_request = EMRCreateRequest(
                patient_id=patient_id,
                doctor_id=doctor_id,
                message_id=message_id,
                session_id=session_id,
                original_message=message,
                extracted_data=extracted_data,
                confidence_score=confidence
            )

            # Store in database
            emr_id = create_emr_entry(emr_request, embeddings)

            logger().info(f"Successfully created EMR entry {emr_id} with confidence {confidence:.2f}")
            return emr_id

        except Exception as e:
            logger().error(f"Error in extract_and_store_emr: {e}")
            raise

    async def _generate_embeddings(self, extracted_data: ExtractedData, original_message: str) -> List[float]:
        """Generate embeddings for the extracted medical data."""
        try:
            # Combine all extracted data into a single text for embedding
            text_parts = []

            if extracted_data.diagnosis:
                text_parts.append(f"Diagnoses: {', '.join(extracted_data.diagnosis)}")

            if extracted_data.symptoms:
                text_parts.append(f"Symptoms: {', '.join(extracted_data.symptoms)}")

            if extracted_data.medications:
                med_text = []
                for med in extracted_data.medications:
                    med_str = med.name
                    if med.dosage:
                        med_str += f" {med.dosage}"
                    if med.frequency:
                        med_str += f" {med.frequency}"
                    med_text.append(med_str)
                text_parts.append(f"Medications: {', '.join(med_text)}")

            if extracted_data.vital_signs:
                vitals = []
                if extracted_data.vital_signs.blood_pressure:
                    vitals.append(f"BP: {extracted_data.vital_signs.blood_pressure}")
                if extracted_data.vital_signs.heart_rate:
                    vitals.append(f"HR: {extracted_data.vital_signs.heart_rate}")
                if extracted_data.vital_signs.temperature:
                    vitals.append(f"Temp: {extracted_data.vital_signs.temperature}")
                if vitals:
                    text_parts.append(f"Vital Signs: {', '.join(vitals)}")

            if extracted_data.lab_results:
                lab_text = []
                for lab in extracted_data.lab_results:
                    lab_str = f"{lab.test_name}: {lab.value}"
                    if lab.unit:
                        lab_str += f" {lab.unit}"
                    lab_text.append(lab_str)
                text_parts.append(f"Lab Results: {', '.join(lab_text)}")

            if extracted_data.procedures:
                text_parts.append(f"Procedures: {', '.join(extracted_data.procedures)}")

            if extracted_data.notes:
                text_parts.append(f"Notes: {extracted_data.notes}")

            # Add original message for context
            text_parts.append(f"Original: {original_message}")

            # Generate embeddings
            combined_text = " | ".join(text_parts)
            embeddings = self.embedding_client.embed(combined_text)[0]

            return embeddings

        except Exception as e:
            logger().error(f"Error generating embeddings: {e}")
            # Return empty embeddings if generation fails
            return []

    async def get_patient_emr(
        self,
        patient_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[EMRResponse]:
        """Get EMR entries for a specific patient."""
        try:
            entries = get_patient_emr_entries(patient_id, limit, offset)

            emr_responses = []
            for entry in entries:
                emr_response = EMRResponse(
                    emr_id=str(entry["_id"]),
                    patient_id=entry["patient_id"],
                    doctor_id=entry["doctor_id"],
                    message_id=entry["message_id"],
                    session_id=entry["session_id"],
                    original_message=entry["original_message"],
                    extracted_data=ExtractedData(**entry["extracted_data"]),
                    confidence_score=entry["confidence_score"],
                    created_at=entry["created_at"],
                    updated_at=entry["updated_at"]
                )
                emr_responses.append(emr_response)

            return emr_responses

        except Exception as e:
            logger().error(f"Error getting patient EMR: {e}")
            return []

    async def search_emr_semantic(
        self,
        patient_id: str,
        query: str,
        limit: int = 10
    ) -> List[EMRResponse]:
        """Search EMR entries using semantic similarity."""
        try:
            # Generate embeddings for the search query
            query_embeddings = self.embedding_client.embed(query)[0]

            # Search using semantic similarity
            entries = search_emr_by_semantic_similarity(
                patient_id, query_embeddings, limit
            )

            emr_responses = []
            for entry in entries:
                emr_response = EMRResponse(
                    emr_id=str(entry["_id"]),
                    patient_id=entry["patient_id"],
                    doctor_id=entry["doctor_id"],
                    message_id=entry["message_id"],
                    session_id=entry["session_id"],
                    original_message=entry["original_message"],
                    extracted_data=ExtractedData(**entry["extracted_data"]),
                    confidence_score=entry["confidence_score"],
                    created_at=entry["created_at"],
                    updated_at=entry["updated_at"]
                )
                emr_responses.append(emr_response)

            return emr_responses

        except Exception as e:
            logger().error(f"Error searching EMR semantically: {e}")
            return []

    async def get_emr_by_id(self, emr_id: str) -> Optional[EMRResponse]:
        """Get a specific EMR entry by ID."""
        try:
            entry = get_emr_by_id(emr_id)
            if not entry:
                return None

            return EMRResponse(
                emr_id=str(entry["_id"]),
                patient_id=entry["patient_id"],
                doctor_id=entry["doctor_id"],
                message_id=entry["message_id"],
                session_id=entry["session_id"],
                original_message=entry["original_message"],
                extracted_data=ExtractedData(**entry["extracted_data"]),
                confidence_score=entry["confidence_score"],
                created_at=entry["created_at"],
                updated_at=entry["updated_at"]
            )

        except Exception as e:
            logger().error(f"Error getting EMR by ID: {e}")
            return None

    async def update_emr(self, emr_id: str, updates: Dict[str, Any]) -> bool:
        """Update an EMR entry."""
        try:
            return update_emr_entry(emr_id, updates)
        except Exception as e:
            logger().error(f"Error updating EMR: {e}")
            return False

    async def delete_emr(self, emr_id: str) -> bool:
        """Delete an EMR entry."""
        try:
            return delete_emr_entry(emr_id)
        except Exception as e:
            logger().error(f"Error deleting EMR: {e}")
            return False

    async def get_emr_statistics(self, patient_id: str) -> Dict[str, Any]:
        """Get EMR statistics for a patient."""
        try:
            return get_emr_statistics(patient_id)
        except Exception as e:
            logger().error(f"Error getting EMR statistics: {e}")
            return {}
