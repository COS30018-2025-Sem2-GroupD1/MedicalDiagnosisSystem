// Medical AI Assistant - Main Application JavaScript

class MedicalChatbotApp {
    constructor() {
        this.currentUser = null;
        this.currentSession = null;
        this.memory = new Map(); // In-memory storage for demo
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadUserPreferences();
        this.initializeUser();
        this.loadChatSessions();
        this.setupTheme();
    }
    
    setupEventListeners() {
        // Sidebar toggle
        document.getElementById('sidebarToggle').addEventListener('click', () => {
            this.toggleSidebar();
        });
        
        // New chat button
        document.getElementById('newChatBtn').addEventListener('click', () => {
            this.startNewChat();
        });
        
        // Send button and input
        document.getElementById('sendBtn').addEventListener('click', () => {
            this.sendMessage();
        });
        
        document.getElementById('chatInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        document.getElementById('chatInput').addEventListener('input', (e) => {
            this.autoResizeTextarea(e.target);
        });
        
        // User profile
        document.getElementById('userProfile').addEventListener('click', () => {
            this.showUserModal();
        });
        
        // Settings
        document.getElementById('settingsBtn').addEventListener('click', () => {
            this.showSettingsModal();
        });
        
        // Action buttons
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportChat();
        });
        
        document.getElementById('clearBtn').addEventListener('click', () => {
            this.clearChat();
        });
        
        // Modal events
        this.setupModalEvents();
        
        // Theme toggle
        document.getElementById('themeSelect').addEventListener('change', (e) => {
            this.setTheme(e.target.value);
        });
    }
    
    setupModalEvents() {
        // User modal
        document.getElementById('userModalClose').addEventListener('click', () => {
            this.hideModal('userModal');
        });
        
        document.getElementById('userModalCancel').addEventListener('click', () => {
            this.hideModal('userModal');
        });
        
        document.getElementById('userModalSave').addEventListener('click', () => {
            this.saveUserProfile();
        });
        
        // Settings modal
        document.getElementById('settingsModalClose').addEventListener('click', () => {
            this.hideModal('settingsModal');
        });
        
        document.getElementById('settingsModalCancel').addEventListener('click', () => {
            this.hideModal('settingsModal');
        });
        
        document.getElementById('settingsModalSave').addEventListener('click', () => {
            this.saveSettings();
        });
        
        // Close modals when clicking outside
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });
    }
    
    initializeUser() {
        // Check if user exists in localStorage
        const savedUser = localStorage.getItem('medicalChatbotUser');
        if (savedUser) {
            this.currentUser = JSON.parse(savedUser);
        } else {
            // Create default user
            this.currentUser = {
                id: this.generateId(),
                name: 'Anonymous',
                role: 'Medical Professional',
                specialty: '',
                createdAt: new Date().toISOString()
            };
            this.saveUser();
        }
        
        this.updateUserDisplay();
    }
    
    loadUserPreferences() {
        const preferences = localStorage.getItem('medicalChatbotPreferences');
        if (preferences) {
            const prefs = JSON.parse(preferences);
            this.setTheme(prefs.theme || 'light');
            this.setFontSize(prefs.fontSize || 'medium');
        }
    }
    
    setupTheme() {
        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            this.setTheme('auto');
        }
    }
    
    setTheme(theme) {
        const root = document.documentElement;
        
        if (theme === 'auto') {
            const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', isDark ? 'dark' : 'light');
        } else {
            root.setAttribute('data-theme', theme);
        }
        
        // Update select element
        document.getElementById('themeSelect').value = theme;
        
        // Save preference
        this.savePreferences();
    }
    
    setFontSize(size) {
        const root = document.documentElement;
        root.style.fontSize = size === 'small' ? '14px' : size === 'large' ? '18px' : '16px';
        
        // Save preference
        this.savePreferences();
    }
    
    savePreferences() {
        const preferences = {
            theme: document.getElementById('themeSelect').value,
            fontSize: document.getElementById('fontSize').value
        };
        localStorage.setItem('medicalChatbotPreferences', JSON.stringify(preferences));
    }
    
    startNewChat() {
        if (this.currentSession) {
            // Save current session
            this.saveCurrentSession();
        }
        
        // Create new session
        this.currentSession = {
            id: this.generateId(),
            title: 'New Chat',
            messages: [],
            createdAt: new Date().toISOString(),
            lastActivity: new Date().toISOString()
        };
        
        // Clear chat messages
        this.clearChatMessages();
        
        // Add welcome message
        this.addMessage('assistant', this.getWelcomeMessage());
        
        // Update UI
        this.updateChatTitle();
        this.loadChatSessions();
        
        // Focus input
        document.getElementById('chatInput').focus();
    }
    
    getWelcomeMessage() {
        return `👋 Welcome to Medical AI Assistant

I'm here to help you with medical questions, diagnosis assistance, and healthcare information. I can:

🔍 Answer medical questions and provide information
📋 Help with symptom analysis and differential diagnosis
💊 Provide medication and treatment information
📚 Explain medical procedures and conditions
⚠️ Offer general health advice (not medical diagnosis)

**Important:** This is for informational purposes only. Always consult with qualified healthcare professionals for medical advice.

How can I assist you today?`;
    }
    
    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message || this.isLoading) return;
        
        // Clear input
        input.value = '';
        this.autoResizeTextarea(input);
        
        // Add user message
        this.addMessage('user', message);
        
        // Show loading
        this.showLoading(true);
        
        try {
            // Send to API
            const response = await this.callMedicalAPI(message);
            
            // Add assistant response
            this.addMessage('assistant', response);
            
            // Update session
            this.updateCurrentSession();
            
        } catch (error) {
            console.error('Error sending message:', error);
            
            // Show more specific error messages
            let errorMessage = 'I apologize, but I encountered an error processing your request.';
            
            if (error.message.includes('500')) {
                errorMessage = 'The server encountered an internal error. Please try again in a moment.';
            } else if (error.message.includes('404')) {
                errorMessage = 'The requested service was not found. Please check your connection.';
            } else if (error.message.includes('fetch')) {
                errorMessage = 'Unable to connect to the server. Please check your internet connection.';
            }
            
            this.addMessage('assistant', errorMessage);
        } finally {
            this.showLoading(false);
        }
    }
    
    async callMedicalAPI(message) {
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                            body: JSON.stringify({
                user_id: this.currentUser.id,
                session_id: this.currentSession?.id || 'default',
                message: message,
                user_role: this.currentUser.role,
                user_specialty: this.currentUser.specialty,
                title: this.currentSession?.title || 'New Chat'
            })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data.response || 'I apologize, but I received an empty response. Please try again.';
            
        } catch (error) {
            console.error('API call failed:', error);
            // Log detailed error information
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                user: this.currentUser,
                session: this.currentSession
            });
            
            // Only return mock response if it's a network error, not a server error
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                return this.generateMockResponse(message);
            } else {
                throw error; // Re-throw server errors to show proper error message
            }
        }
    }
    
    generateMockResponse(message) {
        const responses = [
            "Based on your question about medical topics, I can provide general information. However, please remember that this is for educational purposes only and should not replace professional medical advice.",
            "That's an interesting medical question. While I can offer some general insights, it's important to consult with healthcare professionals for personalized medical advice.",
            "I understand your medical inquiry. For accurate diagnosis and treatment recommendations, please consult with qualified healthcare providers who can assess your specific situation.",
            "Thank you for your medical question. I can provide educational information, but medical decisions should always be made in consultation with healthcare professionals.",
            "I appreciate your interest in medical topics. Remember that medical information found online should be discussed with healthcare providers for proper evaluation."
        ];
        
        return responses[Math.floor(Math.random() * responses.length)];
    }
    
    addMessage(role, content) {
        if (!this.currentSession) {
            this.startNewChat();
        }
        
        const message = {
            id: this.generateId(),
            role: role,
            content: content,
            timestamp: new Date().toISOString()
        };
        
        this.currentSession.messages.push(message);
        
        // Update UI
        this.displayMessage(message);
        
        // Update session title if it's the first user message
        if (role === 'user' && this.currentSession.messages.length === 2) {
            const title = content.length > 50 ? content.substring(0, 50) + '...' : content;
            this.currentSession.title = title;
            this.updateChatTitle();
        }
    }
    
    displayMessage(message) {
        const chatMessages = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.role}-message fade-in`;
        messageElement.id = `message-${message.id}`;
        
        const avatar = message.role === 'user' ? 
            '<i class="fas fa-user"></i>' : 
            '<i class="fas fa-robot"></i>';
        
        const time = this.formatTime(message.timestamp);
        
        messageElement.innerHTML = `
            <div class="message-avatar">
                ${avatar}
            </div>
            <div class="message-content">
                <div class="message-text">
                    ${this.formatMessageContent(message.content)}
                </div>
                <div class="message-time">${time}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Add to session if it exists
        if (this.currentSession) {
            this.currentSession.lastActivity = new Date().toISOString();
        }
    }
    
    formatMessageContent(content) {
        // Convert markdown-like syntax to HTML
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>')
            .replace(/🔍/g, '<span style="color: var(--primary-color);">🔍</span>')
            .replace(/📋/g, '<span style="color: var(--secondary-color);">📋</span>')
            .replace(/💊/g, '<span style="color: var(--accent-color);">💊</span>')
            .replace(/📚/g, '<span style="color: var(--success-color);">📚</span>')
            .replace(/⚠️/g, '<span style="color: var(--warning-color);">⚠️</span>');
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else if (diff < 86400000) { // Less than 1 day
            const hours = Math.floor(diff / 3600000);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
    
    clearChatMessages() {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '';
    }
    
    clearChat() {
        if (confirm('Are you sure you want to clear this chat? This action cannot be undone.')) {
            this.clearChatMessages();
            if (this.currentSession) {
                this.currentSession.messages = [];
                this.currentSession.title = 'New Chat';
                this.updateChatTitle();
            }
        }
    }
    
    exportChat() {
        if (!this.currentSession || this.currentSession.messages.length === 0) {
            alert('No chat to export.');
            return;
        }
        
        const chatData = {
            user: this.currentUser.name,
            session: this.currentSession.title,
            date: new Date().toISOString(),
            messages: this.currentSession.messages
        };
        
        const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `medical-chat-${this.currentSession.title.replace(/[^a-z0-9]/gi, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    loadChatSessions() {
        const sessionsContainer = document.getElementById('chatSessions');
        sessionsContainer.innerHTML = '';
        
        // Get sessions from localStorage
        const sessions = this.getChatSessions();
        
        if (sessions.length === 0) {
            sessionsContainer.innerHTML = '<div class="no-sessions">No chat sessions yet</div>';
            return;
        }
        
        sessions.forEach(session => {
            const sessionElement = document.createElement('div');
            sessionElement.className = `chat-session ${session.id === this.currentSession?.id ? 'active' : ''}`;
            sessionElement.addEventListener('click', () => {
                this.loadChatSession(session.id);
            });
            
            const time = this.formatTime(session.lastActivity);
            
            sessionElement.innerHTML = `
                <div class="chat-session-title">${session.title}</div>
                <div class="chat-session-time">${time}</div>
            `;
            
            sessionsContainer.appendChild(sessionElement);
        });
    }
    
    loadChatSession(sessionId) {
        const sessions = this.getChatSessions();
        const session = sessions.find(s => s.id === sessionId);
        
        if (!session) return;
        
        this.currentSession = session;
        
        // Clear and reload messages
        this.clearChatMessages();
        session.messages.forEach(message => {
            this.displayMessage(message);
        });
        
        // Update UI
        this.updateChatTitle();
        this.loadChatSessions();
    }
    
    getChatSessions() {
        const sessions = localStorage.getItem(`chatSessions_${this.currentUser.id}`);
        return sessions ? JSON.parse(sessions) : [];
    }
    
    saveCurrentSession() {
        if (!this.currentSession) return;
        
        const sessions = this.getChatSessions();
        const existingIndex = sessions.findIndex(s => s.id === this.currentSession.id);
        
        if (existingIndex >= 0) {
            sessions[existingIndex] = { ...this.currentSession };
        } else {
            sessions.unshift(this.currentSession);
        }
        
        localStorage.setItem(`chatSessions_${this.currentUser.id}`, JSON.stringify(sessions));
    }
    
    updateCurrentSession() {
        if (this.currentSession) {
            this.currentSession.lastActivity = new Date().toISOString();
            this.saveCurrentSession();
        }
    }
    
    updateChatTitle() {
        const titleElement = document.getElementById('chatTitle');
        if (this.currentSession) {
            titleElement.textContent = this.currentSession.title;
        } else {
            titleElement.textContent = 'Medical AI Assistant';
        }
    }
    
    showUserModal() {
        // Populate form with current user data
        document.getElementById('profileName').value = this.currentUser.name;
        document.getElementById('profileRole').value = this.currentUser.role;
        document.getElementById('profileSpecialty').value = this.currentUser.specialty || '';
        
        this.showModal('userModal');
    }
    
    saveUserProfile() {
        const name = document.getElementById('profileName').value.trim();
        const role = document.getElementById('profileRole').value;
        const specialty = document.getElementById('profileSpecialty').value.trim();
        
        if (!name) {
            alert('Please enter a name.');
            return;
        }
        
        this.currentUser.name = name;
        this.currentUser.role = role;
        this.currentUser.specialty = specialty;
        
        this.saveUser();
        this.updateUserDisplay();
        this.hideModal('userModal');
    }
    
    showSettingsModal() {
        this.showModal('settingsModal');
    }
    
    saveSettings() {
        const theme = document.getElementById('themeSelect').value;
        const fontSize = document.getElementById('fontSize').value;
        const autoSave = document.getElementById('autoSave').checked;
        const notifications = document.getElementById('notifications').checked;
        
        this.setTheme(theme);
        this.setFontSize(fontSize);
        
        // Save additional preferences
        const preferences = {
            theme: theme,
            fontSize: fontSize,
            autoSave: autoSave,
            notifications: notifications
        };
        localStorage.setItem('medicalChatbotPreferences', JSON.stringify(preferences));
        
        this.hideModal('settingsModal');
    }
    
    showModal(modalId) {
        document.getElementById(modalId).classList.add('show');
    }
    
    hideModal(modalId) {
        document.getElementById(modalId).classList.remove('show');
    }
    
    showLoading(show) {
        this.isLoading = show;
        const overlay = document.getElementById('loadingOverlay');
        const sendBtn = document.getElementById('sendBtn');
        
        if (show) {
            overlay.classList.add('show');
            sendBtn.disabled = true;
        } else {
            overlay.classList.remove('show');
            sendBtn.disabled = false;
        }
    }
    
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('show');
    }
    
    updateUserDisplay() {
        document.getElementById('userName').textContent = this.currentUser.name;
        document.getElementById('userStatus').textContent = this.currentUser.role;
    }
    
    saveUser() {
        localStorage.setItem('medicalChatbotUser', JSON.stringify(this.currentUser));
    }
    
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
    
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.medicalChatbot = new MedicalChatbotApp();
});

// Handle system theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const themeSelect = document.getElementById('themeSelect');
    if (themeSelect && themeSelect.value === 'auto') {
        window.medicalChatbot.setTheme('auto');
    }
});
