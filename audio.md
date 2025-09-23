# Audio Transcription Feature

This document describes the audio transcription functionality integrated into the Medical AI Assistant.

## Overview

The audio transcription feature allows users to record voice input using their microphone and automatically transcribe it to text using NVIDIA's Riva API. The transcribed text is then inserted into the chat input field for editing before submission.

## Features

- **Voice Recording**: Click and hold the microphone button to record audio
- **Real-time Feedback**: Visual indicators show recording and processing states
- **Automatic Transcription**: Audio is automatically sent to NVIDIA Riva API for transcription
- **Text Editing**: Transcribed text is inserted into the chat input for review and editing
- **Error Handling**: Graceful error handling with user-friendly messages

## Technical Implementation

### Backend Components

1. **Audio Transcription Service** (`src/services/audio_transcription.py`)
   - Handles communication with NVIDIA Riva API
   - Supports WAV, OPUS, and FLAC audio formats
   - Includes audio format validation
   - Provides both file and bytes-based transcription

2. **Audio API Routes** (`src/api/routes/audio.py`)
   - `/audio/transcribe` - POST endpoint for audio transcription
   - `/audio/supported-formats` - GET endpoint for supported formats
   - `/audio/health` - GET endpoint for service health check

### Frontend Components

1. **Audio Recorder** (`static/js/audio/recorder.js`)
   - `AudioRecorder` class for handling audio recording
   - `AudioRecordingUI` class for UI management
   - MediaRecorder API integration
   - Real-time visual feedback

2. **CSS Styles** (`static/css/styles.css`)
   - Recording state indicators
   - Visual feedback for transcribed text
   - Responsive design for mobile devices

## API Configuration

### NVIDIA Riva API Setup

1. **API Keys**: Set environment variables for NVIDIA API keys:
   ```bash
   export NVIDIA_API_1="your_api_key_1"
   export NVIDIA_API_2="your_api_key_2"
   # ... up to NVIDIA_API_5
   ```

2. **Function ID**: The service uses the Whisper model function ID:
   ```
   b702f636-f60c-4a3d-a6f4-f3568c13bd7d
   ```

3. **Server Endpoint**: 
   ```
   grpc.nvcf.nvidia.com:443
   ```

### Supported Audio Formats

- **WAV**: 16-bit, mono, 16kHz recommended
- **OPUS**: WebM container with Opus codec
- **FLAC**: Lossless compression

## Usage

### For Users

1. **Start Recording**: Click and hold the microphone button
2. **Speak**: Record your voice input (up to 30 seconds)
3. **Stop Recording**: Release the button to stop recording
4. **Review Text**: Transcribed text appears in the chat input
5. **Edit if Needed**: Modify the text before sending
6. **Send Message**: Submit the message as usual

### For Developers

1. **Install Dependencies**:
   ```bash
   pip install nvidia-riva-client
   ```

2. **Test the Service**:
   ```bash
   python test_audio_transcription.py
   ```

3. **Start the Server**:
   ```bash
   python start.py
   ```

## Browser Compatibility

- **Chrome/Chromium**: Full support
- **Firefox**: Full support
- **Safari**: Full support (iOS 14.3+)
- **Edge**: Full support

## Security Considerations

- **Microphone Access**: Requires user permission
- **Audio Data**: Transmitted securely to NVIDIA API
- **No Local Storage**: Audio data is not stored locally
- **API Key Rotation**: Automatic key rotation for reliability

## Troubleshooting

### Common Issues

1. **Microphone Access Denied**
   - Ensure browser has microphone permissions
   - Check browser settings for site permissions

2. **Transcription Fails**
   - Verify NVIDIA API keys are set correctly
   - Check network connectivity
   - Ensure audio format is supported

3. **No Audio Detected**
   - Check microphone is working
   - Ensure audio levels are adequate
   - Try speaking closer to the microphone

### Debug Mode

Enable debug logging by opening browser developer tools and checking the console for detailed error messages.

## Future Enhancements

- **Language Selection**: Support for multiple languages
- **Real-time Transcription**: Live transcription during recording
- **Audio Quality Settings**: Configurable audio parameters
- **Offline Support**: Local transcription capabilities
- **Voice Commands**: Special voice commands for UI control

## API Reference

### POST /audio/transcribe

Transcribe an audio file to text.

**Request:**
- `file`: Audio file (multipart/form-data)
- `language_code`: Language code (form data, default: "en")

**Response:**
```json
{
  "success": true,
  "transcribed_text": "Hello, this is a test.",
  "language_code": "en",
  "file_name": "recording.webm"
}
```

### GET /audio/supported-formats

Get list of supported audio formats.

**Response:**
```json
{
  "supported_formats": [".wav", ".opus", ".flac"],
  "description": "Supported audio formats for transcription"
}
```

### GET /audio/health

Check audio transcription service health.

**Response:**
```json
{
  "service": "audio_transcription",
  "status": "available",
  "nvidia_keys_available": true,
  "supported_formats": [".wav", ".opus", ".flac"]
}
```
