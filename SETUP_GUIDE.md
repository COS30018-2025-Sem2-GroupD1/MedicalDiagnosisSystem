# Setup Guide

This guide provides instructions on how to set up and run the Medical Diagnosis System for both local development and using Docker.

## Prerequisites

Before you begin, ensure you have the following installed:

- Git
- Python 3.11 or higher
- pip (Python package installer)
- Docker and Docker Compose

## Environment Variable Setup

The application is configured using a `.env` file in the project's root directory. This file is required for both local and Docker setups, but the values will differ.

First, create the file:

```bash
touch .env
```

Next, add the following variables to the file. Explanations for each setup type are provided below.

```ini
# --- AI Model API Keys ---
# Add at least one key for each service. The application will rotate through them.
GEMINI_API_KEY_1=your_gemini_api_key
NVIDIA_API_KEY_1=your_nvidia_api_key

# --- MongoDB Connection ---
# Use the appropriate URI for your setup (see examples below)
MONGO_URI=your_mongodb_connection_string
DB_NAME=medicaldiagnosissystem

# --- Application Settings ---
LOG_LEVEL=INFO
PORT=7860
```

### MongoDB URI Examples

- **For Docker Setup (Recommended):** The `docker-compose.yml` file includes a MongoDB service. Use the following URI to connect the application container to the database container:
	```ini
	MONGO_URI=mongodb://root:example@mongo:27017/
	```

- **For Local Development:** You must run your own MongoDB instance. If it is running locally on the default port without authentication, your URI would be:
	```ini
	MONGO_URI=mongodb://localhost:27017/
	```

## Docker Setup (Recommended)

This method runs the application and a MongoDB database in isolated containers, which is the quickest way to get started.

### 1. Configure Environment
Ensure your `.env` file is present in the project root and contains the correct `MONGO_URI` for a Docker environment.

### 2. Build and Run Containers
From the project's root directory, run the following command. This will build the Docker images and start the application and database services.

```bash
docker-compose up --build
```

To run the containers in the background (detached mode), add the `-d` flag:

```bash
docker-compose up --build -d
```

The application will now be accessible at `http://localhost:7860`.

### 3. Stopping the Application
To stop and remove the containers, use:
```bash
docker-compose down
```

## Local Development Setup

This method requires you to run a MongoDB instance on your local machine or have one accessible on your network.

### 1. Clone the Repository
```bash
git clone https://github.com/COS30018-2025-Sem2-GroupD1/MedicalDiagnosisSystem.git
cd MedicalDiagnosisSystem
```

### 2. Configure Environment
Ensure your `.env` file is present and contains the correct `MONGO_URI` that points to your externally-managed MongoDB instance.

### 3. Create and Activate a Virtual Environment
It is highly recommended to use a virtual environment to isolate project dependencies.

First, create the environment in the project's root directory:
```bash
python -m venv .venv
```
Next, activate it. The command differs depending on your operating system:

- **On Linux or macOS:**
	```bash
	source .venv/bin/activate
	```

- **On Windows (using PowerShell):**
	```powershell
	.\.venv\Scripts\Activate.ps1
	```

- **On Windows (using Command Prompt):**
	```cmd
	.\.venv\Scripts\activate.bat
	```

Your shell prompt should now indicate that you are in the `.venv` environment.

### 4. Install Dependencies
Install the required Python packages into your active virtual environment:

```bash
# Install all requirements for running
pip install -r requirements.txt

# Install development-specific dependencies
pip install -r requirements-dev.txt
```

### 5. Run the Application
To run the application for development, use `uvicorn`. This will start a local server that automatically reloads when you make code changes.

```bash
uvicorn src.main:app --reload
```
The application will be accessible at `http://localhost:7860`.

## Development Workflow

### Running Tests
To run the test suite, use `pytest`:

```bash
pytest
```
