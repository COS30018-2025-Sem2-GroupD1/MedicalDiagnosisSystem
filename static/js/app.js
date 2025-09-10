// Medical AI Assistant - Main Application JavaScript

class MedicalChatbotApp {
    constructor() {
        this.currentUser = null; // doctor
        this.currentPatientId = null;
        this.currentSession = null;
        this.backendSessions = [];
        this.memory = new Map(); // In-memory storage for demo
        this.isLoading = false;
        this.doctors = this.loadDoctors();

        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.loadUserPreferences();
        this.initializeUser();
        this.loadSavedPatientId();

        // If a patient is selected, fetch sessions from backend first
        if (this.currentPatientId) {
            await this.fetchAndRenderPatientSessions();
        }

        // Ensure a session exists and is displayed immediately if nothing to show
        this.ensureStartupSession();
        this.loadChatSessions();
        // Apply saved theme immediately
        const prefs = JSON.parse(localStorage.getItem('medicalChatbotPreferences') || '{}');
        this.setTheme(prefs.theme || 'auto');
        this.setupTheme();
    }

    setupEventListeners() {
        // Sidebar toggle
        document.getElementById('sidebarToggle').addEventListener('click', () => {
            this.toggleSidebar();
        });
        // Click outside sidebar to close (mobile/overlay behavior)
        const overlay = document.getElementById('appOverlay');
        const updateOverlay = () => {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && overlay) overlay.classList.toggle('show', sidebar.classList.contains('show'));
        };
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const toggleBtn = document.getElementById('sidebarToggle');
            const main = document.querySelector('.main-content');
            if (!sidebar) return;
            const isOpen = sidebar.classList.contains('show');
            const clickInside = sidebar.contains(e.target) || (toggleBtn && toggleBtn.contains(e.target));
            if (isOpen && !clickInside) {
                sidebar.classList.remove('show');
            }
            // Also close if clicking the main-content while open
            if (isOpen && main && main.contains(e.target) && !sidebar.contains(e.target)) {
                sidebar.classList.remove('show');
            }
            updateOverlay();
        }, true);
        // Keep overlay synced when toggling
        const origToggle = this.toggleSidebar.bind(this);
        this.toggleSidebar = () => { origToggle(); updateOverlay(); };

        // New chat button
        document.getElementById('newChatBtn').addEventListener('click', () => {
            this.startNewChat();
        });

        // Patient load button
        const loadBtn = document.getElementById('loadPatientBtn');
        if (loadBtn) {
            loadBtn.addEventListener('click', () => this.loadPatient());
        }
        const patientInput = document.getElementById('patientIdInput');
        const suggestionsEl = document.getElementById('patientSuggestions');
        if (patientInput) {
            let debounceTimer;
            const hideSuggestions = () => { if (suggestionsEl) suggestionsEl.style.display = 'none'; };
            const renderSuggestions = (items) => {
                if (!suggestionsEl) return;
                if (!items || items.length === 0) { hideSuggestions(); return; }
                suggestionsEl.innerHTML = '';
                items.forEach(p => {
                    const div = document.createElement('div');
                    div.className = 'patient-suggestion';
                    div.textContent = `${p.name || 'Unknown'} (${p.patient_id})`;
                    div.addEventListener('click', () => {
                        this.currentPatientId = p.patient_id;
                        this.savePatientId();
                        patientInput.value = p.patient_id;
                        hideSuggestions();
                        this.fetchAndRenderPatientSessions();
                        const status = document.getElementById('patientStatus');
                        if (status) { status.textContent = `Patient: ${p.patient_id}`; status.style.color = 'var(--text-secondary)'; }
                    });
                    suggestionsEl.appendChild(div);
                });
                suggestionsEl.style.display = 'block';
            };
            patientInput.addEventListener('input', () => {
                const q = patientInput.value.trim();
                clearTimeout(debounceTimer);
                if (!q) { hideSuggestions(); return; }
                debounceTimer = setTimeout(async () => {
                    try {
                        const resp = await fetch(`/patients/search?q=${encodeURIComponent(q)}&limit=8`);
                        if (resp.ok) {
                            const data = await resp.json();
                            renderSuggestions(data.results || []);
                        }
                    } catch (_) { /* ignore */ }
                }, 200);
            });
            patientInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.loadPatient();
                    hideSuggestions();
                }
            });
            document.addEventListener('click', (ev) => {
                if (!suggestionsEl) return;
                if (!suggestionsEl.contains(ev.target) && ev.target !== patientInput) hideSuggestions();
            });
        }

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

        // Theme toggle live
        document.getElementById('themeSelect').addEventListener('change', (e) => {
            this.setTheme(e.target.value);
        });
        // Font size live
        document.getElementById('fontSize').addEventListener('change', (e) => {
            this.setFontSize(e.target.value);
        });
        // Other preferences live
        const autoSaveEl = document.getElementById('autoSave');
        const notificationsEl = document.getElementById('notifications');
        if (autoSaveEl) autoSaveEl.addEventListener('change', () => this.savePreferences());
        if (notificationsEl) notificationsEl.addEventListener('change', () => this.savePreferences());
    }

    loadDoctors() {
        try {
            const raw = localStorage.getItem('medicalChatbotDoctors');
            const arr = raw ? JSON.parse(raw) : [];
            const seen = new Set();
            return arr.filter(x => x && x.name && !seen.has(x.name) && seen.add(x.name));
        } catch { return []; }
    }

    saveDoctors() {
        localStorage.setItem('medicalChatbotDoctors', JSON.stringify(this.doctors));
    }

    populateDoctorSelect() {
        const sel = document.getElementById('profileNameSelect');
        const newSec = document.getElementById('newDoctorSection');
        if (!sel) return;
        sel.innerHTML = '';
        const createOpt = document.createElement('option');
        createOpt.value = '__create__';
        createOpt.textContent = 'Create doctor user...';
        sel.appendChild(createOpt);
        // Ensure no duplicates, and include current user name if not in list
        const names = new Set(this.doctors.map(d => d.name));
        if (this.currentUser?.name && !names.has(this.currentUser.name)) {
            this.doctors.unshift({ name: this.currentUser.name });
            names.add(this.currentUser.name);
            this.saveDoctors();
        }
        this.doctors.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.name;
            opt.textContent = d.name;
            if (this.currentUser?.name === d.name) opt.selected = true;
            sel.appendChild(opt);
        });
        sel.addEventListener('change', () => {
            if (sel.value === '__create__') {
                newSec.style.display = '';
                const input = document.getElementById('newDoctorName');
                if (input) input.value = '';
            } else {
                newSec.style.display = 'none';
            }
        });
        const cancelBtn = document.getElementById('cancelNewDoctor');
        const confirmBtn = document.getElementById('confirmNewDoctor');
        if (cancelBtn) cancelBtn.onclick = () => { newSec.style.display = 'none'; sel.value = this.currentUser?.name || ''; };
        if (confirmBtn) confirmBtn.onclick = () => {
            const name = (document.getElementById('newDoctorName').value || '').trim();
            if (!name) return;
            if (!this.doctors.find(d => d.name === name)) {
                this.doctors.unshift({ name });
                this.saveDoctors();
            }
            this.populateDoctorSelect();
            sel.value = name;
            newSec.style.display = 'none';
        };
    }

    loadSavedPatientId() {
        const pid = localStorage.getItem('medicalChatbotPatientId');
        if (pid && /^\d{8}$/.test(pid)) {
            this.currentPatientId = pid;
            const status = document.getElementById('patientStatus');
            if (status) {
                status.textContent = `Patient: ${pid}`;
                status.style.color = 'var(--text-secondary)';
            }
            const input = document.getElementById('patientIdInput');
            if (input) input.value = pid;
        }
    }

    savePatientId() {
        if (this.currentPatientId) {
            localStorage.setItem('medicalChatbotPatientId', this.currentPatientId);
        } else {
            localStorage.removeItem('medicalChatbotPatientId');
        }
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

        // Edit title modal wiring
        const closeEdit = () => this.hideModal('editTitleModal');
        const editTitleModal = document.getElementById('editTitleModal');
        if (editTitleModal) {
            document.getElementById('editTitleModalClose').addEventListener('click', closeEdit);
            document.getElementById('editTitleModalCancel').addEventListener('click', closeEdit);
            document.getElementById('editTitleModalSave').addEventListener('click', () => {
                const input = document.getElementById('editSessionTitleInput');
                const newTitle = input.value.trim();
                if (!newTitle) return;
                if (!this._pendingEditSessionId) return;
                this.renameChatSession(this._pendingEditSessionId, newTitle);
                this._pendingEditSessionId = null;
                input.value = '';
                this.hideModal('editTitleModal');
            });
        }
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
            this.setTheme(prefs.theme || 'auto');
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
            fontSize: document.getElementById('fontSize').value,
            autoSave: document.getElementById('autoSave').checked,
            notifications: document.getElementById('notifications').checked
        };
        localStorage.setItem('medicalChatbotPreferences', JSON.stringify(preferences));
    }

    startNewChat() {
        if (this.currentSession) {
            // Save current session (local only)
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

    ensureStartupSession() {
        // If we already have backend sessions for selected patient, do not create a local one
        if (this.backendSessions && this.backendSessions.length > 0) {
            return;
        }
        const sessions = this.getChatSessions();
        if (sessions.length === 0) {
            // Create a new session immediately so it shows in sidebar
            this.currentSession = {
                id: this.generateId(),
                title: 'New Chat',
                messages: [],
                createdAt: new Date().toISOString(),
                lastActivity: new Date().toISOString()
            };
            this.saveCurrentSession();
            this.updateChatTitle();
        } else {
            // Load the most recent session into view
            this.currentSession = sessions[0];
            this.clearChatMessages();
            this.currentSession.messages.forEach(m => this.displayMessage(m));
            this.updateChatTitle();
        }
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

    async loadPatient() {
        const input = document.getElementById('patientIdInput');
        const status = document.getElementById('patientStatus');
        const id = (input?.value || '').trim();
        if (!/^\d{8}$/.test(id)) {
            status.textContent = 'Invalid patient ID. Use 8 digits.';
            status.style.color = 'var(--warning-color)';
            return;
        }
        this.currentPatientId = id;
        this.savePatientId();
        status.textContent = `Patient: ${id}`;
        status.style.color = 'var(--text-secondary)';
        await this.fetchAndRenderPatientSessions();
    }

    async fetchAndRenderPatientSessions() {
        if (!this.currentPatientId) return;
        try {
            const resp = await fetch(`/patients/${this.currentPatientId}/sessions`);
            if (resp.ok) {
                const data = await resp.json();
                const sessions = Array.isArray(data.sessions) ? data.sessions : [];
                this.backendSessions = sessions.map(s => ({
                    id: s.session_id,
                    title: s.title || 'New Chat',
                    messages: [],
                    createdAt: s.created_at || new Date().toISOString(),
                    lastActivity: s.last_activity || new Date().toISOString(),
                    source: 'backend'
                }));
                // Prefer backend sessions if present
                if (this.backendSessions.length > 0) {
                    this.currentSession = this.backendSessions[0];
                    await this.hydrateMessagesForSession(this.currentSession.id);
                }
            } else {
                console.warn('Failed to fetch patient sessions', resp.status);
                this.backendSessions = [];
            }
        } catch (e) {
            console.error('Failed to load patient sessions', e);
            this.backendSessions = [];
        }
        this.loadChatSessions();
    }

    async hydrateMessagesForSession(sessionId) {
        try {
            const resp = await fetch(`/sessions/${sessionId}/messages?limit=1000`);
            if (!resp.ok) return;
            const data = await resp.json();
            const msgs = Array.isArray(data.messages) ? data.messages : [];
            const normalized = msgs.map(m => ({
                id: m._id || this.generateId(),
                role: m.role,
                content: m.content,
                timestamp: m.timestamp
            }));
            // set into currentSession if matched
            if (this.currentSession && this.currentSession.id === sessionId) {
                this.currentSession.messages = normalized;
                // Render
                this.clearChatMessages();
                this.currentSession.messages.forEach(m => this.displayMessage(m));
                this.updateChatTitle();
            }
        } catch (e) {
            console.error('Failed to hydrate session messages', e);
        }
    }

    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();

        if (!message || this.isLoading) return;
        if (!this.currentPatientId) {
            const status = document.getElementById('patientStatus');
            status.textContent = 'Select a patient before chatting.';
            status.style.color = 'var(--warning-color)';
            return;
        }

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
                patient_id: this.currentPatientId,
                doctor_id: this.currentUser.id,
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
                session: this.currentSession,
                patientId: this.currentPatientId
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

        // Update session title if it's the first user message -> call summariser
        if (role === 'user' && this.currentSession.messages.length === 2) {
            this.summariseAndSetTitle(content);
        }
    }

    async summariseAndSetTitle(text) {
        try {
            const resp = await fetch('/summarise', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, max_words: 5 })
            });
            if (resp.ok) {
                const data = await resp.json();
                const title = (data.title || 'New Chat').trim();
                this.currentSession.title = title;
                this.updateCurrentSession();
                this.updateChatTitle();
                this.loadChatSessions();
            } else {
                // Fallback: simple truncation
                const fallback = text.length > 50 ? text.substring(0, 50) + '...' : text;
                this.currentSession.title = fallback;
                this.updateCurrentSession();
                this.updateChatTitle();
                this.loadChatSessions();
            }
        } catch (e) {
            const fallback = text.length > 50 ? text.substring(0, 50) + '...' : text;
            this.currentSession.title = fallback;
            this.updateCurrentSession();
            this.updateChatTitle();
            this.loadChatSessions();
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

        // Prefer backend sessions if a patient is selected and sessions are available
        const sessions = (this.backendSessions && this.backendSessions.length > 0)
            ? this.backendSessions
            : this.getChatSessions();

        if (sessions.length === 0) {
            sessionsContainer.innerHTML = '<div class="no-sessions">No chat sessions yet</div>';
            return;
        }

        sessions.forEach(session => {
            const sessionElement = document.createElement('div');
            sessionElement.className = `chat-session ${session.id === this.currentSession?.id ? 'active' : ''}`;
            sessionElement.addEventListener('click', async () => {
                if (session.source === 'backend') {
                    this.currentSession = { ...session };
                    await this.hydrateMessagesForSession(session.id);
                } else {
                this.loadChatSession(session.id);
                }
            });

            const time = this.formatTime(session.lastActivity);

            sessionElement.innerHTML = `
                <div class="chat-session-row">
                    <div class="chat-session-meta">
                        <div class="chat-session-title">${session.title}</div>
                        <div class="chat-session-time">${time}</div>
                    </div>
                    <div class="chat-session-actions">
                        <button class="chat-session-menu" title="Options" aria-label="Options" data-session-id="${session.id}">
                            <i class="fas fa-ellipsis-vertical"></i>
                        </button>
                    </div>
                </div>
            `;

            sessionsContainer.appendChild(sessionElement);

            // Wire 3-dot menu (local sessions only for now)
            const menuBtn = sessionElement.querySelector('.chat-session-menu');
            if (session.source !== 'backend') {
            menuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showSessionMenu(e.currentTarget, session.id);
            });
            } else {
                menuBtn.disabled = true;
                menuBtn.style.opacity = 0.5;
                menuBtn.title = 'Options available for local sessions only';
            }
        });
    }

    showSessionMenu(anchorEl, sessionId) {
        // Remove existing popover
        document.querySelectorAll('.chat-session-menu-popover').forEach(p => p.remove());
        const rect = anchorEl.getBoundingClientRect();
        const pop = document.createElement('div');
        pop.className = 'chat-session-menu-popover show';
        pop.innerHTML = `
            <div class="chat-session-menu-item" data-action="edit" data-session-id="${sessionId}"><i class="fas fa-pen"></i> Edit Name</div>
            <div class="chat-session-menu-item" data-action="delete" data-session-id="${sessionId}"><i class="fas fa-trash"></i> Delete</div>
        `;
        document.body.appendChild(pop);
        // Position near button
        pop.style.top = `${rect.bottom + window.scrollY + 6}px`;
        pop.style.left = `${rect.right + window.scrollX - pop.offsetWidth}px`;

        const onDocClick = (ev) => {
            if (!pop.contains(ev.target) && ev.target !== anchorEl) {
                pop.remove();
                document.removeEventListener('click', onDocClick);
            }
        };
        setTimeout(() => document.addEventListener('click', onDocClick), 0);

        pop.querySelectorAll('.chat-session-menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const action = item.getAttribute('data-action');
                const id = item.getAttribute('data-session-id');
                if (action === 'delete') {
                    this.deleteChatSession(id);
                } else if (action === 'edit') {
                    this._pendingEditSessionId = id;
                    const sessions = this.getChatSessions();
                    const s = sessions.find(x => x.id === id);
                    const input = document.getElementById('editSessionTitleInput');
                    input.value = s ? s.title : '';
                    this.showModal('editTitleModal');
                }
                pop.remove();
            });
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
        if (this.currentSession.source === 'backend') return; // do not persist backend sessions locally here

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

    deleteChatSession(sessionId) {
        const sessions = this.getChatSessions();
        const index = sessions.findIndex(s => s.id === sessionId);
        if (index === -1) return;

        const confirmDelete = confirm('Delete this chat session? This cannot be undone.');
        if (!confirmDelete) return;

        sessions.splice(index, 1);
        localStorage.setItem(`chatSessions_${this.currentUser.id}`, JSON.stringify(sessions));

        // If deleting the current session, switch to another or clear view
        if (this.currentSession && this.currentSession.id === sessionId) {
            if (sessions.length > 0) {
                this.currentSession = sessions[0];
                this.clearChatMessages();
                this.currentSession.messages.forEach(m => this.displayMessage(m));
                this.updateChatTitle();
            } else {
                this.currentSession = null;
                this.clearChatMessages();
                this.updateChatTitle();
            }
        }

        this.loadChatSessions();
    }

    renameChatSession(sessionId, newTitle) {
        const sessions = this.getChatSessions();
        const idx = sessions.findIndex(s => s.id === sessionId);
        if (idx === -1) return;
        sessions[idx] = { ...sessions[idx], title: newTitle };
        localStorage.setItem(`chatSessions_${this.currentUser.id}`, JSON.stringify(sessions));
        if (this.currentSession && this.currentSession.id === sessionId) {
            this.currentSession.title = newTitle;
            this.updateChatTitle();
        }
        this.loadChatSessions();
    }

    showUserModal() {
        this.populateDoctorSelect();
        // Ensure the dropdown is visible immediately with options
        const sel = document.getElementById('profileNameSelect');
        if (sel && sel.options.length === 0) {
            // Fallback in unlikely case populate didn't run
            const createOpt = document.createElement('option');
            createOpt.value = '__create__';
            createOpt.textContent = 'Create doctor user...';
            sel.appendChild(createOpt);
        }
        document.getElementById('profileRole').value = this.currentUser.role;
        document.getElementById('profileSpecialty').value = this.currentUser.specialty || '';

        this.showModal('userModal');
    }

    saveUserProfile() {
        const nameSel = document.getElementById('profileNameSelect');
        const name = nameSel ? nameSel.value : '';
        const role = document.getElementById('profileRole').value;
        const specialty = document.getElementById('profileSpecialty').value.trim();

        if (!name || name === '__create__') {
            alert('Please select or create a doctor name.');
            return;
        }

        if (!this.doctors.find(d => d.name === name)) {
            this.doctors.unshift({ name });
            this.saveDoctors();
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

// Add near setupEventListeners inside the class methods where others are wired
// Patient modal open
document.addEventListener('DOMContentLoaded', () => {
    const profileBtn = document.getElementById('patientMenuBtn');
    const modal = document.getElementById('patientModal');
    const closeBtn = document.getElementById('patientModalClose');
    const logoutBtn = document.getElementById('patientLogoutBtn');
    const createBtn = document.getElementById('patientCreateBtn');

    if (profileBtn && modal) {
        profileBtn.addEventListener('click', async () => {
            const pid = window.medicalChatbot?.currentPatientId;
            if (pid) {
                try {
                    const resp = await fetch(`/patients/${pid}`);
                    if (resp.ok) {
                        const p = await resp.json();
                        const name = p.name || 'Unknown';
                        const age = typeof p.age === 'number' ? p.age : '-';
                        const sex = p.sex || '-';
                        const meds = Array.isArray(p.medications) && p.medications.length > 0 ? p.medications.join(', ') : '-';
                        document.getElementById('patientSummary').textContent = `${name} — ${sex}, ${age}`;
                        document.getElementById('patientMedications').textContent = meds;
                        document.getElementById('patientAssessment').textContent = p.past_assessment_summary || '-';
                    }
                } catch (e) {
                    console.error('Failed to load patient profile', e);
                }
            }
            modal.classList.add('show');
        });
    }
    if (closeBtn && modal) {
        closeBtn.addEventListener('click', () => modal.classList.remove('show'));
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('Log out current patient?')) {
                if (window.medicalChatbot) {
                    window.medicalChatbot.currentPatientId = null;
                    localStorage.removeItem('medicalChatbotPatientId');
                    const status = document.getElementById('patientStatus');
                    if (status) { status.textContent = 'No patient selected'; status.style.color = 'var(--text-secondary)'; }
                    const input = document.getElementById('patientIdInput');
                    if (input) input.value = '';
                    modal.classList.remove('show');
                }
            }
        });
    }
    if (createBtn) {
        createBtn.addEventListener('click', () => {
            modal.classList.remove('show');
        });
    }
});

