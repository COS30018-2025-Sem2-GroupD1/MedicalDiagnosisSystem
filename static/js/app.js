// Medical AI Assistant - Main Application JavaScript
import { attachUIHandlers } from './ui/handlers.js';
import { attachDoctorUI } from './ui/doctor.js';
import { attachPatientUI } from './ui/patient.js';
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

        // Patient handlers moved to ui/patient.js

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


    clearChatMessages() {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '';
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
