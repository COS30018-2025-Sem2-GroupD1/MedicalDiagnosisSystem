// audio/recorder.js
// Audio recording and transcription functionality

export class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.audioContext = null;
        this.audioStream = null;
    }

    async initialize() {
        try {
            // Request microphone access
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000, // 16kHz for better speech recognition
                    channelCount: 1,   // Mono
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            // Create MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.audioStream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            // Set up event handlers
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.processRecording();
            };

            return true;
        } catch (error) {
            console.error('Failed to initialize audio recorder:', error);
            throw new Error('Microphone access denied or not available');
        }
    }

    startRecording() {
        if (!this.mediaRecorder || this.isRecording) {
            return false;
        }

        try {
            this.audioChunks = [];
            this.mediaRecorder.start();
            this.isRecording = true;
            console.log('Audio recording started');
            return true;
        } catch (error) {
            console.error('Failed to start recording:', error);
            return false;
        }
    }

    stopRecording() {
        if (!this.mediaRecorder || !this.isRecording) {
            return false;
        }

        try {
            this.mediaRecorder.stop();
            this.isRecording = false;
            console.log('Audio recording stopped');
            return true;
        } catch (error) {
            console.error('Failed to stop recording:', error);
            return false;
        }
    }

    async processRecording() {
        if (this.audioChunks.length === 0) {
            console.warn('No audio data recorded');
            return null;
        }

        try {
            // Create audio blob
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            
            // Convert to WAV format for better compatibility
            const wavBlob = await this.convertToWav(audioBlob);
            
            // Transcribe audio
            const transcribedText = await this.transcribeAudio(wavBlob);
            
            return transcribedText;
        } catch (error) {
            console.error('Failed to process recording:', error);
            throw error;
        }
    }

    async convertToWav(webmBlob) {
        try {
            // For now, we'll use the webm blob directly
            // In a production environment, you might want to convert to WAV
            // This requires additional libraries like lamejs or similar
            return webmBlob;
        } catch (error) {
            console.error('Failed to convert to WAV:', error);
            return webmBlob; // Fallback to original blob
        }
    }

    async transcribeAudio(audioBlob) {
        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.webm');
            formData.append('language_code', 'en');

            const response = await fetch('/audio/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Transcription failed');
            }

            const result = await response.json();
            return result.transcribed_text;
        } catch (error) {
            console.error('Transcription failed:', error);
            throw error;
        }
    }

    cleanup() {
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
    }

    isAvailable() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }
}

// Audio recording UI controller
export class AudioRecordingUI {
    constructor(app) {
        this.app = app;
        this.recorder = new AudioRecorder();
        this.microphoneBtn = null;
        this.isInitialized = false;
        this.recordingTimeout = null;
    }

    async initialize() {
        if (!this.recorder.isAvailable()) {
            console.warn('Audio recording not supported in this browser');
            return false;
        }

        try {
            await this.recorder.initialize();
            this.setupUI();
            this.isInitialized = true;
            return true;
        } catch (error) {
            console.error('Failed to initialize audio recording UI:', error);
            this.showError('Microphone access denied. Please allow microphone access to use voice input.');
            return false;
        }
    }

