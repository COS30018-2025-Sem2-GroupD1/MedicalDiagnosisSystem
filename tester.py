#!/usr/bin/env python3
"""
Quick test to verify the medical chatbot fixes
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """Test basic system functionality"""
    print("🔍 Testing basic functionality...")
    
    try:
        # Test imports
        from memo.memory import MemoryLRU
        from memo.history import MedicalHistoryManager
        from utils.rotator import APIKeyRotator
        from utils.embeddings import create_embedding_client
        print("✅ All imports successful")
        
        # Test memory system
        memory = MemoryLRU()
        user = memory.create_user("test_user", "Dr. Test")
        user.set_preference("role", "Physician")
        print(f"✅ User created: {user.name}, Role: {user.role}")
        
        # Test session creation
        session_id = memory.create_session("test_user", "Test Chat")
        session = memory.get_session(session_id)
        print(f"✅ Session created: {session.title}")
        
        # Test API rotator
        rotator = APIKeyRotator("TEST_", max_slots=3)
        key = rotator.get_key()
        print(f"✅ API rotator working: {key}")
        
        # Test embedding client
        embedder = create_embedding_client("default", dimension=128)
        embeddings = embedder.embed(["test message"])
        print(f"✅ Embeddings working: {len(embeddings)} vectors")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_medical_response():
    """Test medical response generation"""
    print("\n🏥 Testing medical response generation...")
    
    try:
        # Import the function
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # We need to import the function from app.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("app", "app.py")
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
        
        # Test response generation
        response = app_module.generate_medical_response(
            "What is fever?",
            "Physician",
            "Emergency Medicine"
        )
        
        print(f"✅ Response generated: {len(response)} characters")
        print(f"Response preview: {response[:200]}...")
        
        # Test with different question
        response2 = app_module.generate_medical_response(
            "How to treat headache?",
            "Medical Student",
            "Neurology"
        )
        
        print(f"✅ Second response generated: {len(response2)} characters")
        print(f"Response preview: {response2[:200]}...")
        
        print("\n🎉 Medical response tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Medical response test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Medical AI Assistant - Fix Verification Test")
    print("=" * 60)
    
    success1 = test_basic_functionality()
    success2 = test_medical_response()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 All tests passed! The system should now work correctly.")
        print("\nTo start the system:")
        print("python3 start.py")
        print("\nThen open http://localhost:8000 in your browser")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        sys.exit(1)
