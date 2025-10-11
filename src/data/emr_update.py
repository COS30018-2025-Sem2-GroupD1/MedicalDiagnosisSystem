# src/data/emr_update.py

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.data.connection import get_database
from src.models.emr import ExtractedData
from src.utils.logger import logger


class EMRUpdateService:
    """Service for updating EMR records with document analysis results."""

    def __init__(self):
        self.db = get_database()

    async def save_document_analysis(
        self,
        patient_id: str,
        filename: str,
        file_content: bytes,
        extracted_data: ExtractedData,
        confidence_score: float,
        original_message: str = None
    ) -> str:
        """
        Save document analysis results to the EMR database.

        Args:
            patient_id: The ID of the patient
            filename: The name of the uploaded file
            file_content: The binary content of the file
            extracted_data: The extracted medical data
            confidence_score: The confidence score of the analysis
            original_message: Optional original message (for chat-based entries)

        Returns:
            The EMR ID of the created record
        """
        try:
            # Generate unique EMR ID
            emr_id = str(uuid.uuid4())
            
            # Prepare the EMR record
            emr_record = {
                "emr_id": emr_id,
                "patient_id": patient_id,
                "original_message": original_message or f"Document upload: {filename}",
                "extracted_data": {
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
                "confidence_score": confidence_score,
                "source": "document_upload",
                "filename": filename,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Save to database
            result = await self.db.emr_records.insert_one(emr_record)
            
            if result.inserted_id:
                logger().info(f"Successfully saved document analysis for patient {patient_id}, EMR ID: {emr_id}")
                return emr_id
            else:
                raise Exception("Failed to insert EMR record")

        except Exception as e:
            logger().error(f"Error saving document analysis: {e}")
            raise

    async def update_emr_record(
        self,
        emr_id: str,
        extracted_data: ExtractedData,
        confidence_score: float = None
    ) -> bool:
        """
        Update an existing EMR record with new extracted data.

        Args:
            emr_id: The EMR record ID to update
            extracted_data: The updated extracted medical data
            confidence_score: Optional new confidence score

        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Prepare update data
            update_data = {
                "extracted_data": {
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
                "updated_at": datetime.utcnow()
            }

            if confidence_score is not None:
                update_data["confidence_score"] = confidence_score

            # Update the record
            result = await self.db.emr_records.update_one(
                {"emr_id": emr_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger().info(f"Successfully updated EMR record {emr_id}")
                return True
            else:
                logger().warning(f"No EMR record found with ID {emr_id}")
                return False

        except Exception as e:
            logger().error(f"Error updating EMR record {emr_id}: {e}")
            raise

    async def get_emr_record(self, emr_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an EMR record by ID.

        Args:
            emr_id: The EMR record ID

        Returns:
            The EMR record if found, None otherwise
        """
        try:
            record = await self.db.emr_records.find_one({"emr_id": emr_id})
            if record:
                # Convert ObjectId to string for JSON serialization
                record["_id"] = str(record["_id"])
            return record

        except Exception as e:
            logger().error(f"Error retrieving EMR record {emr_id}: {e}")
            raise

    async def delete_emr_record(self, emr_id: str) -> bool:
        """
        Delete an EMR record.

        Args:
            emr_id: The EMR record ID to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = await self.db.emr_records.delete_one({"emr_id": emr_id})
            
            if result.deleted_count > 0:
                logger().info(f"Successfully deleted EMR record {emr_id}")
                return True
            else:
                logger().warning(f"No EMR record found with ID {emr_id}")
                return False

        except Exception as e:
            logger().error(f"Error deleting EMR record {emr_id}: {e}")
            raise

    async def get_patient_emr_records(
        self,
        patient_id: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve EMR records for a specific patient.

        Args:
            patient_id: The patient ID
            limit: Maximum number of records to return
            skip: Number of records to skip

        Returns:
            List of EMR records
        """
        try:
            cursor = self.db.emr_records.find(
                {"patient_id": patient_id}
            ).sort("created_at", -1).skip(skip).limit(limit)

            records = []
            async for record in cursor:
                # Convert ObjectId to string for JSON serialization
                record["_id"] = str(record["_id"])
                records.append(record)

            return records

        except Exception as e:
            logger().error(f"Error retrieving EMR records for patient {patient_id}: {e}")
            raise

    async def get_patient_emr_statistics(self, patient_id: str) -> Dict[str, Any]:
        """
        Get EMR statistics for a patient.

        Args:
            patient_id: The patient ID

        Returns:
            Dictionary containing EMR statistics
        """
        try:
            pipeline = [
                {"$match": {"patient_id": patient_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_entries": {"$sum": 1},
                        "avg_confidence": {"$avg": "$confidence_score"},
                        "diagnosis_count": {
                            "$sum": {
                                "$cond": [
                                    {"$gt": [{"$size": {"$ifNull": ["$extracted_data.diagnosis", []]}}, 0]},
                                    1,
                                    0
                                ]
                            }
                        },
                        "medication_count": {
                            "$sum": {
                                "$cond": [
                                    {"$gt": [{"$size": {"$ifNull": ["$extracted_data.medications", []]}}, 0]},
                                    1,
                                    0
                                ]
                            }
                        }
                    }
                }
            ]

            result = await self.db.emr_records.aggregate(pipeline).to_list(1)
            
            if result:
                stats = result[0]
                return {
                    "total_entries": stats.get("total_entries", 0),
                    "avg_confidence": stats.get("avg_confidence", 0.0),
                    "diagnosis_count": stats.get("diagnosis_count", 0),
                    "medication_count": stats.get("medication_count", 0)
                }
            else:
                return {
                    "total_entries": 0,
                    "avg_confidence": 0.0,
                    "diagnosis_count": 0,
                    "medication_count": 0
                }

        except Exception as e:
            logger().error(f"Error retrieving EMR statistics for patient {patient_id}: {e}")
            raise