// Handle system theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const themeSelect = document.getElementById('themeSelect');
    if (themeSelect && themeSelect.value === 'auto') {
        window.medicalChatbot.setTheme('auto');
    }
});

// Ensure sidebar toggle works in mobile
(function ensureSidebarToggle() {
    document.addEventListener('DOMContentLoaded', () => {
        const sidebar = document.getElementById('sidebar');
        const toggle = document.getElementById('sidebarToggle');
        if (toggle && sidebar) {
            toggle.addEventListener('click', () => {
                sidebar.classList.toggle('show');
            });
        }
    });
})();

// Restore doctor profile modal opening
(function wireDoctorModalOpen() {
    document.addEventListener('DOMContentLoaded', () => {
        const doctorCard = document.getElementById('userProfile');
        const userModal = document.getElementById('userModal');
        const closeBtn = document.getElementById('userModalClose');
        const cancelBtn = document.getElementById('userModalCancel');
        if (doctorCard && userModal) {
            doctorCard.addEventListener('click', () => userModal.classList.add('show'));
        }
        if (closeBtn) closeBtn.addEventListener('click', () => userModal.classList.remove('show'));
        if (cancelBtn) cancelBtn.addEventListener('click', () => userModal.classList.remove('show'));
        if (userModal) {
            userModal.addEventListener('click', (e) => { if (e.target === userModal) userModal.classList.remove('show'); });
        }
    });
})();

