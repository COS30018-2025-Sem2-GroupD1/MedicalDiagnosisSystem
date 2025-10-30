# src/services/extractor.py

import base64
import json
import mimetypes
import re
from typing import Any, Dict, List, Optional, Tuple

from src.models.emr import ExtractedData, LabResult, Medication, VitalSigns
#from src.services.gemini import gemini_chat
from src.services.local_llm_service import get_inference
from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator


class EMRExtractor:
    """Service for extracting structured medical data from chat messages using Gemini AI."""

    def __init__(self, gemini_rotator: APIKeyRotator):
        self.gemini_rotator = gemini_rotator

    async def extract_medical_data(self, message: str, patient_context: Optional[Dict[str, Any]] = None) -> Tuple[ExtractedData, float]:
        """
        Extract structured medical data from a chat message using Gemini AI.

        Args:
            message: The chat message to analyze
            patient_context: Optional patient context information

        Returns:
            Tuple of (ExtractedData, confidence_score)
        """
        try:
            # Prepare the prompt for Gemini
            prompt = self._build_extraction_prompt(message, patient_context)

            # Get response from Gemini
            response = await self._call_gemini_api(prompt)

            # Parse the response
            extracted_data, confidence = self._parse_gemini_response(response)

            logger().info(f"Successfully extracted medical data with confidence {confidence:.2f}")
            return extracted_data, confidence

        except Exception as e:
            logger().error(f"Error extracting medical data: {e}")
            # Return empty data with low confidence
            return ExtractedData(), 0.0

    def _build_extraction_prompt(self, message: str, patient_context: Optional[Dict[str, Any]] = None) -> str:
        """Build the prompt for Gemini AI to extract medical data."""

        context_info = ""
        if patient_context:
            context_info = f"""
Patient Context:
- Name: {patient_context.get('name', 'Unknown')}
- Age: {patient_context.get('age', 'Unknown')}
- Sex: {patient_context.get('sex', 'Unknown')}
- Current Medications: {', '.join(patient_context.get('medications', []))}
- Past Assessment Summary: {patient_context.get('past_assessment_summary', 'None')}
"""

        prompt = f"""You are a medical AI assistant specialized in extracting structured medical data from clinical conversations.

{context_info}

Please analyze the following medical message and extract all relevant clinical information in the specified JSON format:

Message: "{message}"

Extract the following information and return ONLY a valid JSON object with this exact structure:

{{
    "diagnosis": ["list of diagnoses mentioned"],
    "symptoms": ["list of symptoms described"],
    "medications": [
        {{
            "name": "medication name",
            "dosage": "dosage if mentioned",
            "frequency": "frequency if mentioned",
            "duration": "duration if mentioned"
        }}
    ],
    "vital_signs": {{
        "blood_pressure": "value if mentioned",
        "heart_rate": "value if mentioned",
        "temperature": "value if mentioned",
        "respiratory_rate": "value if mentioned",
        "oxygen_saturation": "value if mentioned"
    }},
    "lab_results": [
        {{
            "test_name": "test name",
            "value": "test value",
            "unit": "unit if mentioned",
            "reference_range": "normal range if mentioned"
        }}
    ],
    "procedures": ["list of procedures mentioned"],
    "notes": "additional clinical notes and observations"
}}

Guidelines:
1. Only extract information that is explicitly mentioned or clearly implied
2. Use medical terminology appropriately
3. If a field has no relevant information, use an empty array [] or null
4. For medications, only include those that are prescribed, recommended, or mentioned as current
5. Extract vital signs only if specific values are mentioned
6. Include lab results only if specific test values are provided
7. Be conservative - it's better to miss something than to hallucinate information
8. Return ONLY the JSON object, no additional text or explanation

Confidence Assessment:
After the JSON, provide a confidence score (0.0-1.0) based on:
- Clarity of medical information in the message
- Specificity of clinical details
- Presence of measurable values (vitals, lab results)
- Overall clinical relevance

Format: CONFIDENCE: 0.85

Return the JSON followed by the confidence score on a new line."""

        return prompt

    async def _call_gemini_api(self, prompt: str) -> str:
        """Call the Gemini API with the extraction prompt."""
        try:
            # Use the gemini_chat function with the rotator
            #response = await gemini_chat(prompt, self.gemini_rotator)
            response = get_inference(prompt=prompt)
            return response
        except Exception as e:
            logger().error(f"Error calling Gemini API: {e}")
            raise

    def _parse_gemini_response(self, response: str) -> Tuple[ExtractedData, float]:
        """Parse the Gemini response to extract structured data and confidence score."""
        try:
            # Extract confidence score
            confidence = 0.5  # Default confidence
            confidence_match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response)
            if confidence_match:
                confidence = float(confidence_match.group(1))

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger().warning("No JSON found in Gemini response")
                return ExtractedData(), confidence

            json_str = json_match.group(0)
            data = json.loads(json_str)

            # Parse medications
            medications = []
            for med_data in data.get('medications', []):
                if isinstance(med_data, dict):
                    medications.append(Medication(
                        name=med_data.get('name', ''),
                        dosage=med_data.get('dosage'),
                        frequency=med_data.get('frequency'),
                        duration=med_data.get('duration')
                    ))

            # Parse vital signs
            vital_signs_data = data.get('vital_signs', {})
            vital_signs = None
            if vital_signs_data and any(vital_signs_data.values()):
                vital_signs = VitalSigns(
                    blood_pressure=vital_signs_data.get('blood_pressure'),
                    heart_rate=vital_signs_data.get('heart_rate'),
                    temperature=vital_signs_data.get('temperature'),
                    respiratory_rate=vital_signs_data.get('respiratory_rate'),
                    oxygen_saturation=vital_signs_data.get('oxygen_saturation')
                )

            # Parse lab results
            lab_results = []
            for lab_data in data.get('lab_results', []):
                if isinstance(lab_data, dict):
                    lab_results.append(LabResult(
                        test_name=lab_data.get('test_name', ''),
                        value=lab_data.get('value', ''),
                        unit=lab_data.get('unit'),
                        reference_range=lab_data.get('reference_range')
                    ))

            # Create ExtractedData object
            extracted_data = ExtractedData(
                diagnosis=data.get('diagnosis', []),
                symptoms=data.get('symptoms', []),
                medications=medications,
                vital_signs=vital_signs,
                lab_results=lab_results,
                procedures=data.get('procedures', []),
                notes=data.get('notes', '') + (f"\n\nDocument Overview: {data.get('overview', '')}" if data.get('overview') else '')
            )

            return extracted_data, confidence

        except json.JSONDecodeError as e:
            logger().error(f"Error parsing JSON from Gemini response: {e}")
            return ExtractedData(), 0.0
        except Exception as e:
            logger().error(f"Error parsing Gemini response: {e}")
            return ExtractedData(), 0.0

    def extract_medications_from_text(self, text: str) -> List[str]:
        """Extract medication names from text using pattern matching."""
        # Common medication patterns
        medication_patterns = [
            r'\b(?:acetaminophen|tylenol|ibuprofen|advil|motrin|aspirin|naproxen|aleve)\b',
            r'\b(?:metformin|insulin|glipizide|metoprolol|lisinopril|amlodipine|atorvastatin|simvastatin)\b',
            r'\b(?:omeprazole|pantoprazole|ranitidine|famotidine|sertraline|fluoxetine|paroxetine)\b',
            r'\b(?:prednisone|hydrocortisone|dexamethasone|methylprednisolone)\b',
            r'\b(?:warfarin|heparin|clopidogrel|aspirin)\b',
            r'\b(?:furosemide|hydrochlorothiazide|spironolactone|triamterene)\b'
        ]

        medications = set()
        for pattern in medication_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            medications.update(matches)

        return list(medications)

    def extract_vital_signs_from_text(self, text: str) -> Dict[str, str]:
        """Extract vital signs from text using pattern matching."""
        vital_signs = {}

        # Blood pressure patterns
        bp_pattern = r'(?:blood pressure|bp|pressure)\s*:?\s*(\d{2,3}/\d{2,3})'
        bp_match = re.search(bp_pattern, text, re.IGNORECASE)
        if bp_match:
            vital_signs['blood_pressure'] = bp_match.group(1)

        # Heart rate patterns
        hr_pattern = r'(?:heart rate|hr|pulse)\s*:?\s*(\d{2,3})\s*(?:bpm|beats per minute)?'
        hr_match = re.search(hr_pattern, text, re.IGNORECASE)
        if hr_match:
            vital_signs['heart_rate'] = hr_match.group(1)

        # Temperature patterns
        temp_pattern = r'(?:temperature|temp|fever)\s*:?\s*(\d{2,3}(?:\.\d)?)\s*(?:°?[fc])?'
        temp_match = re.search(temp_pattern, text, re.IGNORECASE)
        if temp_match:
            vital_signs['temperature'] = temp_match.group(1)

        # Respiratory rate patterns
        rr_pattern = r'(?:respiratory rate|rr|breathing rate)\s*:?\s*(\d{1,2})\s*(?:breaths per minute|bpm)?'
        rr_match = re.search(rr_pattern, text, re.IGNORECASE)
        if rr_match:
            vital_signs['respiratory_rate'] = rr_match.group(1)

        # Oxygen saturation patterns
        o2_pattern = r'(?:oxygen saturation|o2 sat|spo2)\s*:?\s*(\d{2,3})\s*%?'
        o2_match = re.search(o2_pattern, text, re.IGNORECASE)
        if o2_match:
            vital_signs['oxygen_saturation'] = o2_match.group(1)

        return vital_signs

    async def analyze_document(self, file_content: bytes, filename: str, patient_context: Optional[Dict[str, Any]] = None) -> Tuple[ExtractedData, float]:
        """
        Analyze a medical document (PDF, image, or text) and extract structured medical data.

        Args:
            file_content: The binary content of the uploaded file
            filename: The name of the uploaded file
            patient_context: Optional patient context information

        Returns:
            Tuple of (ExtractedData, confidence_score)
        """
        try:
            # Determine file type and prepare content for Gemini
            mime_type, _ = mimetypes.guess_type(filename)

            if not mime_type:
                logger().warning(f"Unknown file type for {filename}")
                return ExtractedData(), 0.0

            # Encode file content to base64
            file_base64 = base64.b64encode(file_content).decode('utf-8')

            # Build the prompt for document analysis
            prompt = self._build_document_analysis_prompt(file_base64, mime_type, filename, patient_context)

            # Get response from Gemini
            response = await self._call_gemini_api(prompt)

            # Parse the response
            extracted_data, confidence = self._parse_gemini_response(response)

            logger().info(f"Successfully analyzed document {filename} with confidence {confidence:.2f}")
            return extracted_data, confidence

        except Exception as e:
            logger().error(f"Error analyzing document {filename}: {e}")
            # Return empty data with low confidence
            return ExtractedData(), 0.0

    def _build_document_analysis_prompt(self, file_base64: str, mime_type: str, filename: str, patient_context: Optional[Dict[str, Any]] = None) -> str:
        """Build the prompt for Gemini AI to analyze medical documents."""

        context_info = ""
        if patient_context:
            context_info = f"""
Patient Context:
- Name: {patient_context.get('name', 'Unknown')}
- Age: {patient_context.get('age', 'Unknown')}
- Sex: {patient_context.get('sex', 'Unknown')}
- Current Medications: {', '.join(patient_context.get('medications', []))}
- Past Assessment Summary: {patient_context.get('past_assessment_summary', 'None')}
"""

        # Determine the content type for Gemini
        if mime_type.startswith('image/'):
            content_type = "image"
        elif mime_type == 'application/pdf':
            content_type = "pdf"
        elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            content_type = "document"
        else:
            content_type = "text"

        prompt = f"""You are a medical AI assistant specialized in analyzing medical documents and extracting structured clinical information.

{context_info}

Please analyze the following medical document and extract all relevant clinical information in the specified JSON format.

Document Information:
- Filename: {filename}
- Content Type: {content_type}
- MIME Type: {mime_type}

Document Content (Base64 encoded):
{file_base64}

Extract the following information and return ONLY a valid JSON object with this exact structure:

{{
    "overview": "Brief summary of the document content and main findings",
    "diagnosis": ["list of diagnoses mentioned or identified"],
    "symptoms": ["list of symptoms described"],
    "medications": [
        {{
            "name": "medication name",
            "dosage": "dosage if mentioned",
            "frequency": "frequency if mentioned",
            "duration": "duration if mentioned"
        }}
    ],
    "vital_signs": {{
        "blood_pressure": "value if mentioned",
        "heart_rate": "value if mentioned",
        "temperature": "value if mentioned",
        "respiratory_rate": "value if mentioned",
        "oxygen_saturation": "value if mentioned"
    }},
    "lab_results": [
        {{
            "test_name": "test name",
            "value": "test value",
            "unit": "unit if mentioned",
            "reference_range": "normal range if mentioned"
        }}
    ],
    "procedures": ["list of procedures mentioned or performed"],
    "notes": "additional clinical notes and observations"
}}

Guidelines for Document Analysis:
1. Carefully read and analyze the entire document content
2. Extract information that is explicitly mentioned or clearly documented
3. Use medical terminology appropriately and maintain accuracy
4. If a field has no relevant information, use an empty array [] or null
5. For medications, include all prescribed, recommended, or mentioned medications
6. Extract vital signs only if specific values are documented
7. Include lab results only if specific test values are provided
8. Be thorough but conservative - prioritize accuracy over completeness
9. For images, focus on visible text, charts, and medical data
10. For PDFs and documents, analyze all text content systematically
11. Return ONLY the JSON object, no additional text or explanation

Confidence Assessment:
After the JSON, provide a confidence score (0.0-1.0) based on:
- Document clarity and readability
- Specificity of medical information
- Presence of measurable values (vitals, lab results)
- Overall clinical relevance and completeness
- Document type and quality

Format: CONFIDENCE: 0.85

Return the JSON followed by the confidence score on a new line."""

        return prompt
