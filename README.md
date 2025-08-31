---
title: Medical Diagnosis System
emoji: 🏥
colorFrom: yellow
colorTo: green
sdk: docker
pinned: false
license: mit
short_description: Group project for uni work
python_version: 3.10
app_port: 7860
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

a. Linux/MacOS (bash/zsh):
```bash
source .venv/bin/activate
```
b. Windows PowerShell:
```bash
.\.venv\Scripts\Activate.ps1
```
c. Fish Shell:
```bash
source .venv/bin/activate.fish
```

3. **Check the environment before continuing**
```bash
echo $VIRTUAL_ENV # It should return your .venv path
which python # It should also return your .venv path
which pip # Same as the above
```
If one of any is not working, a potential solution is to append `sudo` when creating virtual environment:
```bash
sudo python -m venv .venv
source .venv/bin/activate
# check with the commands above
```
Since the environment is installed using super user, following commands to install the required libraries will also needed to be under super user, and because of that, it can install locally on your device instead of within the environment.
To ensure that it doesn't happen, run this command to change the ownership to your username
```bash
sudo chown -R your_username:your_username path/to/virtuaelenv/
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
├── main.py             # Entry point
├── api/                # API routes
│   ├── api_base.py     # Base router
│   ├── v1.py           # v1 API routes
│   └── routes/         # Route modules
└── utils/              # Utility functions
├── .env.example            # Environment template
├── dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose config
├── README.md
└── requirements.txt        # Python dependencies
```

## Running the Service

### Local Development
```bash
uvicorn app:app --reload
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
