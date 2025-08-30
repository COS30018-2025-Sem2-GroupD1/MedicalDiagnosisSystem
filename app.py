# app.py
import os
import faiss
import numpy as np
import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from google import genai
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

# ✅ Enable Logging for Debugging
import logging
# —————— Silence Noisy Loggers ——————
for name in [
    "uvicorn.error", "uvicorn.access",
    "fastapi", "starlette",
    "pymongo", "gridfs",
    "sentence_transformers", "faiss",
    "google", "google.auth",
]:
    logging.getLogger(name).setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(name)s — %(levelname)s — %(message)s", force=True) # Change INFO to DEBUG for full-ctx JSON loader
logger = logging.getLogger("medical-chatbot")
logger.setLevel(logging.DEBUG)

# Debug Start
logger.info("🚀 Starting Medical Chatbot API...")

# ✅ Environment Variables
# mongo_uri = os.getenv("MONGO_URI")           # TODO: Create MongoDB cluster
gemini_flash_api_key = os.getenv("GEMINI_API")
# Validate environment endpoint
if not all([gemini_flash_api_key, mongo_uri]):
    raise ValueError("❌ Missing API keys! Set them in Hugging Face Secrets.")


# ✅ Monitor Resources Before Startup
import psutil
def check_system_resources():
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)
    disk = psutil.disk_usage("/")
    # Defines log info messages
    logger.info(f"[System] 🔍 System Resources - RAM: {memory.percent}%, CPU: {cpu}%, Disk: {disk.percent}%")
    if memory.percent > 85:
        logger.warning("⚠️ High RAM usage detected!")
    if cpu > 90:
        logger.warning("⚠️ High CPU usage detected!")
    if disk.percent > 90:
        logger.warning("⚠️ High Disk usage detected!")
check_system_resources()

# ✅ Reduce Memory usage with optimizers
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ✅ Initialize FastAPI app
app = FastAPI(title="Medical Chatbot API", version="0.1.0")
memory = MemoryManager()

from fastapi.middleware.cors import CORSMiddleware # Bypassing CORS origin

# Add the CORS middleware:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # or your origin here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Use Lazy Loading for FAISS Index
index = None  # Delay FAISS Index loading until first query

# ✅ Load SentenceTransformer Model (Quantized/Halved)
logger.info("[Embedder] 📥 Loading SentenceTransformer Model...")
MODEL_CACHE_DIR = "/app/model_cache"
try:
    embedding_model = SentenceTransformer(MODEL_CACHE_DIR, device="cpu")
    embedding_model = embedding_model.half()  # Reduce memory
    logger.info("✅ Model Loaded Successfully.")
except Exception as e:
    logger.error(f"❌ Model Loading Failed: {e}")
    exit(1)

# Cache in-memory vectors (optional — useful for <10k rows)
SYMPTOM_VECTORS = None
SYMPTOM_DOCS = None

# ✅ Setup MongoDB Connection
# QA data
# client = MongoClient(mongo_uri) # REACTIVATE after MongoDB creation

# ✅ Load Index (Lazy Load) with gridfs
import gridfs


# ✅ RAG
def retrieve_medical_info(query, k=5, min_sim=0.9): # Min similarity between query and kb is to be 80%
    '''TODO: Implement your RAG pipeline'''


# ✅ Gemini Flash API Call
def _gemini(prompt, model, temperature=0.7):
    client_genai = genai.Client(api_key=gemini_flash_api_key)
    try:
        response = client_genai.models.generate_content(model=model, contents=prompt)
        return response.text
    except Exception as e:
        logger.error(f"[LLM] ❌ Error calling Gemini API: {e}")
        return "Error generating response from Gemini."

# ✅ Chatbot Class
class RAGMedicalChatbot:
    def __init__(self, model_name, retrieve_function):
        self.model_name = model_name
        self.retrieve = retrieve_function

    def chat() -> str:
        # Build prompt 
        parts = ["You are a medical chatbot, designed to answer medical questions."]
        parts.append("Please format your answer using MarkDown.")
        parts.append("**Bold for titles**, *italic for emphasis*, and clear headings.")
        #...
        response = _gemini(prompt, model=self.model_name, temperature=0.7)
         # Store exchange + chunking
        if user_id:
            memory.add_exchange(user_id, user_query, response, lang=lang)
        logger.info(f"[LLM] Response on `prompt`: {response.strip()}") # Debug out base response
        return response.strip()

# ✅ Initialize Chatbot
chatbot = RAGMedicalChatbot(model_name="gemini-2.5-flash", retrieve_function=retrieve_medical_info)

# ✅ Chat Endpoint
@app.post("/chat")
async def chat_endpoint(req: Request):
    body = await req.json()
    user_id = body.get("user_id", "anonymous")
    #...
    start = time.time()
    # Final
    return JSONResponse({"response": f"{answer}\n\n(Response time: {elapsed:.2f}s)"})


# ✅ Run Uvicorn
if __name__ == "__main__":
    logger.info("[System] ✅ Starting FastAPI Server...")
    try:
        uvicorn.run(app, host="0.0.0.0", port=7860, log_level="debug")
    except Exception as e:
        logger.error(f"❌ Server Startup Failed: {e}")
        exit(1)
