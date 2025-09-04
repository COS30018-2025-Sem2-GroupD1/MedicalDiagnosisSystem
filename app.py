# app.py
# Access via: https://medai-cos30018-medicaldiagnosissystem.hf.space/
import os
import time
import logging
import uvicorn
from google import genai
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️ python-dotenv not available, using system environment variables")
except Exception as e:
    print(f"⚠️ Error loading .env file: {e}")

# Import our custom modules
from memo.memory import MemoryLRU
from memo.history import MedicalHistoryManager
from utils.rotator import APIKeyRotator
from utils.embeddings import create_embedding_client
from utils.logger import get_logger

# Configure logging
logger = get_logger("MEDICAL_APP", __name__)

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    user_role: Optional[str] = "Medical Professional"
    user_specialty: Optional[str] = ""
    title: Optional[str] = "New Chat"  # Added missing title field

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    medical_context: Optional[str] = None

class UserProfileRequest(BaseModel):
    user_id: str
    name: str
    role: str
    specialty: Optional[str] = ""

class SessionRequest(BaseModel):
    user_id: str
    title: Optional[str] = "New Chat"

# Initialize FastAPI app
app = FastAPI(
    title="Medical AI Assistant",
    description="AI-powered medical chatbot with memory and context awareness",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
memory_system = MemoryLRU(capacity=50, max_sessions_per_user=20)
embedding_client = create_embedding_client("all-MiniLM-L6-v2", dimension=384)
history_manager = MedicalHistoryManager(memory_system, embedding_client)

# Initialize API rotators for Gemini and NVIDIA
gemini_rotator = APIKeyRotator("GEMINI_API_", max_slots=5)
nvidia_rotator = APIKeyRotator("NVIDIA_API_", max_slots=5)

# Mock medical knowledge base for demo purposes
MEDICAL_KB = {
    "symptoms": {
        "fever": "Fever is a temporary increase in body temperature, often due to illness. Normal body temperature is around 98.6°F (37°C).",
        "headache": "Headache is pain in the head or upper neck. Common types include tension headaches, migraines, and cluster headaches.",
        "cough": "Cough is a sudden expulsion of air from the lungs. It can be dry or productive (bringing up mucus).",
        "fatigue": "Fatigue is extreme tiredness that doesn't improve with rest. It can be caused by various medical conditions.",
        "nausea": "Nausea is a feeling of sickness with an inclination to vomit. It can be caused by various conditions including infections, medications, and pregnancy.",
        "dizziness": "Dizziness is a sensation of lightheadedness or unsteadiness. It can be caused by inner ear problems, low blood pressure, or neurological conditions.",
        "chest pain": "Chest pain can have many causes, from muscle strain to serious heart conditions. Any unexplained chest pain should be evaluated by a healthcare provider.",
        "shortness of breath": "Shortness of breath, or dyspnea, is difficulty breathing. It can be caused by respiratory, cardiac, or other medical conditions."
    },
    "conditions": {
        "hypertension": "Hypertension (high blood pressure) is a common condition that affects the arteries. It's often called the 'silent killer' because it usually has no symptoms.",
        "diabetes": "Diabetes is a chronic disease that affects how your body turns food into energy. There are two main types: Type 1 and Type 2.",
        "asthma": "Asthma is a condition that affects the airways in the lungs. It can cause wheezing, shortness of breath, chest tightness, and coughing.",
        "pneumonia": "Pneumonia is an infection that inflames the air sacs in one or both lungs. It can be caused by bacteria, viruses, or fungi.",
        "heart disease": "Heart disease refers to various conditions affecting the heart, including coronary artery disease, heart failure, and arrhythmias.",
        "arthritis": "Arthritis is inflammation of the joints, causing pain and stiffness. The most common types are osteoarthritis and rheumatoid arthritis.",
        "depression": "Depression is a mental health disorder characterized by persistently depressed mood or loss of interest in activities.",
        "anxiety": "Anxiety disorders involve excessive fear or worry that can interfere with daily activities and relationships."
    },
    "medications": {
        "aspirin": "Aspirin is a common medication used to treat pain, fever, and inflammation. It's also used to prevent heart attacks and strokes.",
        "ibuprofen": "Ibuprofen is a nonsteroidal anti-inflammatory drug (NSAID) used to reduce fever and treat pain or inflammation.",
        "acetaminophen": "Acetaminophen is used to treat pain and reduce fever. It's generally safe when used as directed.",
        "antibiotics": "Antibiotics are medications that fight bacterial infections. They don't work against viral infections like colds or flu.",
        "insulin": "Insulin is a hormone that helps control blood sugar levels. It's essential for people with Type 1 diabetes and some with Type 2.",
        "statins": "Statins are medications that help lower cholesterol levels in the blood, reducing the risk of heart disease and stroke."
    },
    "procedures": {
        "blood test": "Blood tests can check for various conditions, monitor organ function, and assess overall health. Common types include CBC, metabolic panels, and lipid profiles.",
        "x-ray": "X-rays use radiation to create images of bones and some soft tissues. They're commonly used to diagnose fractures, pneumonia, and other conditions.",
        "mri": "MRI (Magnetic Resonance Imaging) uses magnetic fields and radio waves to create detailed images of organs and tissues.",
        "ct scan": "CT scans use X-rays and computer technology to create cross-sectional images of the body, useful for diagnosing various conditions."
    }
}

def search_medical_kb(query: str) -> str:
    """Search the medical knowledge base for relevant information"""
    query_lower = query.lower()
    relevant_info = []
    
    for category, items in MEDICAL_KB.items():
        for key, value in items.items():
            if query_lower in key.lower() or query_lower in value.lower():
                relevant_info.append(f"{key.title()}: {value}")
    
    if relevant_info:
        return "\n\n".join(relevant_info[:3])  # Limit to 3 most relevant
    return ""

async def generate_medical_response_with_gemini(user_message: str, user_role: str, user_specialty: str, medical_context: str = "", rotator=None) -> str:
    """Generate a medical response using Gemini AI for intelligent, contextual responses"""
    try:        
        # Get API key from rotator
        api_key = rotator.get_key() if rotator else None
        if not api_key:
            logger.warning("No Gemini API key available, using fallback response")
            return generate_medical_response_fallback(user_message, user_role, user_specialty, medical_context)
        
        # Configure Gemini
        client = genai.Client(api_key=api_key)
        
        # Build context-aware prompt
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

        # Generate response
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        
        if response.text:
            # Add medical disclaimer if not already present
            if "disclaimer" not in response.text.lower() and "consult" not in response.text.lower():
                response.text += "\n\n⚠️ **Important Disclaimer:** This information is for educational purposes only and should not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals."
            
            return response.text
        
        # Fallback if Gemini fails
        logger.warning("Gemini response generation failed, using fallback")
        return generate_medical_response_fallback(user_message, user_role, user_specialty, medical_context)
        
    except Exception as e:
        logger.warning(f"Gemini medical response generation failed: {e}, using fallback")
        return generate_medical_response_fallback(user_message, user_role, user_specialty, medical_context)

def generate_medical_response_fallback(user_message: str, user_role: str, user_specialty: str, medical_context: str = "") -> str:
    """Fallback medical response generator using local knowledge base"""
    
    # Search medical knowledge base
    kb_info = search_medical_kb(user_message)
    
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

def generate_medical_response(user_message: str, user_role: str, user_specialty: str, medical_context: str = "") -> str:
    """Legacy function - now calls the fallback generator"""
    return generate_medical_response_fallback(user_message, user_role, user_specialty, medical_context)

@app.get("/", response_class=HTMLResponse)
async def get_medical_chatbot():
    """Serve the medical chatbot UI"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Medical chatbot UI not found")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Handle chat messages and generate medical responses"""
    start_time = time.time()
    
    try:
        logger.info(f"Chat request from user {request.user_id} in session {request.session_id}")
        logger.info(f"Message: {request.message[:100]}...")  # Log first 100 chars of message
        
        # Get or create user profile
        user_profile = memory_system.get_user(request.user_id)
        if not user_profile:
            memory_system.create_user(request.user_id, request.user_role or "Anonymous")
            if request.user_specialty:
                memory_system.get_user(request.user_id).set_preference("specialty", request.user_specialty)
        
        # Get or create session
        session = memory_system.get_session(request.session_id)
        if not session:
            session_id = memory_system.create_session(request.user_id, request.title or "New Chat")
            session = memory_system.get_session(session_id)
            logger.info(f"Created new session: {session_id}")
        
        # Get medical context from memory
        medical_context = history_manager.get_conversation_context(
            request.user_id, 
            request.session_id, 
            request.message
        )
        
        # Generate response using Gemini AI
        logger.info(f"Generating medical response using Gemini AI for user {request.user_id}")
        response = await generate_medical_response_with_gemini(
            request.message,
            request.user_role or "Medical Professional",
            request.user_specialty or "",
            medical_context,
            gemini_rotator
        )
        logger.info(f"Gemini response generated successfully, length: {len(response)} characters")
        
        # Process and store the exchange
        try:
            await history_manager.process_medical_exchange(
                request.user_id,
                request.session_id,
                request.message,
                response,
                gemini_rotator,
                nvidia_rotator
            )
        except Exception as e:
            logger.warning(f"Failed to process medical exchange: {e}")
            # Continue without storing if there's an error
        
        # Calculate response time
        response_time = time.time() - start_time
        
        logger.info(f"Generated response in {response_time:.2f}s for user {request.user_id}")
        logger.info(f"Response length: {len(response)} characters")
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            medical_context=medical_context if medical_context else None
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        logger.error(f"Request data: {request.dict()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/users")
async def create_user_profile(request: UserProfileRequest):
    """Create or update user profile"""
    try:
        user = memory_system.create_user(request.user_id, request.name)
        user.set_preference("role", request.role)
        if request.specialty:
            user.set_preference("specialty", request.specialty)
        
        return {"message": "User profile created successfully", "user_id": request.user_id}
    except Exception as e:
        logger.error(f"Error creating user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile and sessions"""
    try:
        user = memory_system.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        sessions = memory_system.get_user_sessions(user_id)
        
        return {
            "user": {
                "id": user.user_id,
                "name": user.name,
                "role": user.preferences.get("role", "Unknown"),
                "specialty": user.preferences.get("specialty", ""),
                "created_at": user.created_at,
                "last_seen": user.last_seen
            },
            "sessions": [
                {
                    "id": session.session_id,
                    "title": session.title,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "message_count": len(session.messages)
                }
                for session in sessions
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions")
async def create_chat_session(request: SessionRequest):
    """Create a new chat session"""
    try:
        session_id = memory_system.create_session(request.user_id, request.title or "New Chat")
        return {"session_id": session_id, "message": "Session created successfully"}
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """Get chat session details and messages"""
    try:
        session = memory_system.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "title": session.title,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "messages": session.messages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session"""
    try:
        memory_system.delete_session(session_id)
        return {"message": "Session deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "components": {
            "memory_system": "operational",
            "embedding_client": "operational" if embedding_client.is_available() else "fallback_mode",
            "api_rotator": "operational",
            "gemini_keys_available": len([k for k in gemini_rotator.keys if k]) > 0,
            "nvidia_keys_available": len([k for k in nvidia_rotator.keys if k]) > 0
        }
    }

@app.get("/api/info")
async def get_api_info():
    """Get API information and capabilities"""
    return {
        "name": "Medical AI Assistant",
        "version": "1.0.0",
        "description": "AI-powered medical chatbot with memory and context awareness",
        "features": [
            "Multi-user support with profiles",
            "Chat session management",
            "Medical context memory",
            "API key rotation",
            "Embedding-based similarity search",
            "Medical knowledge base integration"
        ],
        "endpoints": [
            "POST /chat - Send chat message",
            "POST /users - Create user profile",
            "GET /users/{user_id} - Get user profile and sessions",
            "POST /sessions - Create chat session",
            "GET /sessions/{session_id} - Get session details",
            "DELETE /sessions/{session_id} - Delete session",
            "GET /health - Health check",
            "GET /api/info - API information"
        ]
    }

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("🚀 Starting Medical AI Assistant...")
    
    # Check system resources
    try:
        import psutil
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        logger.info(f"System Resources - RAM: {memory.percent}%, CPU: {cpu}%")
        
        if memory.percent > 85:
            logger.warning("⚠️ High RAM usage detected!")
        if cpu > 90:
            logger.warning("⚠️ High CPU usage detected!")
    except ImportError:
        logger.info("psutil not available, skipping system resource check")
    
    # Check API keys
    gemini_keys = len([k for k in gemini_rotator.keys if k])
    if gemini_keys == 0:
        logger.warning("⚠️ No Gemini API keys found! Set GEMINI_API_1, GEMINI_API_2, etc. environment variables.")
    else:
        logger.info(f"✅ {gemini_keys} Gemini API keys available")
    
    nvidia_keys = len([k for k in nvidia_rotator.keys if k])
    if nvidia_keys == 0:
        logger.warning("⚠️ No NVIDIA API keys found! Set NVIDIA_API_1, NVIDIA_API_2, etc. environment variables.")
    else:
        logger.info(f"✅ {nvidia_keys} NVIDIA API keys available")
    
    # Check embedding client
    if embedding_client.is_available():
        logger.info("✅ Embedding model loaded successfully")
    else:
        logger.info("⚠️ Using fallback embedding mode")
    
    logger.info("✅ Medical AI Assistant startup complete")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Medical AI Assistant...")

if __name__ == "__main__":
    logger.info("Starting Medical AI Assistant server...")
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000, 
            log_level="info",
            reload=True
        )
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        exit(1)