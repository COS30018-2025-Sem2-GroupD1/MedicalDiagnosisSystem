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

A sophisticated AI-powered medical chatbot system with ChatGPT-like UI, multi-user support, session management, and medical context awareness.

## 🚀 Features

### Core Functionality
- **AI-Powered Medical Chat**: Intelligent responses to medical questions using advanced language models
- **Multi-User Support**: Individual user profiles with role-based customization (Physician, Nurse, Medical Student, etc.)
- **Chat Session Management**: Multiple concurrent chat sessions per user with persistent history
- **Medical Context Memory**: LRU-based memory system that maintains conversation context and medical history
- **API Key Rotation**: Dynamic rotation of Gemini API keys for reliability and rate limit management

### User Interface
- **ChatGPT-like Design**: Familiar, intuitive interface optimized for medical professionals
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Dark/Light Theme**: Automatic theme switching with system preference detection
- **Real-time Chat**: Smooth, responsive chat experience with typing indicators
- **Session Management**: Easy navigation between different chat sessions

### Medical Features
- **Medical Knowledge Base**: Built-in medical information for common symptoms, conditions, and medications
- **Context Awareness**: Remembers previous conversations and provides relevant medical context
- **Role-Based Responses**: Tailored responses based on user's medical role and specialty
- **Medical Disclaimers**: Appropriate warnings and disclaimers for medical information
- **Export Functionality**: Export chat sessions for medical records or educational purposes

## 🏗️ Architecture

### Core Components
```
MedicalDiagnosisSystem/
├── app.py                 # FastAPI main application
├── memo/
│   ├── memory.py         # Enhanced LRU memory system
│   └── history.py        # Medical history manager
├── utils/
│   ├── rotator.py        # API key rotation system
│   ├── embeddings.py     # Embedding client with fallback
│   └── logger.py         # Structured logging
└── static/
    ├── index.html        # Main UI
    ├── styles.css        # Styling
    └── app.js           # Frontend logic
```

### Memory System
- **User Profiles**: Persistent user data with preferences and roles
- **Chat Sessions**: Individual conversation threads with message history
- **Medical Context**: QA summaries stored in LRU cache for quick retrieval
- **Semantic Search**: Embedding-based similarity search for relevant medical information

### API Integration
- **Gemini API**: Google's advanced language model for medical responses
- **Key Rotation**: Automatic rotation on rate limits or errors
- **Fallback Support**: Graceful degradation when external APIs are unavailable

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- pip package manager
- Modern web browser

### Setup
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MedicalDiagnosisSystem
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   # Create .env file
   echo "GEMINI_API_1=your_gemini_api_key_1" > .env
   echo "GEMINI_API_2=your_gemini_api_key_2" >> .env
   echo "GEMINI_API_3=your_gemini_api_key_3" >> .env
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the UI**
   Open your browser and navigate to `http://localhost:8000`

## 🔧 Configuration

### Environment Variables
- `GEMINI_API_1` through `GEMINI_API_5`: Gemini API keys for rotation
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `PORT`: Server port (default: 8000)

### Memory Settings
- **LRU Capacity**: Default 50 QA summaries per user
- **Max Sessions**: Default 20 sessions per user
- **Session Timeout**: Configurable session expiration

### Embedding Model
- **Default Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Fallback Mode**: Hash-based embeddings when model unavailable
- **GPU Support**: Optional CUDA acceleration for embeddings

## 📱 Usage

### Getting Started
1. **Access the Application**: Navigate to the provided URL
2. **Create User Profile**: Click on your profile to set name, role, and specialty
3. **Start New Chat**: Click "New Chat" to begin a conversation
4. **Ask Medical Questions**: Type your medical queries in natural language
5. **Manage Sessions**: Use the sidebar to switch between different chat sessions

### User Roles
- **Physician**: Full medical context with clinical guidance
- **Nurse**: Nursing-focused responses and care instructions
- **Medical Student**: Educational content with learning objectives
- **Healthcare Professional**: General medical information
- **Patient**: Educational content with appropriate disclaimers

### Features
- **Real-time Chat**: Instant responses with typing indicators
- **Session Export**: Download chat history as JSON files
- **Context Memory**: System remembers previous conversations
- **Medical Disclaimers**: Appropriate warnings for medical information
- **Responsive Design**: Works on all device sizes

## 🔒 Security & Privacy

### Data Protection
- **Local Storage**: User data stored locally in browser (no server persistence)
- **Session Isolation**: Users can only access their own data
- **No PII Storage**: Personal information not logged or stored
- **Medical Disclaimers**: Clear warnings about information limitations

### API Security
- **Key Rotation**: Automatic API key rotation for security
- **Rate Limiting**: Built-in protection against API abuse
- **Error Handling**: Graceful degradation on API failures

## 🧪 Development

### Local Development
```bash
# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
python app.py

# Run tests
pytest

# Format code
black .

# Lint code
flake8
```

### Project Structure
```
├── app.py              # Main FastAPI application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── memo/              # Memory and history management
│   ├── __init__.py
│   ├── memory.py      # Enhanced LRU memory system
│   └── history.py     # Medical history manager
├── utils/             # Utility modules
│   ├── __init__.py
│   ├── rotator.py     # API key rotation
│   ├── embeddings.py  # Embedding client
│   └── logger.py      # Logging utilities
└── static/            # Frontend assets
    ├── index.html     # Main HTML
    ├── styles.css     # CSS styling
    └── app.js        # JavaScript logic
```

### Adding New Features
1. **Backend**: Add new endpoints in `app.py`
2. **Memory**: Extend memory system in `memo/memory.py`
3. **Frontend**: Update UI components in `static/` files
4. **Testing**: Add tests for new functionality

## 🚀 Deployment

### Production Considerations
- **Environment Variables**: Secure API key management
- **HTTPS**: Enable SSL/TLS for production
- **Rate Limiting**: Implement request rate limiting
- **Monitoring**: Add health checks and logging
- **Database**: Consider persistent storage for production

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "app.py"]
```

### Cloud Deployment
- **AWS**: Deploy on EC2 or Lambda
- **Google Cloud**: Use Cloud Run or App Engine
- **Azure**: Deploy on App Service
- **Heroku**: Simple deployment with Procfile

## 📊 Performance

### Optimization Features
- **Lazy Loading**: Embedding models loaded on demand
- **LRU Caching**: Efficient memory management
- **API Rotation**: Load balancing across multiple API keys
- **Fallback Modes**: Graceful degradation on failures

### Monitoring
- **Health Checks**: `/health` endpoint for system status
- **Resource Usage**: CPU and memory monitoring
- **API Metrics**: Response times and success rates
- **Error Tracking**: Comprehensive error logging

## 🤝 Contributing

### Development Guidelines
1. **Code Style**: Follow PEP 8 and use Black formatter
2. **Testing**: Add tests for new features
3. **Documentation**: Update README and docstrings
4. **Security**: Follow security best practices
5. **Performance**: Consider performance implications

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

**Medical Information Disclaimer**: This application provides educational medical information only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals for medical decisions.

**AI Limitations**: While this system uses advanced AI technology, it has limitations and should not be relied upon for critical medical decisions.

## 🆘 Support

### Getting Help
- **Issues**: Report bugs via GitHub Issues
- **Documentation**: Check this README and code comments
- **Community**: Join discussions in GitHub Discussions

### Common Issues
- **API Keys**: Ensure Gemini API keys are properly set
- **Dependencies**: Verify all requirements are installed
- **Port Conflicts**: Check if port 8000 is available
- **Memory Issues**: Monitor system resources

---

**Built with ❤️ for the medical community**
