# Medical AI Assistant - Setup Guide

## 🎯 What We've Built

A comprehensive medical chatbot system with:

1. **ChatGPT-like UI** - Modern, responsive web interface
2. **Multi-user Support** - Individual profiles and chat sessions
3. **Medical Context Memory** - LRU-based memory system
4. **API Key Rotation** - Dynamic Gemini API management
5. **Fallback Systems** - Graceful degradation when services unavailable

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables (Optional)
```bash
# For full Gemini AI functionality
export GEMINI_API_1="your_api_key_1"
export GEMINI_API_2="your_api_key_2"
...
export GEMINI_API_5="your_api_key_5"
```

### 3. Start the System
```bash
python3 start.py
```

### 4. Access the UI
Open your browser and go to: **http://localhost:8000**

## 🏗️ System Architecture

### Core Components
- **`app.py`** - FastAPI main application with all endpoints
- **`memo/memory.py`** - Enhanced LRU memory with user/session management
- **`memo/history.py`** - Medical history manager with context awareness
- **`utils/rotator.py`** - API key rotation for reliability
- **`utils/embeddings.py`** - Embedding client with fallback support
- **`static/`** - Complete web UI (HTML, CSS, JavaScript)

### Key Features
- **User Management**: Create profiles with medical roles and specialties
- **Session Management**: Multiple concurrent chat sessions per user
- **Medical Memory**: Context-aware responses using conversation history
- **API Integration**: Gemini AI with automatic key rotation
- **Responsive UI**: Works on desktop, tablet, and mobile

## 📱 Using the System

### First Time Setup
1. **Access the UI** at http://localhost:8000
2. **Click your profile** to set name, role, and specialty
3. **Start a new chat** to begin your first conversation
4. **Ask medical questions** in natural language

### User Roles Available
- **Physician** - Full medical context and clinical guidance
- **Nurse** - Nursing-focused responses and care instructions
- **Medical Student** - Educational content with learning objectives
- **Healthcare Professional** - General medical information
- **Patient** - Educational content with appropriate disclaimers

### Features
- **Real-time Chat**: Instant responses with typing indicators
- **Session Export**: Download chat history as JSON files
- **Context Memory**: System remembers previous conversations
- **Medical Disclaimers**: Appropriate warnings for medical information
- **Dark/Light Theme**: Automatic theme switching

## 🔧 Configuration Options

### Environment Variables
```bash
# Required for full functionality
GEMINI_API_1=your_key_1
GEMINI_API_2=your_key_2
GEMINI_API_3=your_key_3

# Optional
LOG_LEVEL=INFO
PORT=8000
```

### Memory Settings
- **LRU Capacity**: 50 QA summaries per user (configurable)
- **Max Sessions**: 20 sessions per user (configurable)
- **Session Timeout**: Configurable session expiration

### Embedding Model
- **Default**: `all-MiniLM-L6-v2` (384 dimensions)
- **Fallback**: Hash-based embeddings when model unavailable
- **GPU Support**: Optional CUDA acceleration

## 🧪 Testing the System

### Run System Tests
```bash
python3 test_system.py
```

### Test Individual Components
```bash
# Test memory system
python3 -c "from memo.memory import MemoryLRU; m = MemoryLRU(); print('✅ Memory system works')"

# Test API rotator
python3 -c "from utils.rotator import APIKeyRotator; r = APIKeyRotator('TEST_'); print('✅ Rotator works')"

# Test embeddings
python3 -c "from utils.embeddings import create_embedding_client; c = create_embedding_client(); print('✅ Embeddings work')"
```

## 🌐 API Endpoints

### Core Endpoints
- **`GET /`** - Main web UI
- **`POST /chat`** - Send chat messages
- **`POST /users`** - Create user profiles
- **`GET /users/{user_id}`** - Get user data and sessions
- **`POST /sessions`** - Create chat sessions
- **`GET /sessions/{session_id}`** - Get session details
- **`DELETE /sessions/{session_id}`** - Delete sessions

### Utility Endpoints
- **`GET /health`** - System health check
- **`GET /api/info`** - API information and capabilities
- **`GET /docs`** - Interactive API documentation (Swagger UI)

## 🔒 Security & Privacy

### Data Protection
- **Local Storage**: User data stored in browser (no server persistence)
- **Session Isolation**: Users can only access their own data
- **No PII Storage**: Personal information not logged or stored
- **Medical Disclaimers**: Clear warnings about information limitations

### API Security
- **Key Rotation**: Automatic API key rotation for security
- **Rate Limiting**: Built-in protection against API abuse
- **Error Handling**: Graceful degradation on API failures

## 🚀 Deployment

### Local Development
```bash
python3 start.py
```

### Production Deployment
```bash
# Set production environment variables
export PRODUCTION=true
export LOG_LEVEL=WARNING

# Start with production settings
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment
```bash
# Build and run with Docker
docker build -t medical-ai-assistant .
docker run -p 8000:8000 medical-ai-assistant
```

## 🐛 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure you're in the right directory
cd MedicalDiagnosisSystem

# Install dependencies
pip install -r requirements.txt

# Check Python version (3.8+ required)
python3 --version
```

#### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process or use a different port
export PORT=8001
python3 start.py
```

#### API Key Issues
```bash
# Check environment variables
echo $GEMINI_API_1

# Set them if missing
export GEMINI_API_1="your_key_here"
```

#### Memory Issues
```bash
# Check system resources
free -h
top

# Reduce memory usage in app.py
# Set smaller capacity values in MemoryLRU
```

### Getting Help
- **Check logs**: Look for error messages in the console
- **Test components**: Run `python3 test_system.py`
- **Check health**: Visit http://localhost:8000/health
- **API docs**: Visit http://localhost:8000/docs

## 🔮 Future Enhancements

### Planned Features
- **Database Integration**: Persistent storage for production use
- **Advanced RAG**: Vector database for medical knowledge
- **Multi-language Support**: Internationalization
- **Voice Interface**: Speech-to-text and text-to-speech
- **Mobile App**: Native iOS/Android applications
- **Analytics Dashboard**: Usage statistics and insights

### Customization
- **Medical Knowledge Base**: Add your own medical content
- **Response Templates**: Customize AI response styles
- **Integration APIs**: Connect with existing medical systems
- **Custom Models**: Use different AI models or fine-tuned versions

## 📚 Additional Resources

### Documentation
- **FastAPI**: https://fastapi.tiangolo.com/
- **Uvicorn**: https://www.uvicorn.org/
- **Google Gemini**: https://ai.google.dev/
- **Sentence Transformers**: https://www.sbert.net/

### Support
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and share experiences
- **Contributing**: Submit pull requests and improvements

---

**🎉 Your Medical AI Assistant is ready to use!**

Start with `python3 start.py` and enjoy your intelligent medical chatbot!
