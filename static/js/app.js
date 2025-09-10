// Medical AI Assistant - Main Application JavaScript
import { attachUIHandlers } from './ui/handlers.js';
import { attachDoctorUI } from './ui/doctor.js';
import { attachPatientUI } from './ui/patient.js';
import { attachSettingsUI } from './ui/settings.js';
import { attachSessionsUI } from './chat/sessions.js';
import { attachMessagingUI } from './chat/messaging.js';

class MedicalChatbotApp {
    constructor() {
        this.currentUser = null; // doctor
        this.currentPatientId = null;
        this.currentSession = null;
        this.backendSessions = [];
        this.memory = new Map();  // In-memory storage for STM/demo
        this.isLoading = false;
        this.doctors = this.loadDoctors();

        this.init();
    }

    async init() {
        // Attach shared UI helpers once
        attachUIHandlers(this);
        // Attach specialized UIs
        attachDoctorUI(this);
        attachPatientUI(this);
        attachSettingsUI(this);
        attachSessionsUI(this);
        attachMessagingUI(this);
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
        
        // Bind patient handlers
        console.log('[DEBUG] Binding patient handlers');
        this.bindPatientHandlers();
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
        console.log('[DEBUG] Overlay element found:', !!overlay);
        const updateOverlay = () => {
            const sidebar = document.getElementById('sidebar');
            const isOpen = sidebar && sidebar.classList.contains('show');
            console.log('[DEBUG] Updating overlay - sidebar open:', isOpen);
            if (sidebar && overlay) {
                if (isOpen) {
                    overlay.classList.add('show');
                    console.log('[DEBUG] Overlay shown');
                } else {
                    overlay.classList.remove('show');
                    console.log('[DEBUG] Overlay hidden');
                }
            }
        };
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const toggleBtn = document.getElementById('sidebarToggle');
            const main = document.querySelector('.main-content');
            if (!sidebar) return;
            const isOpen = sidebar.classList.contains('show');
            const clickInside = sidebar.contains(e.target) || (toggleBtn && toggleBtn.contains(e.target));
            const clickOnOverlay = overlay && overlay.contains(e.target);
            
            console.log('[DEBUG] Click event - sidebar open:', isOpen, 'click inside:', clickInside, 'click on overlay:', clickOnOverlay);
            
            if (isOpen && !clickInside) {
                if (clickOnOverlay) {
                    console.log('[DEBUG] Clicked on overlay, closing sidebar');
                } else {
                    console.log('[DEBUG] Clicked outside sidebar, closing sidebar');
                }
                sidebar.classList.remove('show');
            }
            // Also close if clicking the main-content while open
            if (isOpen && main && main.contains(e.target) && !sidebar.contains(e.target)) {
                console.log('[DEBUG] Clicked on main content, closing sidebar');
                sidebar.classList.remove('show');
            }
            updateOverlay();
        }, true);
        if (overlay) {
            overlay.addEventListener('click', () => {
                console.log('[DEBUG] Overlay clicked directly');
                const sidebar = document.getElementById('sidebar');
                if (sidebar) sidebar.classList.remove('show');
                updateOverlay();
            });
        }
        // Keep overlay synced when toggling
        const origToggle = this.toggleSidebar.bind(this);
        this.toggleSidebar = () => { 
            console.log('[DEBUG] Wrapped toggleSidebar called');
            origToggle(); 
            updateOverlay(); 
        };
        
        // Initialize overlay state
        updateOverlay();
        
        // Handle window resize for responsive behavior
        window.addEventListener('resize', () => {
            console.log('[DEBUG] Window resized, updating overlay');
            updateOverlay();
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
        document.getElementById('chatInput').addEventListener('input', (e) => this.autoResizeTextarea(e.target));

        // User profile
        document.getElementById('userProfile').addEventListener('click', () => {
            console.log('[DEBUG] User profile clicked');
            this.showUserModal();
        });

        // Settings
        document.getElementById('settingsBtn').addEventListener('click', () => {
            console.log('[DEBUG] Settings clicked');
            this.showSettingsModal();
        });

        // Action buttons
        document.getElementById('exportBtn').addEventListener('click', () => this.exportChat());
        document.getElementById('clearBtn').addEventListener('click', () => this.clearChat());

        // Modal events
        this.setupModalEvents();

        // Theme toggle live
        document.getElementById('themeSelect').addEventListener('change', (e) => {
            console.log('[Theme] change ->', e.target.value);
            this.setTheme(e.target.value);
        });
        // Font size live
        document.getElementById('fontSize').addEventListener('change', (e) => {
            console.log('[Font] change ->', e.target.value);
            this.setFontSize(e.target.value);
        });
        // Other preferences live
        const autoSaveEl = document.getElementById('autoSave');
        const notificationsEl = document.getElementById('notifications');
        if (autoSaveEl) autoSaveEl.addEventListener('change', () => this.savePreferences());
        if (notificationsEl) notificationsEl.addEventListener('change', () => this.savePreferences());
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

    clearChatMessages() {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '';
    }

    updateChatTitle() {
        const titleElement = document.getElementById('chatTitle');
        if (this.currentSession) {
            titleElement.textContent = this.currentSession.title;
        } else {
            titleElement.textContent = 'Medical AI Assistant';
        }
    }

    showModal(modalId) {
        console.log('[DEBUG] showModal called with ID:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            console.log('[DEBUG] Modal shown:', modalId);
        } else {
            console.error('[DEBUG] Modal not found:', modalId);
        }
    }

    hideModal(modalId) {
        console.log('[DEBUG] hideModal called with ID:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            console.log('[DEBUG] Modal hidden:', modalId);
        } else {
            console.error('[DEBUG] Modal not found:', modalId);
        }
    }

    showUserModal() {
        console.log('[DEBUG] showUserModal called');
        this.showModal('userModal');
    }

    showSettingsModal() {
        console.log('[DEBUG] showSettingsModal called');
        this.showModal('settingsModal');
    }

    saveSettings() {
        const theme = document.getElementById('themeSelect').value;
        const fontSize = document.getElementById('fontSize').value;
        const autoSave = document.getElementById('autoSave').checked;
        const notifications = document.getElementById('notifications').checked;

        console.log('[Settings] save', { theme, fontSize, autoSave, notifications });
        this.setTheme(theme);
        this.setFontSize(fontSize);

        // Save additional preferences
        const preferences = {
            theme: theme,
            fontSize: fontSize,
            autoSave: autoSave,
            notifications: notifications
        };
        console.log('[Prefs] write', preferences);
        localStorage.setItem('medicalChatbotPreferences', JSON.stringify(preferences));

        this.hideModal('settingsModal');
    }

    updateUserDisplay() {
        document.getElementById('userName').textContent = this.currentUser.name;
        document.getElementById('userStatus').textContent = this.currentUser.role;
    }

    saveUser() {
        localStorage.setItem('medicalChatbotUser', JSON.stringify(this.currentUser));
    }

    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

// ----------------------------------------------------------
// Additional UI setup START
// Including session.js and settings.js from ui/ and chat/
// -----------------------------
// Our submodules aren't lodaed on app.js, so we need to add them here
// Perhaps this is FastAPI limitation, remove this when proper deploy this
// On UI specific hosting site.
// ----------------------------------------------------------  

    // Additional methods that are called by the modules
    loadUserPreferences() {
        const prefs = JSON.parse(localStorage.getItem('medicalChatbotPreferences') || '{}');
        if (prefs.theme) this.setTheme(prefs.theme);
        if (prefs.fontSize) this.setFontSize(prefs.fontSize);
        if (prefs.autoSave !== undefined) document.getElementById('autoSave').checked = prefs.autoSave;
        if (prefs.notifications !== undefined) document.getElementById('notifications').checked = prefs.notifications;
    }

    setTheme(theme) {
        const root = document.documentElement;
        if (theme === 'auto') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        } else {
            root.setAttribute('data-theme', theme);
        }
    }

    setFontSize(size) {
        const root = document.documentElement;
        const sizes = { small: '14px', medium: '16px', large: '18px' };
        root.style.fontSize = sizes[size] || '16px';
    }

    setupTheme() {
        const themeSelect = document.getElementById('themeSelect');
        if (themeSelect) {
            const prefs = JSON.parse(localStorage.getItem('medicalChatbotPreferences') || '{}');
            themeSelect.value = prefs.theme || 'auto';
        }
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

    getChatSessions() {
        const sessions = localStorage.getItem('medicalChatbotSessions');
        return sessions ? JSON.parse(sessions) : [];
    }

    saveCurrentSession() {
        if (!this.currentSession) return;
        const sessions = this.getChatSessions();
        const existingIndex = sessions.findIndex(s => s.id === this.currentSession.id);
        if (existingIndex >= 0) {
            sessions[existingIndex] = this.currentSession;
        } else {
            sessions.unshift(this.currentSession);
        }
        localStorage.setItem('medicalChatbotSessions', JSON.stringify(sessions));
    }

    loadChatSessions() {
        const sessionsContainer = document.getElementById('chatSessions');
        if (!sessionsContainer) return;

        // Combine backend and local sessions
        const allSessions = [...this.backendSessions, ...this.getChatSessions()];
        
        // Remove duplicates and sort by last activity
        const uniqueSessions = allSessions.reduce((acc, session) => {
            const existing = acc.find(s => s.id === session.id);
            if (!existing) {
                acc.push(session);
            } else if (session.lastActivity > existing.lastActivity) {
                const index = acc.indexOf(existing);
                acc[index] = session;
            }
            return acc;
        }, []);

        uniqueSessions.sort((a, b) => new Date(b.lastActivity) - new Date(a.lastActivity));

        sessionsContainer.innerHTML = '';
        uniqueSessions.forEach(session => {
            const sessionElement = document.createElement('div');
            sessionElement.className = 'chat-session';
            if (this.currentSession && this.currentSession.id === session.id) {
                sessionElement.classList.add('active');
            }
            
            const timeAgo = this.formatTime(session.lastActivity);
            sessionElement.innerHTML = `
                <div class="chat-session-row">
                    <div class="chat-session-meta">
                        <div class="chat-session-title">${session.title}</div>
                        <div class="chat-session-time">${timeAgo}</div>
                    </div>
                    <div class="chat-session-actions">
                        <button class="chat-session-menu" onclick="event.stopPropagation(); this.nextElementSibling.classList.toggle('show')">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <div class="chat-session-menu-popover">
                            <div class="chat-session-menu-item" onclick="window.medicalChatbot.renameChatSession('${session.id}')">
                                <i class="fas fa-edit"></i> Rename
                            </div>
                            <div class="chat-session-menu-item" onclick="window.medicalChatbot.deleteChatSession('${session.id}')">
                                <i class="fas fa-trash"></i> Delete
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            sessionElement.addEventListener('click', () => {
                this.loadChatSession(session.id);
            });
            
            sessionsContainer.appendChild(sessionElement);
        });
    }

    loadChatSession(sessionId) {
        const allSessions = [...this.backendSessions, ...this.getChatSessions()];
        const session = allSessions.find(s => s.id === sessionId);
        if (!session) return;

        this.currentSession = session;
        this.clearChatMessages();
        
        if (session.source === 'backend') {
            this.hydrateMessagesForSession(sessionId);
        } else {
            session.messages.forEach(m => this.displayMessage(m));
        }
        
        this.updateChatTitle();
        this.loadChatSessions();
    }

    renameChatSession(sessionId, newTitle) {
        const allSessions = [...this.backendSessions, ...this.getChatSessions()];
        const session = allSessions.find(s => s.id === sessionId);
        if (session) {
            session.title = newTitle;
            if (session.source === 'backend') {
                // Update backend session
                this.updateBackendSession(sessionId, { title: newTitle });
            } else {
                // Update local session
                this.saveCurrentSession();
            }
            this.loadChatSessions();
            this.updateChatTitle();
        }
    }

    deleteChatSession(sessionId) {
        if (confirm('Are you sure you want to delete this chat session?')) {
            const allSessions = [...this.backendSessions, ...this.getChatSessions()];
            const session = allSessions.find(s => s.id === sessionId);
            
            if (session && session.source === 'backend') {
                // Delete from backend
                this.deleteBackendSession(sessionId);
            } else {
                // Delete from local storage
                const sessions = this.getChatSessions();
                const filtered = sessions.filter(s => s.id !== sessionId);
                localStorage.setItem('medicalChatbotSessions', JSON.stringify(filtered));
            }
            
            if (this.currentSession && this.currentSession.id === sessionId) {
                this.startNewChat();
            } else {
                this.loadChatSessions();
            }
        }
    }

    updateBackendSession(sessionId, updates) {
        // This would call the backend API to update session metadata
        console.log('Updating backend session:', sessionId, updates);
    }

    deleteBackendSession(sessionId) {
        // This would call the backend API to delete the session
        console.log('Deleting backend session:', sessionId);
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            if (show) {
                overlay.classList.add('show');
            } else {
                overlay.classList.remove('show');
            }
        }
        this.isLoading = show;
    }

    updateCurrentSession() {
        if (this.currentSession) {
            this.currentSession.lastActivity = new Date().toISOString();
            this.saveCurrentSession();
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.medicalChatbot = new MedicalChatbotApp();
});


// ----------------------------------------------------------
// Additional UI setup END
// ----------------------------------------------------------    

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