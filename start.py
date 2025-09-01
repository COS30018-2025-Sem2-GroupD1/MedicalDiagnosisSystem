#!/usr/bin/env python3
"""
Medical AI Assistant - Startup Script
Simple script to start the medical chatbot system
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
    
    print("\n📱 Starting Medical AI Assistant...")
    print("🌐 Web UI will be available at: http://localhost:8000")
    print("📚 API documentation at: http://localhost:8000/docs")
    print("🔍 Health check at: http://localhost:8000/health")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Start the server
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
