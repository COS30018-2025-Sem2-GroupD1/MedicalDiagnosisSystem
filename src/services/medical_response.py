# services/medical_response.py

from data.medical_kb import search_medical_kb
from src.services.gemini import gemini_chat
from src.utils.logger import get_logger
from src.utils.rotator import APIKeyRotator

logger = get_logger("MEDICAL_RESPONSE", __name__)

async def generate_medical_response(
	user_message: str,
	user_role: str,
	user_specialty: str,
	rotator: APIKeyRotator,
	medical_context: str = ""
) -> str:
	"""Generate a medical response using Gemini AI for intelligent, contextual responses"""
	# Build context-aware prompt
	# In future this should be moved to a prompt builder function that adds more information and direction based on the user's role and specialty.
	prompt = f"""You are a knowledgeable medical AI assistant. Provide a comprehensive, accurate, and helpful response to this medical question.
**User Role:** {user_role}
**User Specialty:** {user_specialty if user_specialty else 'General'}
**Medical Context:** {medical_context if medical_context else 'No previous context'}
**Question:** {user_message}
**Instructions:**
1. Provide a detailed, medically accurate response
2. Consider the user's role and specialty
3. Include relevant medical information and guidance
4. Mention when professional medical consultation is needed
5. Use clear, professional language
6. Include appropriate medical disclaimers
**Response Format:**
- Start with a direct answer to the question
- Provide relevant medical information
- Include role-specific guidance
- Add appropriate warnings and disclaimers
- Keep the response comprehensive but focused
Remember: This is for educational purposes only. Always emphasize consulting healthcare professionals for medical advice."""

	# Generate response using Gemini
	response_text = await gemini_chat(prompt, rotator)

	if response_text:
		# Add medical disclaimer if not already present
		if "disclaimer" not in response_text.lower() and "consult" not in response_text.lower():
			response_text += "\n\n⚠️ **Important Disclaimer:** This information is for educational purposes only and should not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals."

		logger.info(f"Gemini response generated successfully, length: {len(response_text)} characters")
		return response_text

	# Fallback if Gemini fails
	logger.warning("Gemini response generation failed, using fallback")
	return generate_medical_response_fallback(
		user_message,
		user_role,
		user_specialty,
		medical_context
	)

def generate_medical_response_fallback(
	user_message: str,
	user_role: str,
	user_specialty: str,
	medical_context: str = ""
) -> str:
	"""Fallback medical response generator using local knowledge base"""
	# Search medical knowledge base
	kb_info = search_medical_kb(user_message)

	logger.info("Generating backup response")

	# Build response based on available information
	response_parts = []

	# Analyze the question to provide more specific responses
	question_lower = user_message.lower()

	if kb_info:
		response_parts.append(f"Based on your question about medical topics, here's what I found:\n\n{kb_info}")

		# Add specific guidance based on the medical topic
		if any(word in question_lower for word in ["fever", "temperature", "hot"]):
			response_parts.append("\n\n**Key Points about Fever:**")
			response_parts.append("• Normal body temperature is around 98.6°F (37°C)")
			response_parts.append("• Fever is often a sign of infection or inflammation")
			response_parts.append("• Monitor for other symptoms that accompany fever")
			response_parts.append("• Seek medical attention for high fevers (>103°F/39.4°C) or persistent fevers")

		elif any(word in question_lower for word in ["headache", "head pain", "migraine"]):
			response_parts.append("\n\n**Key Points about Headaches:**")
			response_parts.append("• Tension headaches are the most common type")
			response_parts.append("• Migraines often have specific triggers and symptoms")
			response_parts.append("• Sudden, severe headaches require immediate medical attention")
			response_parts.append("• Keep a headache diary to identify patterns")

		elif any(word in question_lower for word in ["cough", "cold", "respiratory"]):
			response_parts.append("\n\n**Key Points about Respiratory Symptoms:**")
			response_parts.append("• Dry vs. productive cough have different implications")
			response_parts.append("• Most colds resolve within 7-10 days")
			response_parts.append("• Persistent cough may indicate underlying conditions")
			response_parts.append("• Monitor for difficulty breathing or chest pain")

		elif any(word in question_lower for word in ["hypertension", "blood pressure", "high bp"]):
			response_parts.append("\n\n**Key Points about Hypertension:**")
			response_parts.append("• Often called the 'silent killer' due to lack of symptoms")
			response_parts.append("• Regular monitoring is essential")
			response_parts.append("• Lifestyle modifications can help control blood pressure")
			response_parts.append("• Medication may be necessary for some individuals")

		elif any(word in question_lower for word in ["diabetes", "blood sugar", "glucose"]):
			response_parts.append("\n\n**Key Points about Diabetes:**")
			response_parts.append("• Type 1: Autoimmune, requires insulin")
			response_parts.append("• Type 2: Often lifestyle-related, may be managed with diet/exercise")
			response_parts.append("• Regular blood sugar monitoring is crucial")
			response_parts.append("• Complications can affect multiple organ systems")

	else:
		# Provide more helpful response for general questions
		if "what is" in question_lower or "define" in question_lower:
			response_parts.append("I understand you're asking about a medical topic. While I don't have specific information about this particular condition or symptom, I can provide some general guidance.")
		elif "how to" in question_lower or "treatment" in question_lower:
			response_parts.append("I understand you're asking about treatment or management of a medical condition. This is an area where professional medical advice is particularly important.")
		elif "symptom" in question_lower or "sign" in question_lower:
			response_parts.append("I understand you're asking about symptoms or signs of a medical condition. Remember that symptoms can vary between individuals and may indicate different conditions.")
		else:
			response_parts.append("Thank you for your medical question. While I can provide general information, it's important to consult with healthcare professionals for personalized medical advice.")

	# Add role-specific guidance
	if user_role.lower() in ["physician", "doctor", "nurse"]:
		response_parts.append("\n\n**Professional Context:** As a healthcare professional, you're likely familiar with these concepts. Remember to always follow your institution's protocols and guidelines, and consider the latest clinical evidence in your practice.")
	elif user_role.lower() in ["medical student", "student"]:
		response_parts.append("\n\n**Educational Context:** As a medical student, this information can help with your studies. Always verify information with your professors and clinical supervisors, and use this as a starting point for further research.")
	elif user_role.lower() in ["patient"]:
		response_parts.append("\n\n**Patient Context:** As a patient, this information is for educational purposes only. Please discuss any concerns with your healthcare provider, and don't make treatment decisions based solely on this information.")
	else:
		response_parts.append("\n\n**General Context:** This information is provided for educational purposes. Always consult with qualified healthcare professionals for medical advice.")

	# Add specialty-specific information if available
	if user_specialty and user_specialty.lower() in ["cardiology", "cardiac"]:
		response_parts.append("\n\n**Cardiology Perspective:** Given your interest in cardiology, consider how this information relates to cardiovascular health and patient care. Many conditions can have cardiac implications.")
	elif user_specialty and user_specialty.lower() in ["pediatrics", "pediatric"]:
		response_parts.append("\n\n**Pediatric Perspective:** In pediatric care, remember that children may present differently than adults and may require specialized approaches. Consider age-appropriate considerations.")
	elif user_specialty and user_specialty.lower() in ["emergency", "er"]:
		response_parts.append("\n\n**Emergency Medicine Perspective:** In emergency settings, rapid assessment and intervention are crucial. Consider the urgency and severity of presenting symptoms.")

	# Add medical disclaimer
	response_parts.append("\n\n⚠️ **Important Disclaimer:** This information is for educational purposes only and should not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals.")

	return "\n".join(response_parts)
