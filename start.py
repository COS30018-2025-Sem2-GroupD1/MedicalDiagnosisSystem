#!/usr/bin/env python3
"""
Medical AI Assistant - Startup Script
Simple script to start the medical chatbot system
Not needed for huggingface deployment
"""

import os
import sys

import uvicorn


def main():
	"""Start the Medical AI Assistant"""
	print("🚀 Medical AI Assistant")
	print("=" * 50)

	# Check if we're in the right directory
	if not os.path.exists("app.py"):
		print("❌ Error: app.py not found!")
		print("Please run this script from the MedicalDiagnosisSystem directory.")
		sys.exit(1)

	# Check for environment variables
	gemini_keys = []
	for i in range(1, 6):
		key = os.getenv(f"GEMINI_API_{i}")
		if key:
			gemini_keys.append(f"GEMINI_API_{i}")

	if not gemini_keys:
		print("⚠️  Warning: No Gemini API keys found!")
		print("Set GEMINI_API_1, GEMINI_API_2, etc. environment variables for full functionality.")
		print("The system will work with mock responses for demo purposes.")
	else:
		print(f"✅ Found {len(gemini_keys)} Gemini API keys")

	# Check for MongoDB environment variables
	mongo_user = os.getenv("MONGO_USER")
	user_db = os.getenv("USER_DB")
	
	if not mongo_user:
		print("❌ Error: MONGO_USER environment variable not found!")
		print("Set MONGO_USER environment variable for database connectivity.")
		sys.exit(1)
	
	if not user_db:
		print("❌ Error: USER_DB environment variable not found!")
		print("Set USER_DB environment variable for database connectivity.")
		sys.exit(1)
	
	print("✅ MongoDB environment variables found")

	print("\n📱 Starting Medical AI Assistant...")
	print("🌐 Web UI will be available at: https://medai-cos30018-medicaldiagnosissystem.hf.space")
	print("📚 API documentation at: https://medai-cos30018-medicaldiagnosissystem.hf.space/docs")
	print("🔍 Health check at: https://medai-cos30018-medicaldiagnosissystem.hf.space/health")
	print("\nPress Ctrl+C to stop the server")
	print("=" * 50)

	# Start the server
	uvicorn.run(
		"src.main:app",
		host="0.0.0.0",
		port=7860,
		log_level="info",
		reload=True
	)

if __name__ == "__main__":
	main()
