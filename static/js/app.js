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
        const overlay = document.getElementById('sidebarOverlay');
        const updateOverlay = () => {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && overlay) overlay.style.display = sidebar.classList.contains('show') ? 'block' : 'none';
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
        if (overlay) {
            overlay.addEventListener('click', () => {
                const sidebar = document.getElementById('sidebar');
                if (sidebar) sidebar.classList.remove('show');
                updateOverlay();
            });
        }
        // Keep overlay synced when toggling
        const origToggle = this.toggleSidebar.bind(this);
        this.toggleSidebar = () => { origToggle(); updateOverlay(); };

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
            this.showUserModal();
        });

        // Settings
        document.getElementById('settingsBtn').addEventListener('click', () => {
            this.showSettingsModal();
        });

        // Action buttons
        document.getElementById('exportBtn').addEventListener('click', () => this.exportChat());
        document.getElementById('clearBtn').addEventListener('click', () => this.clearChat());

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
}

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
