# emr/services/emr_extractor.py

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.emr.models.emr import ExtractedData, Medication, VitalSigns, LabResult
from src.services.gemini import GeminiRotator
from src.utils.logger import logger


class EMRExtractor:
    """Service for extracting structured medical data from chat messages using Gemini AI."""
    
    def __init__(self, gemini_rotator: GeminiRotator):
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
            # Use the gemini rotator to get a response
            response = await self.gemini_rotator.generate_response(
                prompt,
                max_tokens=2000,
                temperature=0.1  # Low temperature for more consistent extraction
            )
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
                notes=data.get('notes')
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
