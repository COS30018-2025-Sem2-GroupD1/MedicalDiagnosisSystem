---
title: Medical Diagnosis System
emoji: 🏥
colorFrom: yellow
colorTo: green
sdk: docker
pinned: false
license: mit
short_description: Group project for uni work
python_version: 3.11
app_port: 7860
---

# Medical AI Assistant

AI-powered medical chatbot with patient-centric memory, MongoDB persistence, and a fast, modern UI.

## 🚀 Key Features

- Patient-centric RAG memory
  - Short-term: last 3 QA summaries in in-memory LRU (fast context)
  - Long-term: last 20 QA summaries per patient persisted in MongoDB (continuity)
- Chat history persistence per session in MongoDB
- Patient/Doctor context saved on all messages and summaries
- Patient search typeahead (name or ID) with instant session hydration
- Doctor dropdown with built‑in "Create doctor user..." flow
- Modern UI: sidebar sessions, modals (doctor, settings, patient profile), dark/light mode, mobile-friendly
- Model integration: Gemini responses, NVIDIA summariser fallback via key rotators

## 🏗️ Architecture (high-level)

### Medical Features
- **Medical Knowledge Base**: Built-in medical information for common symptoms,
conditions, and medications
- **Context Awareness**: Remembers previous conversations and provides relevant medical
context
- **Role-Based Responses**: Tailored responses based on user's medical role and specialty
- **Medical Disclaimers**: Appropriate warnings and disclaimers for medical information
- **Export Functionality**: Export chat sessions for medical records or educational
purposes

Backend (FastAPI):
- `src/core/memory/memory.py`: LRU short‑term memory + sessions
- `src/core/memory/history.py`: builds context; writes memory/messages to Mongo
- `src/data/`: Mongo helpers (modularized)
  - `connection.py`: Mongo connection + collection names
  - `session/operations.py`: chat sessions (ensure/list/delete/etc.)
  - `message/operations.py`: chat messages (save/list)
  - `patient/operations.py`: patients (get/create/update/search)
  - `user/operations.py`: accounts/doctors (create/search/list)
  - `medical/operations.py`: medical records + memory summaries
  - `utils.py`: generic helpers (indexing, backups)
- `src/api/routes/`: `chat`, `session`, `user` (patients), `system`, `static`

Frontend (static):
- `static/index.html`, `static/css/styles.css`
- `static/js/app.js` (or modularized under `static/js/ui/*` and `static/js/chat/*` — see `UI_SETUP.md`)

## 🛠️ Quick Start

### Prerequisites
- Python 3.11+
- pip

### Setup
1. Clone and install
```bash
git clone https://huggingface.co/spaces/MedAI-COS30018/MedicalDiagnosisSystem
cd MedAI
pip install -r requirements.txt
```
2. Configure environment
```bash
# Create .env
echo "GEMINI_API_1=your_gemini_api_key_1" > .env
echo "NVIDIA_API_1=your_nvidia_api_key_1" >> .env
# MongoDB (required)
echo "MONGO_USER=your_mongodb_connection_string" >> .env
# Optional DB name (default: medicaldiagnosissystem)
# Optional DB name (default: medicaldiagnosissystem). Env var key: USER_DB
echo "USER_DB=medicaldiagnosissystem" >> .env
```
3. Run
```bash
python -m src.main
```
Helpful: [UI SETUP](https://huggingface.co/spaces/MedAI-COS30018/MedicalDiagnosisSystem/blob/main/UI_SETUP.md) | [SETUP GUIDE](https://huggingface.co/spaces/MedAI-COS30018/MedicalDiagnosisSystem/blob/main/SETUP_GUIDE.md)

## 🔧 Config
- `GEMINI_API_1..5`, `NVIDIA_API_1..5`
- `MONGO_USER`, `MONGO_DB`
- `LOG_LEVEL`, `PORT`
- Memory: 3 short‑term, 20 long‑term

## 📱 Usage
1. Select/create a doctor; set role/specialty.
2. Search patient by name/ID; select a result.
3. Start a new chat; ask your question.
4. Manage sessions in the sidebar (rename/delete from menu).
5. View patient profile and create/edit via modals/pages.

## 🔌 Endpoints (selected)
- `POST /chat` → `{ response, session_id, timestamp, medical_context? }`
- `POST /sessions` → `{ session_id }`
- `GET /patients/{patient_id}/sessions`
- `GET /sessions/{session_id}/messages`
- `DELETE /sessions/{session_id}` → deletes session (cache + Mongo) and its messages
- `GET /patients/search?q=term&limit=8`

## 🔒 Data & Privacy
- MongoDB persistence keyed by `patient_id` with `doctor_id` attribution
- UI localStorage for UX (doctor list, preferences, selected patient)
- Avoid logging PHI; secure Mongo credentials

## 🧪 Dev
```bash
pip install -r requirements.txt
python -m src.main   # run
pytest               # tests
black . && flake8    # format + lint
```

## 🧾 License & Disclaimer
- Apache 2.0 License (see [LICENSE](./LICENSE))
- Educational information only; not a substitute for professional medical advice
- Team D1 - COS30018, Swinburne University of Technology