    setupUI() {
        this.microphoneBtn = document.getElementById('microphoneBtn');
        if (!this.microphoneBtn) {
            console.error('Microphone button not found');
            return;
        }

        // Add recording state classes
        this.microphoneBtn.classList.add('recording-enabled');
        
        // Set up event listeners
        this.microphoneBtn.addEventListener('mousedown', (e) => this.startRecording(e));
        this.microphoneBtn.addEventListener('mouseup', (e) => this.stopRecording(e));
        this.microphoneBtn.addEventListener('mouseleave', (e) => this.stopRecording(e));
        
        // Touch events for mobile
        this.microphoneBtn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording(e);
        });
        this.microphoneBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopRecording(e);
        });

        // Update button appearance
        this.updateButtonState('ready');
    }

    async startRecording(event) {
        if (!this.isInitialized || this.recorder.isRecording) {
            return;
        }

        event.preventDefault();
        
        try {
            const success = this.recorder.startRecording();
            if (success) {
                this.updateButtonState('recording');
                this.showRecordingIndicator();
                
                // Auto-stop after 30 seconds to prevent very long recordings
                this.recordingTimeout = setTimeout(() => {
                    this.stopRecording(event);
                }, 30000);
            }
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.showError('Failed to start recording. Please try again.');
        }
    }

    async stopRecording(event) {
        if (!this.isInitialized || !this.recorder.isRecording) {
            return;
        }

        event.preventDefault();
        
        try {
            const success = this.recorder.stopRecording();
            if (success) {
                this.updateButtonState('processing');
                this.hideRecordingIndicator();
                
                if (this.recordingTimeout) {
                    clearTimeout(this.recordingTimeout);
                    this.recordingTimeout = null;
                }

                // Process the recording
                const transcribedText = await this.recorder.processRecording();
                
                if (transcribedText) {
                    this.insertTranscribedText(transcribedText);
                    this.showSuccess('Audio transcribed successfully!');
                } else {
                    this.showError('No speech detected. Please try again.');
                }
                
                this.updateButtonState('ready');
            }
        } catch (error) {
            console.error('Failed to stop recording:', error);
            this.showError('Transcription failed. Please try again.');
            this.updateButtonState('ready');
        }
    }

    insertTranscribedText(text) {
        const chatInput = document.getElementById('chatInput');
        if (!chatInput) {
            console.error('Chat input not found');
            return;
        }

        // Append transcribed text to existing content
        const currentText = chatInput.value.trim();
        const newText = currentText ? `${currentText} ${text}` : text;
        
        chatInput.value = newText;
        
        // Add visual feedback for transcribed text
        chatInput.classList.add('transcribed');
        
        // Remove the highlighting after a few seconds
        setTimeout(() => {
            chatInput.classList.remove('transcribed');
        }, 3000);
        
        // Trigger input event to update UI
        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        
        // Focus the input
        chatInput.focus();
        
        // Auto-resize if needed
        if (this.app && this.app.autoResizeTextarea) {
            this.app.autoResizeTextarea(chatInput);
        }
    }

    updateButtonState(state) {
        if (!this.microphoneBtn) return;

        // Remove all state classes
        this.microphoneBtn.classList.remove('recording-ready', 'recording-active', 'recording-processing');
        
        // Add appropriate state class
        switch (state) {
            case 'ready':
                this.microphoneBtn.classList.add('recording-ready');
                this.microphoneBtn.title = 'Hold to record voice input';
                break;
            case 'recording':
                this.microphoneBtn.classList.add('recording-active');
                this.microphoneBtn.title = 'Recording... Release to stop';
                break;
            case 'processing':
                this.microphoneBtn.classList.add('recording-processing');
                this.microphoneBtn.title = 'Processing audio...';
                break;
        }
    }

    showRecordingIndicator() {
        // Create or update recording indicator
        let indicator = document.getElementById('recordingIndicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'recordingIndicator';
            indicator.className = 'recording-indicator';
            indicator.innerHTML = '<i class="fas fa-microphone"></i> Recording...';
            
            const chatInputContainer = document.querySelector('.chat-input-container');
            if (chatInputContainer) {
                chatInputContainer.appendChild(indicator);
            }
        }
        
        indicator.style.display = 'block';
    }

    hideRecordingIndicator() {
        const indicator = document.getElementById('recordingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    showError(message) {
        // Create or update error message
        let errorMsg = document.getElementById('audioError');
        if (!errorMsg) {
            errorMsg = document.createElement('div');
            errorMsg.id = 'audioError';
            errorMsg.className = 'audio-error-message';
            
            const chatInputContainer = document.querySelector('.chat-input-container');
            if (chatInputContainer) {
                chatInputContainer.appendChild(errorMsg);
            }
        }
        
        errorMsg.textContent = message;
        errorMsg.style.display = 'block';
        
        // Hide after 5 seconds
        setTimeout(() => {
            errorMsg.style.display = 'none';
        }, 5000);
    }

    showSuccess(message) {
        // Create or update success message
        let successMsg = document.getElementById('audioSuccess');
        if (!successMsg) {
            successMsg = document.createElement('div');
            successMsg.id = 'audioSuccess';
            successMsg.className = 'audio-success-message';
            
            const chatInputContainer = document.querySelector('.chat-input-container');
            if (chatInputContainer) {
                chatInputContainer.appendChild(successMsg);
            }
        }
        
        successMsg.textContent = message;
        successMsg.style.display = 'block';
        
        // Hide after 3 seconds
        setTimeout(() => {
            successMsg.style.display = 'none';
        }, 3000);
    }

    cleanup() {
        if (this.recorder) {
            this.recorder.cleanup();
        }
        
        if (this.recordingTimeout) {
            clearTimeout(this.recordingTimeout);
            this.recordingTimeout = null;
        }
    }
}
