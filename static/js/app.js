// Medical AI Assistant - Main Application JavaScript
// static/js/app.js

// TEMPORARILY DISABLED SUBMODULES
// import { attachUIHandlers } from './ui/handlers.js';
// import { attachDoctorUI } from './ui/doctor.js';
// import { attachPatientUI } from './ui/patient.js';
// import { attachSettingsUI } from './ui/settings.js';
// import { attachSessionsUI } from './chat/sessions.js';
// import { attachMessagingUI } from './chat/messaging.js';

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
        // // TEMPORARILY DISABLED SUBMODULES ATTACHMENT
        // attachUIHandlers(this);
        // // Attach specialized UIs
        // attachDoctorUI(this);
        // attachPatientUI(this);
        // attachSettingsUI(this);
        // attachSessionsUI(this);
        // attachMessagingUI(this);
        this.setupEventListeners();
        this.loadUserPreferences();
        this.initializeUser();
        await this.loadSavedPatientId();

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
        this.setupPatientModal();
        // Apply saved theme immediately
        const prefs = JSON.parse(localStorage.getItem('medicalChatbotPreferences') || '{}');
        this.setTheme(prefs.theme || 'auto');
        this.setupTheme();
    }

    setupEventListeners() {
        // Sidebar toggle
        const sidebarToggle = document.getElementById('sidebarToggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => {
            this.toggleSidebar();
        });
        }
        
        // Click outside sidebar to close (mobile/overlay behavior)
        const overlay = document.getElementById('appOverlay');
        console.log('[DEBUG] Overlay element found:', !!overlay);
        const updateOverlay = () => {
            const sidebar = document.getElementById('sidebar');
            const isOpen = sidebar && sidebar.classList.contains('show');
            console.log('[DEBUG] Updating overlay - sidebar open:', isOpen);
            if (overlay) {
                if (isOpen) {
                    overlay.classList.add('show');
                    console.log('[DEBUG] Overlay shown');
                } else {
                    overlay.classList.remove('show');
                    console.log('[DEBUG] Overlay hidden');
                }
            }
        };
        
        // Keep overlay synced when toggling
        const origToggle = this.toggleSidebar.bind(this);
        this.toggleSidebar = () => { 
            console.log('[DEBUG] Wrapped toggleSidebar called');
            origToggle(); 
            updateOverlay(); 
        };
        
        // Initialize overlay state - ensure it's hidden on startup
        if (overlay) {
            overlay.classList.remove('show');
        }
        updateOverlay();
        
        // Handle window resize for responsive behavior
        window.addEventListener('resize', () => {
            console.log('[DEBUG] Window resized, updating overlay');
            updateOverlay();
        });
        
        // Click outside to close sidebar
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

        // New chat button
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
            this.startNewChat();
        });
        }

        // Send button and input
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
            this.sendMessage();
        });
        }

        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
            chatInput.addEventListener('input', (e) => this.autoResizeTextarea(e.target));
        }

        // User profile
        const userProfile = document.getElementById('userProfile');
        if (userProfile) {
            userProfile.addEventListener('click', () => {
                console.log('[DEBUG] User profile clicked');
            this.showUserModal();
        });
        }

        // Settings
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                console.log('[DEBUG] Settings clicked');
            this.showSettingsModal();
        });
        }

        // Action buttons
        const exportBtn = document.getElementById('exportBtn');
        const clearBtn = document.getElementById('clearBtn');
        if (exportBtn) exportBtn.addEventListener('click', () => this.exportChat());
        if (clearBtn) clearBtn.addEventListener('click', () => this.clearChat());

        // Modal events
        this.setupModalEvents();

        // Theme toggle live
        const themeSelect = document.getElementById('themeSelect');
        if (themeSelect) {
            themeSelect.addEventListener('change', (e) => {
                console.log('[Theme] change ->', e.target.value);
            this.setTheme(e.target.value);
        });
        }
        // Font size live
        const fontSize = document.getElementById('fontSize');
        if (fontSize) {
            fontSize.addEventListener('change', (e) => {
                console.log('[Font] change ->', e.target.value);
                this.setFontSize(e.target.value);
            });
        }
        // Other preferences live
        const autoSaveEl = document.getElementById('autoSave');
        const notificationsEl = document.getElementById('notifications');
        if (autoSaveEl) autoSaveEl.addEventListener('change', () => this.savePreferences());
        if (notificationsEl) notificationsEl.addEventListener('change', () => this.savePreferences());
    }

    setupModalEvents() {
        // User modal
        const userModalClose = document.getElementById('userModalClose');
        const userModalCancel = document.getElementById('userModalCancel');
        const userModalSave = document.getElementById('userModalSave');
        
        if (userModalClose) {
            userModalClose.addEventListener('click', () => {
            this.hideModal('userModal');
        });
        }

        if (userModalCancel) {
            userModalCancel.addEventListener('click', () => {
            this.hideModal('userModal');
        });
        }

        if (userModalSave) {
            userModalSave.addEventListener('click', () => {
            this.saveUserProfile();
        });
        }

        // Settings modal
        const settingsModalClose = document.getElementById('settingsModalClose');
        const settingsModalCancel = document.getElementById('settingsModalCancel');
        const settingsModalSave = document.getElementById('settingsModalSave');
        
        if (settingsModalClose) {
            settingsModalClose.addEventListener('click', () => {
            this.hideModal('settingsModal');
        });
        }

        if (settingsModalCancel) {
            settingsModalCancel.addEventListener('click', () => {
            this.hideModal('settingsModal');
        });
        }

        if (settingsModalSave) {
            settingsModalSave.addEventListener('click', () => {
            this.saveSettings();
        });
        }

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
            const editTitleModalClose = document.getElementById('editTitleModalClose');
            const editTitleModalCancel = document.getElementById('editTitleModalCancel');
            const editTitleModalSave = document.getElementById('editTitleModalSave');
            
            if (editTitleModalClose) editTitleModalClose.addEventListener('click', closeEdit);
            if (editTitleModalCancel) editTitleModalCancel.addEventListener('click', closeEdit);
            if (editTitleModalSave) {
                editTitleModalSave.addEventListener('click', () => {
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
// -----------------------------
// Our submodules aren't lodaed on app.js, so we need to add them here
// Perhaps this is FastAPI limitation, remove this when proper deploy this
// On UI specific hosting site.
// ----------------------------------------------------------  


    // ================================================================================
    // HANDLERS.JS FUNCTIONALITY
    // ================================================================================
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        console.log('[DEBUG] toggleSidebar called');
        if (sidebar) {
            const wasOpen = sidebar.classList.contains('show');
            sidebar.classList.toggle('show');
            const isNowOpen = sidebar.classList.contains('show');
            console.log('[DEBUG] Sidebar toggled - was open:', wasOpen, 'now open:', isNowOpen);
            } else {
            console.error('[DEBUG] Sidebar element not found');
        }
    }

    autoResizeTextarea(textarea) {
        if (!textarea) return;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    exportChat() {
        if (!this.currentSession || this.currentSession.messages.length === 0) {
            alert('No chat to export.');
            return;
        }
        const chatData = {
            user: this.currentUser?.name || 'Unknown',
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
        this.populateDoctorSelect();
        const sel = document.getElementById('profileNameSelect');
        if (sel && sel.options.length === 0) {
            const createOpt = document.createElement('option');
            createOpt.value = '__create__';
            createOpt.textContent = 'Create doctor user...';
            sel.appendChild(createOpt);
        }
        if (sel && !sel.value) sel.value = this.currentUser?.name || '__create__';
        
        // Safely set role and specialty with null checks
        const roleEl = document.getElementById('profileRole');
        const specialtyEl = document.getElementById('profileSpecialty');
        if (roleEl) roleEl.value = (this.currentUser && this.currentUser.role) ? this.currentUser.role : 'Medical Professional';
        if (specialtyEl) specialtyEl.value = (this.currentUser && this.currentUser.specialty) ? this.currentUser.specialty : '';
        
        // Add event listener for doctor selection changes
        this.setupDoctorSelectionHandler();
        
        this.showModal('userModal');
    }

    setupDoctorSelectionHandler() {
        const sel = document.getElementById('profileNameSelect');
        const roleEl = document.getElementById('profileRole');
        const specialtyEl = document.getElementById('profileSpecialty');
        
        if (!sel || !roleEl || !specialtyEl) return;
        
        // Remove existing listeners to avoid duplicates
        sel.removeEventListener('change', this.handleDoctorSelection);
        
        // Add new listener
        this.handleDoctorSelection = async (event) => {
            const selectedName = event.target.value;
            console.log('[DEBUG] Doctor selected:', selectedName);
            
            if (selectedName === '__create__') {
                // Reset to default values for new doctor
                roleEl.value = 'Medical Professional';
                specialtyEl.value = '';
                return;
            }
            
            // Find the selected doctor in our doctors list
            const selectedDoctor = this.doctors.find(d => d.name === selectedName);
            if (selectedDoctor) {
                // Update role and specialty from the selected doctor
                if (selectedDoctor.role) {
                    roleEl.value = selectedDoctor.role;
                }
                if (selectedDoctor.specialty) {
                    specialtyEl.value = selectedDoctor.specialty;
                }
                console.log('[DEBUG] Updated role and specialty for doctor:', selectedName, selectedDoctor.role, selectedDoctor.specialty);
            } else {
                // If doctor not found in local list, try to fetch from backend
                try {
                    const resp = await fetch(`/doctors/search?q=${encodeURIComponent(selectedName)}&limit=1`);
                    if (resp.ok) {
                        const data = await resp.json();
                        const doctor = data.results && data.results[0];
                        if (doctor) {
                            if (doctor.role) {
                                roleEl.value = doctor.role;
                            }
                            if (doctor.specialty) {
                                specialtyEl.value = doctor.specialty;
                            }
                            console.log('[DEBUG] Fetched and updated role/specialty from backend:', doctor.role, doctor.specialty);
                        }
                    }
                } catch (e) {
                    console.warn('Failed to fetch doctor details from backend:', e);
                }
            }
        };
        
        sel.addEventListener('change', this.handleDoctorSelection);
    }

    showSettingsModal() {
        console.log('[DEBUG] showSettingsModal called');
        this.showModal('settingsModal');
    }
    

    // ================================================================================
    // SETTINGS.JS FUNCTIONALITY
    // ================================================================================
    loadUserPreferences() {
        const prefs = JSON.parse(localStorage.getItem('medicalChatbotPreferences') || '{}');
        if (prefs.theme) this.setTheme(prefs.theme);
        if (prefs.fontSize) this.setFontSize(prefs.fontSize);
        if (prefs.autoSave !== undefined) document.getElementById('autoSave').checked = prefs.autoSave;
        if (prefs.notifications !== undefined) document.getElementById('notifications').checked = prefs.notifications;
    }

    setTheme(theme) {
        const root = document.documentElement;
        console.log('[Theme] Setting theme to:', theme);
        if (theme === 'auto') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
            console.log('[Theme] Auto theme applied:', prefersDark ? 'dark' : 'light');
        } else {
            root.setAttribute('data-theme', theme);
            console.log('[Theme] Manual theme applied:', theme);
        }
        // Force a re-render by toggling a class
        root.classList.add('theme-updated');
        setTimeout(() => root.classList.remove('theme-updated'), 100);
    }

    setFontSize(size) {
        const root = document.documentElement;
        const sizes = { small: '14px', medium: '16px', large: '18px' };
        const fontSize = sizes[size] || '16px';
        console.log('[Font] Setting font size to:', fontSize);
        root.style.fontSize = fontSize;
        // Force a re-render
        root.classList.add('font-updated');
        setTimeout(() => root.classList.remove('font-updated'), 100);
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


    // ================================================================================
    // SESSIONS.JS FUNCTIONALITY
    // ================================================================================
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

    loadChatSessions() {
        const sessionsContainer = document.getElementById('chatSessions');
        sessionsContainer.innerHTML = '';
        const sessions = (this.backendSessions && this.backendSessions.length > 0) ? this.backendSessions : this.getChatSessions();
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

    updateChatTitle() {
        const titleElement = document.getElementById('chatTitle');
        if (this.currentSession) {
            titleElement.textContent = this.currentSession.title;
        } else {
            titleElement.textContent = 'Medical AI Assistant';
        }
    }

    async switchToSession(session) {
        console.log('[DEBUG] Switching to session:', session.id, session.source);
        this.currentSession = { ...session };
        this.clearChatMessages();
        
        if (session.source === 'backend') {
            // For backend sessions, always fetch fresh messages
            await this.hydrateMessagesForSession(session.id);
        } else {
            // For local sessions, load from localStorage
            const localSessions = this.getChatSessions();
            const localSession = localSessions.find(s => s.id === session.id);
            if (localSession && localSession.messages) {
                // Sort messages by timestamp
                const sortedMessages = localSession.messages.sort((a, b) => {
                    const timeA = new Date(a.timestamp || 0).getTime();
                    const timeB = new Date(b.timestamp || 0).getTime();
                    return timeA - timeB; // Ascending order for display
                });
                sortedMessages.forEach(message => this.displayMessage(message));
                // Check if session needs title generation
                this.checkAndGenerateSessionTitle();
            }
        }
        
        this.updateChatTitle();
        this.loadChatSessions(); // Re-render to update active state
    }

    loadChatSession(sessionId) {
        const sessions = this.getChatSessions();
        const session = sessions.find(s => s.id === sessionId);
        if (!session) return;
        this.switchToSession(session);
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

    deleteChatSession(sessionId) {
        const sessions = this.getChatSessions();
        const index = sessions.findIndex(s => s.id === sessionId);
        if (index === -1) return;
        const confirmDelete = confirm('Delete this chat session? This cannot be undone.');
        if (!confirmDelete) return;
        sessions.splice(index, 1);
        localStorage.setItem(`chatSessions_${this.currentUser.id}`, JSON.stringify(sessions));
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
                if (action === 'delete') this.deleteChatSession(id);
                else if (action === 'edit') {
                    this._pendingEditSessionId = id;
                    const sessions = this.getChatSessions();
                    const s = sessions.find(x => x.id === id);
                    const input = document.getElementById('editSessionTitleInput');
                    if (input) input.value = s ? s.title : '';
                    this.showModal('editTitleModal');
                }
                pop.remove();
            });
        });
    }

    updateBackendSession(sessionId, updates) {
        // This would call the backend API to update session metadata
        console.log('Updating backend session:', sessionId, updates);
    }

    deleteBackendSession(sessionId) {
        // This would call the backend API to delete the session
        console.log('Deleting backend session:', sessionId);
    }

    updateCurrentSession() {
        if (this.currentSession) {
            this.currentSession.lastActivity = new Date().toISOString();
            this.saveCurrentSession();
        }
    }


    // ================================================================================
    // DOCTOR.JS FUNCTIONALITY
    // ================================================================================
    async loadDoctors() {
        try {
            // Fetch doctors from MongoDB
            const resp = await fetch('/doctors');
            if (resp.ok) {
                const data = await resp.json();
                this.doctors = data.results || [];
                // Ensure each doctor has role and specialty information
                this.doctors = this.doctors.map(doctor => ({
                    name: doctor.name,
                    role: doctor.role || 'Medical Professional',
                    specialty: doctor.specialty || '',
                    _id: doctor._id || doctor.doctor_id
                }));
                // Also save to localStorage for offline access
                localStorage.setItem('medicalChatbotDoctors', JSON.stringify(this.doctors));
                console.log('[DEBUG] Loaded doctors with role/specialty:', this.doctors);
                return this.doctors;
            } else {
                // Fallback to localStorage if API fails
                const raw = localStorage.getItem('medicalChatbotDoctors');
                const arr = raw ? JSON.parse(raw) : [];
                const seen = new Set();
                this.doctors = arr.filter(x => x && x.name && !seen.has(x.name) && seen.add(x.name));
                return this.doctors;
            }
        } catch (e) {
            console.warn('Failed to load doctors from API, using localStorage fallback:', e);
            // Fallback to localStorage
            const raw = localStorage.getItem('medicalChatbotDoctors');
            const arr = raw ? JSON.parse(raw) : [];
            const seen = new Set();
            this.doctors = arr.filter(x => x && x.name && !seen.has(x.name) && seen.add(x.name));
            return this.doctors;
        }
    }

    async searchDoctors(query) {
        try {
            const resp = await fetch(`/doctors/search?q=${encodeURIComponent(query)}&limit=10`);
            if (resp.ok) {
                const data = await resp.json();
                return data.results || [];
            }
        } catch (e) {
            console.warn('Doctor search failed:', e);
        }
        return [];
    }

    async createDoctor(doctorData) {
        try {
            const resp = await fetch('/doctors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(doctorData)
            });
            if (resp.ok) {
                const data = await resp.json();
                // Add to local doctors list
                this.doctors.push({ name: data.name, _id: data.doctor_id });
                this.saveDoctors();
                return data;
            }
        } catch (e) {
            console.error('Failed to create doctor:', e);
        }
        return null;
    }

    saveDoctors() {
        localStorage.setItem('medicalChatbotDoctors', JSON.stringify(this.doctors));
    }

    async populateDoctorSelect() {
        const sel = document.getElementById('profileNameSelect');
        const newSec = document.getElementById('newDoctorSection');
        if (!sel) return;
        
        // Load doctors from MongoDB
        await this.loadDoctors();
        
        sel.innerHTML = '';
        const createOpt = document.createElement('option');
        createOpt.value = '__create__';
        createOpt.textContent = 'Create doctor user...';
        sel.appendChild(createOpt);
        // Ensure no duplicates, include current doctor
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
                // Trigger doctor selection handler to update role/specialty
                if (this.handleDoctorSelection) {
                    this.handleDoctorSelection({ target: sel });
                }
            }
        });
        const cancelBtn = document.getElementById('cancelNewDoctor');
        const confirmBtn = document.getElementById('confirmNewDoctor');
        if (cancelBtn) cancelBtn.onclick = () => { newSec.style.display = 'none'; sel.value = this.currentUser?.name || ''; };
        if (confirmBtn) confirmBtn.onclick = async () => {
            const name = (document.getElementById('newDoctorName').value || '').trim();
            if (!name) return;
            if (!this.doctors.find(d => d.name === name)) {
                // Get current role and specialty from the form
                const role = document.getElementById('profileRole').value || 'Medical Professional';
                const specialty = document.getElementById('profileSpecialty').value.trim() || '';
                
                // Create doctor in MongoDB
                const result = await this.createDoctor({ 
                    name, 
                    role, 
                    specialty,
                    medical_roles: [role]
                });
                if (result) {
                    this.doctors.unshift({ 
                        name, 
                        role, 
                        specialty, 
                        _id: result.doctor_id 
                    });
                    this.saveDoctors();
                    
                    // Update current user profile
                    this.currentUser.name = name;
                    this.currentUser.role = role;
                    this.currentUser.specialty = specialty;
                    this.saveUser();
                    this.updateUserDisplay();
                }
            }
            await this.populateDoctorSelect();
            sel.value = name;
            newSec.style.display = 'none';
        };
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

        // Check if this is a new doctor creation (not in our local list)
        const existingDoctorIndex = this.doctors.findIndex(d => d.name === name);
        const isNewDoctor = existingDoctorIndex === -1;

        // Update local doctors list
        if (isNewDoctor) {
            // Add new doctor to local list
            this.doctors.unshift({ 
                name, 
                role, 
                specialty 
            });
        } else {
            // Update existing doctor in local list
            this.doctors[existingDoctorIndex] = {
                ...this.doctors[existingDoctorIndex],
                role: role,
                specialty: specialty
            };
        }
        this.saveDoctors();

        // Update current user profile
        this.currentUser.name = name;
        this.currentUser.role = role;
        this.currentUser.specialty = specialty;
        this.saveUser();
        this.updateUserDisplay();

        // Only create new doctor in MongoDB if it's actually a new doctor
        if (isNewDoctor) {
            const doctorPayload = {
                name: name,
                role: role,
                specialty: specialty || null,
                medical_roles: [role]
            };
            
            fetch('/doctors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(doctorPayload)
            }).then(resp => {
                if (!resp.ok) throw new Error('Failed to create doctor in backend');
                return resp.json();
            }).then((data) => {
                console.log('[Doctor] Created new doctor in backend:', data);
                // Update local doctor with the ID from backend
                const localDoctor = this.doctors.find(d => d.name === name);
                if (localDoctor) {
                    localDoctor._id = data.doctor_id;
                    this.saveDoctors();
                }
            }).catch(err => {
                console.warn('[Doctor] failed to create doctor in backend:', err);
            });
        } else {
            console.log('[Doctor] Updated existing doctor profile locally (no backend call needed)');
        }

        this.hideModal('userModal');
    }

    // ================================================================================
    // PATIENT.JS FUNCTIONALITY
    // ================================================================================
    
    async getLocalStorageSuggestions(query) {
        try {
            const storedPatients = JSON.parse(localStorage.getItem('medicalChatbotPatients') || '[]');
            return storedPatients.filter(p => {
                // Check name match (case-insensitive contains)
                const nameMatch = p.name.toLowerCase().includes(query.toLowerCase());
                // Check patient_id match
                let idMatch = p.patient_id.includes(query);
                // Special handling for numeric queries - check if patient_id starts with the query
                if (/^\d+$/.test(query)) {
                    idMatch = p.patient_id.startsWith(query) || p.patient_id.includes(query);
                }
                return nameMatch || idMatch;
            });
        } catch (e) {
            console.warn('Failed to get localStorage suggestions:', e);
            return [];
        }
    }

    combinePatientResults(mongoResults, localResults) {
        // Create a map to deduplicate by patient_id, with MongoDB results taking priority
        const resultMap = new Map();
        
        // Add MongoDB results first (they take priority)
        mongoResults.forEach(patient => {
            resultMap.set(patient.patient_id, patient);
        });
        
        // Add localStorage results only if not already present
        localResults.forEach(patient => {
            if (!resultMap.has(patient.patient_id)) {
                resultMap.set(patient.patient_id, patient);
            }
        });
        
        return Array.from(resultMap.values());
    }

    async tryFallbackSearch(query, renderSuggestions) {
        // Use localStorage for fallback suggestions
        try {
            const localResults = await this.getLocalStorageSuggestions(query);
            if (localResults.length > 0) {
                console.log('[DEBUG] Fallback search found matches from localStorage:', localResults);
                renderSuggestions(localResults);
            } else {
                console.log('[DEBUG] No fallback matches found');
                renderSuggestions([]);
            }
        } catch (e) {
            console.warn('Fallback search failed:', e);
            renderSuggestions([]);
        }
    }
    async loadSavedPatientId() {
        const pid = localStorage.getItem('medicalChatbotPatientId');
        if (pid && /^\d{8}$/.test(pid)) {
            this.currentPatientId = pid;
            const status = document.getElementById('patientStatus');
            const actions = document.getElementById('patientActions');
            const emrLink = document.getElementById('emrLink');
            
            if (status) {
                // Try to fetch patient name
                try {
                    const resp = await fetch(`/patients/${pid}`);
                    if (resp.ok) {
                        const patient = await resp.json();
                        status.textContent = `Patient: ${patient.name || 'Unknown'} (${pid})`;
                    } else {
                        status.textContent = `Patient: ${pid}`;
                    }
                } catch (e) {
                    status.textContent = `Patient: ${pid}`;
                }
                status.style.color = 'var(--text-secondary)';
            }
            
            // Show EMR link
            if (actions) actions.style.display = 'block';
            if (emrLink) emrLink.href = `/static/emr.html?patient_id=${pid}`;
            
            const input = document.getElementById('patientIdInput');
            if (input) input.value = pid;
        }
    }

    savePatientId() {
        if (this.currentPatientId) localStorage.setItem('medicalChatbotPatientId', this.currentPatientId);
        else localStorage.removeItem('medicalChatbotPatientId');
    }

    updatePatientDisplay(patientId, patientName = null) {
        const status = document.getElementById('patientStatus');
        const actions = document.getElementById('patientActions');
        const emrLink = document.getElementById('emrLink');
        
        if (status) {
            if (patientName) {
                status.textContent = `Patient: ${patientName} (${patientId})`;
        } else {
                status.textContent = `Patient: ${patientId}`;
            }
            status.style.color = 'var(--text-secondary)';
        }
        
        // Show EMR link
        if (actions) actions.style.display = 'block';
        if (emrLink) emrLink.href = `/static/emr.html?patient_id=${patientId}`;
    }

    loadPatient = async function () {
        console.log('[DEBUG] loadPatient called');
        const input = document.getElementById('patientIdInput');
        const status = document.getElementById('patientStatus');
        const value = (input?.value || '').trim();
        console.log('[DEBUG] Patient input value:', value);
        
        if (!value) {
            console.log('[DEBUG] No input provided');
            if (status) { status.textContent = 'Please enter patient ID or name.'; status.style.color = 'var(--warning-color)'; }
            return;
        }
        
        // If it's a complete 8-digit ID, use it directly
        if (/^\d{8}$/.test(value)) {
            console.log('[DEBUG] Valid 8-digit ID provided');
            this.currentPatientId = value;
            this.savePatientId();
            // Try to get patient name for display
            try {
                const resp = await fetch(`/patients/${value}`);
                if (resp.ok) {
                    const patient = await resp.json();
                    this.updatePatientDisplay(value, patient.name || 'Unknown');
            } else {
                    this.updatePatientDisplay(value);
                }
            } catch (e) {
                this.updatePatientDisplay(value);
            }
            await this.fetchAndRenderPatientSessions();
            return;
        }
        
        // Otherwise, search for patient by name or partial ID
        console.log('[DEBUG] Searching for patient by name/partial ID');
        try {
            const resp = await fetch(`/patients/search?q=${encodeURIComponent(value)}&limit=1`);
            console.log('[DEBUG] Search response status:', resp.status);
            if (resp.ok) {
                const data = await resp.json();
                console.log('[DEBUG] Search results:', data);
                const first = (data.results || [])[0];
                if (first) {
                    console.log('[DEBUG] Found patient, setting as current:', first);
                    this.currentPatientId = first.patient_id;
                    this.savePatientId();
                    input.value = first.patient_id;
                    this.updatePatientDisplay(first.patient_id, first.name || 'Unknown');
                    await this.fetchAndRenderPatientSessions();
                    return;
                }
            }
        } catch (e) {
            console.error('[DEBUG] Search error:', e);
        }
        
        // No patient found
        console.log('[DEBUG] No patient found');
        if (status) { status.textContent = 'No patient found. Try a different search.'; status.style.color = 'var(--warning-color)'; }
    }

    fetchAndRenderPatientSessions = async function () {
        if (!this.currentPatientId) return;
        
        // Check localStorage cache first
        const cacheKey = `sessions_${this.currentPatientId}`;
        const cached = localStorage.getItem(cacheKey);
        let sessions = [];
        
        if (cached) {
            try {
                const cachedData = JSON.parse(cached);
                // Check if cache is recent (less than 2 minutes old)
                const cacheTime = new Date(cachedData.timestamp || 0).getTime();
                const now = new Date().getTime();
                if (now - cacheTime < 2 * 60 * 1000) { // 2 minutes
                    sessions = cachedData.sessions || [];
                    console.log('[DEBUG] Using cached sessions for patient:', this.currentPatientId);
                }
            } catch (e) {
                console.warn('Failed to parse cached sessions:', e);
            }
        }
        
        // If no cache or cache is stale, fetch from backend
        if (sessions.length === 0) {
            try {
                const resp = await fetch(`/patients/${this.currentPatientId}/sessions`);
                if (resp.ok) {
                    const data = await resp.json();
                    sessions = Array.isArray(data.sessions) ? data.sessions : [];
                    
                    // Cache the sessions
                    localStorage.setItem(cacheKey, JSON.stringify({
                        sessions: sessions,
                        timestamp: new Date().toISOString()
                    }));
                    console.log('[DEBUG] Cached sessions for patient:', this.currentPatientId);
                } else {
                    console.warn('Failed to fetch patient sessions', resp.status);
                }
            } catch (e) {
                console.error('Failed to load patient sessions', e);
            }
        }
        
        // Process sessions
        this.backendSessions = sessions.map(s => ({
            id: s.session_id,
            title: s.title || 'New Chat',
            messages: [],
            createdAt: s.created_at || new Date().toISOString(),
            lastActivity: s.last_activity || new Date().toISOString(),
            source: 'backend'
        }));
        
        if (this.backendSessions.length > 0) {
            this.currentSession = this.backendSessions[0];
            await this.hydrateMessagesForSession(this.currentSession.id);
        }
        
        this.loadChatSessions();
    }

    hydrateMessagesForSession = async function (sessionId) {
        try {
            // Check localStorage cache first
            const cacheKey = `messages_${this.currentPatientId}_${sessionId}`;
            const cached = localStorage.getItem(cacheKey);
            let messages = [];
            
            if (cached) {
                try {
                    const cachedData = JSON.parse(cached);
                    // Check if cache is recent (less than 5 minutes old)
                    const cacheTime = new Date(cachedData.timestamp || 0).getTime();
                    const now = new Date().getTime();
                    if (now - cacheTime < 5 * 60 * 1000) { // 5 minutes
                        messages = cachedData.messages || [];
                        console.log('[DEBUG] Using cached messages for session:', sessionId);
                    }
                } catch (e) {
                    console.warn('Failed to parse cached messages:', e);
                }
            }
            
            // If no cache or cache is stale, fetch from backend
            if (messages.length === 0) {
                const resp = await fetch(`/sessions/${sessionId}/messages?patient_id=${this.currentPatientId}&limit=1000`);
                if (!resp.ok) return;
                const data = await resp.json();
                const msgs = Array.isArray(data.messages) ? data.messages : [];
                messages = msgs.map(m => ({
                    id: m._id || this.generateId(),
                    role: m.role,
                    content: m.content,
                    timestamp: m.timestamp
                }));
                
                // Cache the messages
                localStorage.setItem(cacheKey, JSON.stringify({
                    messages: messages,
                    timestamp: new Date().toISOString()
                }));
                console.log('[DEBUG] Cached messages for session:', sessionId);
            }
            
            // Sort messages by timestamp (ascending order for display)
            const sortedMessages = messages.sort((a, b) => {
                const timeA = new Date(a.timestamp || 0).getTime();
                const timeB = new Date(b.timestamp || 0).getTime();
                return timeA - timeB;
            });
            
            if (this.currentSession && this.currentSession.id === sessionId) {
                this.currentSession.messages = sortedMessages;
                this.clearChatMessages();
                this.currentSession.messages.forEach(m => this.displayMessage(m));
                this.updateChatTitle();
                // Check if session needs title generation
                this.checkAndGenerateSessionTitle();
            }
        } catch (e) {
            console.error('Failed to hydrate session messages', e);
        }
    }

    bindPatientHandlers() {
        console.log('[DEBUG] bindPatientHandlers called');
        const loadBtn = document.getElementById('loadPatientBtn');
        console.log('[DEBUG] Load button found:', !!loadBtn);
        if (loadBtn) loadBtn.addEventListener('click', () => this.loadPatient());
        const patientInput = document.getElementById('patientIdInput');
        const suggestionsEl = document.getElementById('patientSuggestions');
        console.log('[DEBUG] Patient input found:', !!patientInput);
        console.log('[DEBUG] Suggestions element found:', !!suggestionsEl);
        if (!patientInput) return;
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
                div.addEventListener('click', async () => {
                    this.currentPatientId = p.patient_id;
                    this.savePatientId();
                    patientInput.value = p.patient_id;
                    hideSuggestions();
                    this.updatePatientDisplay(p.patient_id, p.name || 'Unknown');
                    await this.fetchAndRenderPatientSessions();
                });
                suggestionsEl.appendChild(div);
            });
            suggestionsEl.style.display = 'block';
        };
        patientInput.addEventListener('input', () => {
            const q = patientInput.value.trim();
            console.log('[DEBUG] Patient input changed:', q);
            clearTimeout(debounceTimer);
            if (!q) { hideSuggestions(); return; }
            debounceTimer = setTimeout(async () => {
                try {
                    console.log('[DEBUG] Searching patients with query:', q);
                    const url = `/patients/search?q=${encodeURIComponent(q)}&limit=8`;
                    console.log('[DEBUG] Search URL:', url);
                    const resp = await fetch(url);
                    console.log('[DEBUG] Search response status:', resp.status);
                    
                    let mongoResults = [];
                    if (resp.ok) {
                        const data = await resp.json();
                        mongoResults = data.results || [];
                        console.log('[DEBUG] MongoDB search results:', mongoResults);
                    } else {
                        console.warn('MongoDB search request failed', resp.status);
                    }
                    
                    // Get localStorage suggestions as fallback/additional results
                    const localResults = await this.getLocalStorageSuggestions(q);
                    
                    // Combine and deduplicate results (MongoDB results take priority)
                    const combinedResults = this.combinePatientResults(mongoResults, localResults);
                    console.log('[DEBUG] Combined search results:', combinedResults);
                    renderSuggestions(combinedResults);
                    
                } catch (e) { 
                    console.error('[DEBUG] Search error:', e);
                    // Fallback for network errors
                    console.log('[DEBUG] Trying fallback search after error');
                    await this.tryFallbackSearch(q, renderSuggestions);
                }
            }, 200);
        });
        patientInput.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter') {
                const value = patientInput.value.trim();
                console.log('[DEBUG] Patient input Enter pressed with value:', value);
                hideSuggestions();
                await this.loadPatient();
            }
        });
        document.addEventListener('click', (ev) => {
            if (!suggestionsEl) return;
            if (!suggestionsEl.contains(ev.target) && ev.target !== patientInput) hideSuggestions();
        });
    }

    // Patient modal functionality
    setupPatientModal() {
        const profileBtn = document.getElementById('patientMenuBtn');
        const modal = document.getElementById('patientModal');
        const closeBtn = document.getElementById('patientModalClose');
        const logoutBtn = document.getElementById('patientLogoutBtn');
        const createBtn = document.getElementById('patientCreateBtn');
        
        if (profileBtn && modal) {
            profileBtn.addEventListener('click', async () => {
                const pid = this?.currentPatientId;
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
                    this.currentPatientId = null;
                    localStorage.removeItem('medicalChatbotPatientId');
                    const status = document.getElementById('patientStatus');
                    if (status) { status.textContent = 'No patient selected'; status.style.color = 'var(--text-secondary)'; }
                    const input = document.getElementById('patientIdInput');
                    if (input) input.value = '';
                    modal.classList.remove('show');
                }
            });
        }
        
        if (createBtn) createBtn.addEventListener('click', () => modal.classList.remove('show'));
    }

    // ================================================================================
    // MESSAGING.JS FUNCTIONALITY
    // ================================================================================
    // Cache invalidation methods
    invalidateSessionCache(patientId) {
        const cacheKey = `sessions_${patientId}`;
        localStorage.removeItem(cacheKey);
        console.log('[DEBUG] Invalidated session cache for patient:', patientId);
    }

    invalidateMessageCache(patientId, sessionId) {
        const cacheKey = `messages_${patientId}_${sessionId}`;
        localStorage.removeItem(cacheKey);
        console.log('[DEBUG] Invalidated message cache for session:', sessionId);
    }

    invalidateAllCaches(patientId) {
        this.invalidateSessionCache(patientId);
        // Invalidate all message caches for this patient
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith(`messages_${patientId}_`)) {
                localStorage.removeItem(key);
            }
        });
        console.log('[DEBUG] Invalidated all caches for patient:', patientId);
    }

    sendMessage = async function () {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        if (!message || this.isLoading) return;
        if (!this.currentPatientId) {
            const status = document.getElementById('patientStatus');
            if (status) { status.textContent = 'Select a patient before chatting.'; status.style.color = 'var(--warning-color)'; }
            return;
        }
        input.value = '';
        this.autoResizeTextarea(input);
        this.addMessage('user', message);
        this.showLoading(true);
        try {
            const response = await this.callMedicalAPI(message);
            this.addMessage('assistant', response);
            this.updateCurrentSession();
            
            // Invalidate caches after successful message exchange
            if (this.currentSession && this.currentSession.id) {
                this.invalidateMessageCache(this.currentPatientId, this.currentSession.id);
                this.invalidateSessionCache(this.currentPatientId);
            }
        } catch (error) {
            console.error('Error sending message:', error);
            let errorMessage = 'I apologize, but I encountered an error processing your request.';
            if (error.message.includes('500')) errorMessage = 'The server encountered an internal error. Please try again in a moment.';
            else if (error.message.includes('404')) errorMessage = 'The requested service was not found. Please check your connection.';
            else if (error.message.includes('fetch')) errorMessage = 'Unable to connect to the server. Please check your internet connection.';
            this.addMessage('assistant', errorMessage);
        } finally {
            this.showLoading(false);
        }
    }

    callMedicalAPI = async function (message) {
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return data.response || 'I apologize, but I received an empty response. Please try again.';
        } catch (error) {
            console.error('API call failed:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                user: this.currentUser,
                session: this.currentSession,
                patientId: this.currentPatientId
            });
            if (error.name === 'TypeError' && error.message.includes('fetch')) return this.generateMockResponse(message);
            throw error;
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
        if (!this.currentSession) this.startNewChat();
        const message = { id: this.generateId(), role, content, timestamp: new Date().toISOString() };
        this.currentSession.messages.push(message);
        this.displayMessage(message);
        if (role === 'user' && this.currentSession.messages.length === 2) this.summariseAndSetTitle(content);
    }

    // Check if session needs title generation after messages are loaded
    checkAndGenerateSessionTitle() {
        if (!this.currentSession || !this.currentSession.messages) return;
        
        // Check if this is a new session that needs a title (exactly 2 messages: user + assistant)
        if (this.currentSession.messages.length === 2 && 
            this.currentSession.title === 'New Chat' && 
            this.currentSession.messages[0].role === 'user') {
            const firstMessage = this.currentSession.messages[0].content;
            this.summariseAndSetTitle(firstMessage);
        }
    }

    summariseAndSetTitle = async function (text) {
        try {
            const resp = await fetch('/summarise', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, max_words: 5 }) });
            if (resp.ok) {
                const data = await resp.json();
                const title = (data.title || 'New Chat').trim();
                this.currentSession.title = title;
                this.updateCurrentSession();
                this.updateChatTitle();
                this.loadChatSessions();
        } else {
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
        const avatar = message.role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        const time = this.formatTime(message.timestamp);
        messageElement.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${this.formatMessageContent(message.content)}</div>
                <div class="message-time">${time}</div>
            </div>`;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        if (this.currentSession) this.currentSession.lastActivity = new Date().toISOString();
    }

    formatMessageContent(content) {
        return content
            // Handle headers (1-6 # symbols)
            .replace(/^#{1,6}\s+(.+)$/gm, (match, text, offset, string) => {
                const level = match.match(/^#+/)[0].length;
                return `<h${level}>${text}</h${level}>`;
            })
            // Handle bold text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Handle italic text
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Handle line breaks
            .replace(/\n/g, '<br>')
            // Handle emojis with colors
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
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) { const minutes = Math.floor(diff / 60000); return `${minutes} minute${minutes > 1 ? 's' : ''} ago`; }
        if (diff < 86400000) { const hours = Math.floor(diff / 3600000); return `${hours} hour${hours > 1 ? 's' : ''} ago`; }
        return date.toLocaleDateString();
    }
}
// ----------------------------------------------------------
// Additional UI setup END
// ----------------------------------------------------------  


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

// Settings modal open/close wiring (from settings.js)
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

// Patient modal open/close wiring (from patient.js)
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
                window.medicalChatbot.currentPatientId = null;
                localStorage.removeItem('medicalChatbotPatientId');
                const status = document.getElementById('patientStatus');
                if (status) { status.textContent = 'No patient selected'; status.style.color = 'var(--text-secondary)'; }
                const input = document.getElementById('patientIdInput');
                if (input) input.value = '';
                modal.classList.remove('show');
            }
        });
    }
    if (createBtn) createBtn.addEventListener('click', () => modal.classList.remove('show'));
});

// Doctor modal open/close wiring (from doctor.js)
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