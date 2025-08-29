---
title: Medical Diagnosis System
emoji: 🏥
colorFrom: yellow
colorTo: green
sdk: docker
pinned: false
license: mit
short_description: Group project for uni work
python_version: 3.13
---

# Medical Diagnosis System

A FastAPI-based backend service for the Medical Diagnosis System.

## Technology Stack
- FastAPI - Web framework
- Uvicorn - ASGI server
- Python 3.13
- Google Gemini AI
- Docker & Docker Compose

## Development Setup

### Prerequisites
- Python 3.13 or higher
- pip package manager
- Docker & Docker Compose (for containerized deployment)
- Google API key for Gemini AI access

### Local Development Setup

1. **Create Virtual Environment**
```bash
python -m venv .venv
```

2. **Activate Virtual Environment**

Linux/MacOS:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```bash
.\.venv\Scripts\Activate.ps1
```

Fish Shell:
```bash
source .venv/bin/activate.fish
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Environment Variables**
```bash
cp .env.example .env
# Edit .env file with your Google API key
```

## Project Structure
```
MedicalDiagnosisSystem/
├── .venv/                  # Virtual environment
├── app/                    # Application code
│   ├── main.py             # Entry point
│   ├── api/                # API routes
│   │   ├── api_base.py     # Base router
│   │   ├── v1.py           # v1 API routes
│   │   └── routes/         # Route modules
│   └── utils/              # Utility functions
├── .env.example            # Environment template
├── dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose config
├── README.md
└── requirements.txt        # Python dependencies
```

## Running the Service

### Local Development
```bash
uvicorn app.main:app --reload
```
The service will be available at `http://localhost:8000`

### Docker Deployment
```bash
docker compose up --build
```
The service will be available at `http://localhost:7860`

## API Documentation
When the service is running:
- OpenAPI UI: `/docs`
- ReDoc UI: `/redoc`
- API Base: `/api`

## API Endpoints
- `/api/v1/chat` - Medical diagnosis chat interface
- `/api/v1/model` - Model information endpoints
- `/api/v1/retrieval` - Data retrieval endpoints

## Environment Variables
Required environment variables (must be set in `.env`):
- `has_been_copied`: Verification flag for environment setup
- `google_api_key`: Google API key for accessing Gemini AI services
