# Backend Service

A FastAPI-based backend service for the Medical Diagnosis System.

## Technology Stack
- FastAPI - Web framework
- Uvicorn - ASGI server
- Python 3.13
- Docker (optional)

## Development Setup

### Prerequisites
- Python 3.13 or higher
- pip package manager
- Docker (optional, for containerized deployment)

### Local Development Setup

1. **Navigate to Backend Directory**
```bash
cd backend
```

2. **Create Virtual Environment**
```bash
python -m venv .venv
```

3. **Activate Virtual Environment**

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

4. **Install Dependencies**
```bash
pip install -r requirements.txt
```

5. **Configure Environment Variables**
```bash
cp .env.example .env
# Edit .env file with required values
```

### VSCode Configuration

1. Open `main.py`
2. Select Python Interpreter:
   - Click Python version in bottom right
   - Either:
     - Select `.venv` from the list, or
     - Choose "Enter interpreter path" and input `./backend/.venv/bin/python`

## Project Structure
```
backend/
├── .venv/                 # Virtual environment
├── app/                   # Application code
│   ├── main.py           # Entry point
│   ├── core/             # Core functionality
│   └── utils/            # Utility functions
├── .env.example          # Environment template
├── dockerfile            # Docker configuration
├── README.md
└── requirements.txt      # Python dependencies
```

## Running the Service

### Local Development
From the backend directory:
```bash
uvicorn app.main:app --reload
```
The service will be available at `http://localhost:8000`

### Docker Deployment
From the project root:
```bash
docker compose up --build
```

## API Documentation
When the service is running:
- OpenAPI UI: `http://localhost:8000/docs`
- ReDoc UI: `http://localhost:8000/redoc`

## Environment Variables
Required environment variables (must be set in `.env`):
- `has_been_copied`: Verification flag for environment setup