// Ensure settings modal opens
(function wireSettingsModal() {
    document.addEventListener('DOMContentLoaded', () => {
        const settingsBtn = document.getElementById('settingsBtn');
        const modal = document.getElementById('settingsModal');
        const closeBtn = document.getElementById('settingsModalClose');
        const cancelBtn = document.getElementById('settingsModalCancel');
        if (settingsBtn && modal) settingsBtn.addEventListener('click', () => modal.classList.add('show'));
        if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.remove('show'));
        if (cancelBtn) cancelBtn.addEventListener('click', () => modal.classList.remove('show'));
        if (modal) modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });
    });
})();

// Add patient registration link under patient ID form if not present
(function ensurePatientCreateLink() {
    document.addEventListener('DOMContentLoaded', () => {
        const patientSection = document.querySelector('.patient-section');
        const inputGroup = document.querySelector('.patient-input-group');
        if (patientSection && inputGroup) {
            let link = document.getElementById('createPatientLink');
            if (!link) {
                link = document.createElement('a');
                link.id = 'createPatientLink';
                link.href = '/static/patient.html';
                link.className = 'patient-create-link';
                link.title = 'Create new patient';
                link.innerHTML = '<i class="fas fa-user-plus"></i>';
                inputGroup.appendChild(link);
            }
        }
    });
})();
