# src/core/response_pipeline.py

from fastapi import HTTPException, status

from src.core import prompt_builder
from src.core.state import AppState
from src.data.medical_kb import search_medical_kb
from src.models.account import Account
from src.services.gemini import gemini_chat
from src.services.guard import SafetyGuard
from src.utils.logger import logger
from src.utils.rotator import APIKeyRotator


async def generate_chat_response(
	state: AppState,
	message: str,
	session_id: str,
	patient_id: str,
	account_id: str
) -> str:
	"""
	Handles the pipeline for generating a chat response, including safety checks,
	context retrieval, response generation, and memory persistence.
	"""
	logger().info(f"Starting response pipeline for session {session_id}")

	# 0. Safety Guard: Validate user query
	try:
		safety_guard = SafetyGuard(state.nvidia_rotator)
		is_safe, safety_reason = safety_guard.check_user_query(message)
		if not is_safe:
			logger().warning(f"Safety guard blocked user query: {safety_reason}")
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=f"Query blocked for safety reasons: {safety_reason}"
			)
		logger().info(f"User query passed safety validation: {safety_reason}")
	except Exception as e:
		logger().error(f"Safety guard error: {e}")
		raise e

	# 1. Get Enhanced Context
	# TODO Implement RAG
	try:
		medical_context = await state.memory_manager.get_enhanced_context(
			session_id=session_id,
			patient_id=patient_id,
			question=message,
			nvidia_rotator=state.nvidia_rotator
		)
	except Exception as e:
		logger().error(f"Error getting medical context: {e}")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to build medical context.")

	account = state.memory_manager.get_account(account_id)
	if not account:
		raise Exception("Account not found")

	# 2. Generate AI Response
	try:
		response_text = await generate_medical_response(
			message=message,
			account=account,
			rotator=state.gemini_rotator,
			medical_context=medical_context,
			nvidia_rotator=state.nvidia_rotator
		)
	except Exception as e:
		logger().error(f"Error generating medical response: {e}")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate AI response.")

	# TODO Safety guard is applied twice
	# 2.5. Safety Guard: Validate AI response
	try:
		is_safe, safety_reason = safety_guard.check_model_answer(message, response_text) # type: ignore
		if not is_safe:
			logger().warning(f"Safety guard blocked AI response: {safety_reason}")
			response_text = "I apologize, but I cannot provide a response to that query as it may contain unsafe content. Please consult with a qualified healthcare professional for medical advice."
		else:
			logger().info(f"AI response passed safety validation: {safety_reason}")
	except Exception as e:
		logger().error(f"Safety guard error for response: {e}")
		logger().warning("Safety guard failed for response, allowing through")

	# 3. Process and Store the Exchange
	summary = await state.memory_manager.process_medical_exchange(
		session_id=session_id,
		patient_id=patient_id,
		doctor_id=account_id,
		question=message,
		answer=response_text,
		gemini_rotator=state.gemini_rotator,
		nvidia_rotator=state.nvidia_rotator
	)
	if not summary:
		logger().warning(f"Failed to process and store medical exchange for session {session_id}")

	return response_text

async def generate_medical_response(
	account: Account,
	message: str,
	rotator: APIKeyRotator,
	medical_context: str = "",
	nvidia_rotator: APIKeyRotator | None = None
) -> str:
	"""Generates an intelligent, contextual medical response using Gemini AI."""
	prompt = prompt_builder.medical_response_prompt(
		account=account,
		user_message=message,
		medical_context=medical_context
	)

	# Generate response using Gemini
	response_text = await gemini_chat(prompt, rotator)

	if response_text:
		# Add medical disclaimer if not already present
		if "disclaimer" not in response_text.lower() and "consult" not in response_text.lower():
			response_text += "\n\n⚠️ **Important Disclaimer:** This information is for educational purposes only and should not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals."

		# TODO Safety guard is applied to the response twice
		# Safety Guard: Validate the generated response
		if nvidia_rotator:
			try:
				safety_guard = SafetyGuard(nvidia_rotator)
				is_safe, safety_reason = safety_guard.check_model_answer(message, response_text)
				if not is_safe:
					logger().warning(f"Safety guard blocked generated response: {safety_reason}")
					# Return safe fallback response
					return "I apologize, but I cannot provide a response to that query as it may contain unsafe content. Please consult with a qualified healthcare professional for medical advice."
				else:
					logger().info(f"Generated response passed safety validation: {safety_reason}")
			except Exception as e:
				logger().error(f"Safety guard error in medical response: {e}")
				# Fail open for now - allow response through if guard fails
				logger().warning("Safety guard failed, allowing generated response through")

		logger().info(f"Gemini response generated, length: {len(response_text)} chars")
		return response_text

	logger().warning("Gemini response failed, using fallback.")
	return _generate_fallback_response(message=message, account=account)

def _generate_fallback_response(
	message: str,
	account: Account
) -> str:
	"""Generates a fallback response using a local knowledge base."""
	kb_info = search_medical_kb(message)

	logger().info("Generating backup response")

	# Build response based on available information
	response_parts = []

	# Analyze the question to provide more specific responses
	question_lower = message.lower()

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
	if account.role.lower() in ["physician", "doctor", "nurse"]:
		response_parts.append("\n\n**Professional Context:** As a healthcare professional, you're likely familiar with these concepts. Remember to always follow your institution's protocols and guidelines, and consider the latest clinical evidence in your practice.")
	elif account.role.lower() in ["medical student", "student"]:
		response_parts.append("\n\n**Educational Context:** As a medical student, this information can help with your studies. Always verify information with your professors and clinical supervisors, and use this as a starting point for further research.")
	elif account.role.lower() in ["patient"]:
		response_parts.append("\n\n**Patient Context:** As a patient, this information is for educational purposes only. Please discuss any concerns with your healthcare provider, and don't make treatment decisions based solely on this information.")
	else:
		response_parts.append("\n\n**General Context:** This information is provided for educational purposes. Always consult with qualified healthcare professionals for medical advice.")

	# Add specialty-specific information if available
	if account.specialty and account.specialty.lower() in ["cardiology", "cardiac"]:
		response_parts.append("\n\n**Cardiology Perspective:** Given your interest in cardiology, consider how this information relates to cardiovascular health and patient care. Many conditions can have cardiac implications.")
	elif account.specialty and account.specialty.lower() in ["pediatrics", "pediatric"]:
		response_parts.append("\n\n**Pediatric Perspective:** In pediatric care, remember that children may present differently than adults and may require specialized approaches. Consider age-appropriate considerations.")
	elif account.specialty and account.specialty.lower() in ["emergency", "er"]:
		response_parts.append("\n\n**Emergency Medicine Perspective:** In emergency settings, rapid assessment and intervention are crucial. Consider the urgency and severity of presenting symptoms.")

	# Add medical disclaimer
	response_parts.append("\n\n⚠️ **Important Disclaimer:** This information is for educational purposes only and should not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals.")

	return "\n".join(response_parts)
