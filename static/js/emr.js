// EMR Page JavaScript
class PatientEMR {
    constructor() {
        this.patientId = null;
        this.patientData = null;
        this.medications = [];
        this.sessions = [];
        
        this.init();
    }

    async init() {
        // Get patient ID from URL or localStorage
        this.patientId = this.getPatientIdFromURL() || localStorage.getItem('medicalChatbotPatientId');
        
        if (!this.patientId) {
            this.showError('No patient selected. Please go back to the main page and select a patient.');
            return;
        }

        this.setupEventListeners();
        await this.loadPatientData();
    }

    getPatientIdFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('patient_id');
    }

    setupEventListeners() {
        // Save button
        document.getElementById('savePatientBtn').addEventListener('click', () => {
            this.savePatientData();
        });

        // Refresh button
        document.getElementById('refreshPatientBtn').addEventListener('click', () => {
            this.loadPatientData();
        });

        // Export button
        document.getElementById('exportPatientBtn').addEventListener('click', () => {
            this.exportPatientData();
        });

        // Add medication button
        document.getElementById('addMedicationBtn').addEventListener('click', () => {
            this.addMedication();
        });

        // Add medication on Enter key
        document.getElementById('newMedicationInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.addMedication();
            }
        });
    }

    async loadPatientData() {
        this.showLoading(true);
        
        try {
            // Load patient data
            const patientResp = await fetch(`/patients/${this.patientId}`);
            if (!patientResp.ok) {
                throw new Error('Failed to load patient data');
            }
            
            this.patientData = await patientResp.json();
            this.populatePatientForm();
            
            // Load patient sessions
            await this.loadPatientSessions();
            
        } catch (error) {
            console.error('Error loading patient data:', error);
            this.showError('Failed to load patient data. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    populatePatientForm() {
        if (!this.patientData) return;

        // Update header
        document.getElementById('patientName').textContent = this.patientData.name || 'Unknown';
        document.getElementById('patientId').textContent = `ID: ${this.patientData.patient_id}`;

        // Populate form fields
        document.getElementById('patientNameInput').value = this.patientData.name || '';
        document.getElementById('patientAgeInput').value = this.patientData.age || '';
        document.getElementById('patientSexInput').value = this.patientData.sex || '';
        document.getElementById('patientPhoneInput').value = this.patientData.phone || '';
        document.getElementById('patientEmailInput').value = this.patientData.email || '';
        document.getElementById('patientAddressInput').value = this.patientData.address || '';
        document.getElementById('pastAssessmentInput').value = this.patientData.past_assessment_summary || '';

        // Populate medications
        this.medications = this.patientData.medications || [];
        this.renderMedications();
    }

    renderMedications() {
        const container = document.getElementById('medicationsList');
        container.innerHTML = '';

        if (this.medications.length === 0) {
            container.innerHTML = '<div style="color: var(--text-secondary); font-style: italic;">No medications listed</div>';
            return;
        }

        this.medications.forEach((medication, index) => {
            const tag = document.createElement('div');
            tag.className = 'medication-tag';
            tag.innerHTML = `
                ${medication}
                <button class="remove-medication" data-index="${index}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            container.appendChild(tag);
        });

        // Add event listeners for remove buttons
        container.querySelectorAll('.remove-medication').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.closest('.remove-medication').dataset.index);
                this.removeMedication(index);
            });
        });
    }

    addMedication() {
        const input = document.getElementById('newMedicationInput');
        const medication = input.value.trim();
        
        if (!medication) return;
        
        this.medications.push(medication);
        this.renderMedications();
        input.value = '';
    }

    removeMedication(index) {
        this.medications.splice(index, 1);
        this.renderMedications();
    }

    async loadPatientSessions() {
        try {
            const resp = await fetch(`/patients/${this.patientId}/sessions`);
            if (resp.ok) {
                const data = await resp.json();
                this.sessions = data.sessions || [];
                this.renderSessions();
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    renderSessions() {
        const container = document.getElementById('sessionsContainer');
        
        if (this.sessions.length === 0) {
            container.innerHTML = '<div style="color: var(--text-secondary); font-style: italic;">No chat sessions found</div>';
            return;
        }

        container.innerHTML = '';
        
        this.sessions.forEach(session => {
            const sessionEl = document.createElement('div');
            sessionEl.className = 'session-item';
            sessionEl.innerHTML = `
                <div class="session-title">${session.title || 'Untitled Session'}</div>
                <div class="session-meta">
                    <span class="session-date">${this.formatDate(session.created_at)}</span>
                    <span class="session-messages">${session.message_count || 0} messages</span>
                </div>
            `;
            
            sessionEl.addEventListener('click', () => {
                // Could open session details or redirect to main page with session
                window.location.href = `/?session_id=${session.session_id}`;
            });
            
            container.appendChild(sessionEl);
        });
    }

    async savePatientData() {
        this.showLoading(true);
        
        try {
            const updateData = {
                name: document.getElementById('patientNameInput').value.trim(),
                age: parseInt(document.getElementById('patientAgeInput').value) || null,
                sex: document.getElementById('patientSexInput').value || null,
                phone: document.getElementById('patientPhoneInput').value.trim() || null,
                email: document.getElementById('patientEmailInput').value.trim() || null,
                address: document.getElementById('patientAddressInput').value.trim() || null,
                medications: this.medications,
                past_assessment_summary: document.getElementById('pastAssessmentInput').value.trim() || null
            };

            const resp = await fetch(`/patients/${this.patientId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });

            if (resp.ok) {
                this.showSuccess('Patient data saved successfully!');
                // Update the header with new name
                document.getElementById('patientName').textContent = updateData.name || 'Unknown';
            } else {
                throw new Error('Failed to save patient data');
            }
        } catch (error) {
            console.error('Error saving patient data:', error);
            this.showError('Failed to save patient data. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    exportPatientData() {
        if (!this.patientData) {
            this.showError('No patient data to export');
            return;
        }

        const exportData = {
            patient_id: this.patientData.patient_id,
            name: this.patientData.name,
            age: this.patientData.age,
            sex: this.patientData.sex,
            phone: this.patientData.phone,
            email: this.patientData.email,
            address: this.patientData.address,
            medications: this.medications,
            past_assessment_summary: this.patientData.past_assessment_summary,
            created_at: this.patientData.created_at,
            updated_at: new Date().toISOString(),
            sessions: this.sessions
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `patient-${this.patientData.patient_id}-emr.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown date';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }

    showError(message) {
        alert('Error: ' + message);
    }

    showSuccess(message) {
        alert('Success: ' + message);
    }
}

// Initialize EMR when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PatientEMR();
});
