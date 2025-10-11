// EMR Page JavaScript
// static/js/emr.js

class EMRPage {
    constructor() {
        this.currentPatientId = null;
        this.currentPatient = null;
        this.emrEntries = [];
        this.filteredEntries = [];
        this.currentPage = 1;
        this.entriesPerPage = 20;

        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadPatientFromURL();
        if (this.currentPatientId) {
            await this.loadEMRData();
            await this.loadPatientStats();
        } else {
            this.showEmptyState();
        }
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadEMRData();
        });

        // Search button
        document.getElementById('searchBtn').addEventListener('click', () => {
            this.openSearchModal();
        });

        // Search input
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.filterEntries(e.target.value);
        });

        // Filter selects
        document.getElementById('dateFilter').addEventListener('change', () => {
            this.applyFilters();
        });

        document.getElementById('typeFilter').addEventListener('change', () => {
            this.applyFilters();
        });

        // Modal handlers
        this.setupModalHandlers();
    }

    setupModalHandlers() {
        // EMR Detail Modal
        const emrDetailModal = document.getElementById('emrDetailModal');
        const emrDetailModalClose = document.getElementById('emrDetailModalClose');
        const emrDetailModalCancel = document.getElementById('emrDetailModalCancel');

        if (emrDetailModalClose) {
            emrDetailModalClose.addEventListener('click', () => {
                emrDetailModal.classList.remove('show');
            });
        }

        if (emrDetailModalCancel) {
            emrDetailModalCancel.addEventListener('click', () => {
                emrDetailModal.classList.remove('show');
            });
        }

        // Search Modal
        const searchModal = document.getElementById('searchModal');
        const searchModalClose = document.getElementById('searchModalClose');
        const searchModalCancel = document.getElementById('searchModalCancel');
        const performSearchBtn = document.getElementById('performSearchBtn');

        if (searchModalClose) {
            searchModalClose.addEventListener('click', () => {
                searchModal.classList.remove('show');
            });
        }

        if (searchModalCancel) {
            searchModalCancel.addEventListener('click', () => {
                searchModal.classList.remove('show');
            });
        }

        if (performSearchBtn) {
            performSearchBtn.addEventListener('click', () => {
                this.performAdvancedSearch();
                searchModal.classList.remove('show');
            });
        }
    }

    async loadPatientFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const patientId = urlParams.get('patient_id');

        // Check if patientId is valid (not undefined, null, or empty)
        if (patientId && patientId !== 'undefined' && patientId !== 'null' && patientId.trim() !== '') {
            this.currentPatientId = patientId;
            await this.loadPatientInfo();
        } else {
            // Try to get from localStorage
            const savedPatientId = localStorage.getItem('medicalChatbotPatientId');
            if (savedPatientId && savedPatientId !== 'undefined' && savedPatientId !== 'null' && savedPatientId.trim() !== '') {
                this.currentPatientId = savedPatientId;
                await this.loadPatientInfo();
            } else {
                console.warn('No valid patient ID found in URL or localStorage');
                this.showEmptyState();
            }
        }
    }

    async loadPatientInfo() {
        try {
            const response = await fetch(`/patient/${this.currentPatientId}`);
            if (response.ok) {
                this.currentPatient = await response.json();
                this.updatePatientInfoBar();
            } else {
                console.error('Failed to load patient info');
                this.showEmptyState();
            }
        } catch (error) {
            console.error('Error loading patient info:', error);
            this.showEmptyState();
        }
    }

    updatePatientInfoBar() {
        if (!this.currentPatient) return;

        const patientInfoBar = document.getElementById('patientInfoBar');
        const patientName = document.getElementById('patientName');
        const patientDetails = document.getElementById('patientDetails');

        patientName.textContent = this.currentPatient.name;
        patientDetails.textContent = `Age: ${this.currentPatient.age} | Sex: ${this.currentPatient.sex} | ID: ${this.currentPatient._id}`;

        patientInfoBar.style.display = 'block';
    }

    async loadPatientStats() {
        try {
            const response = await fetch(`/emr/statistics/${this.currentPatientId}`);
            if (response.ok) {
                const stats = await response.json();
                this.updatePatientStats(stats);
            }
        } catch (error) {
            console.error('Error loading patient stats:', error);
        }
    }

    updatePatientStats(stats) {
        const patientStats = document.getElementById('patientStats');

        patientStats.innerHTML = `
            <div class="stat-item">
                <div class="stat-value">${stats.total_entries || 0}</div>
                <div class="stat-label">Total Entries</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${Math.round((stats.avg_confidence || 0) * 100)}%</div>
                <div class="stat-label">Avg Confidence</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.diagnosis_count || 0}</div>
                <div class="stat-label">Diagnoses</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.medication_count || 0}</div>
                <div class="stat-label">Medications</div>
            </div>
        `;
    }

    async loadEMRData() {
        if (!this.currentPatientId) return;

        this.showLoading(true);

        try {
            const response = await fetch(`/emr/patient/${this.currentPatientId}?limit=100`);
            if (response.ok) {
                this.emrEntries = await response.json();
                this.filteredEntries = [...this.emrEntries];
                this.renderEMRTable();
            } else {
                console.error('Failed to load EMR data');
                this.showEmptyState();
            }
        } catch (error) {
            console.error('Error loading EMR data:', error);
            this.showErrorState('Failed to load EMR data. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    renderEMRTable() {
        const tableBody = document.getElementById('emrTableBody');

        if (this.filteredEntries.length === 0) {
            this.showEmptyState();
            return;
        }

        tableBody.innerHTML = this.filteredEntries.map(entry => {
            const date = new Date(entry.created_at).toLocaleString();
            const type = this.getEMRType(entry.extracted_data);
            const diagnosis = entry.extracted_data.diagnosis?.slice(0, 2).join(', ') || '-';
            const medications = entry.extracted_data.medications?.slice(0, 2).map(m => m.name).join(', ') || '-';
            const vitals = this.formatVitalSigns(entry.extracted_data.vital_signs);
            const confidence = this.formatConfidence(entry.confidence_score);

            return `
                <tr>
                    <td>${date}</td>
                    <td><span class="emr-type emr-type-${type}">${type}</span></td>
                    <td>${diagnosis}</td>
                    <td>${medications}</td>
                    <td>${vitals}</td>
                    <td>${confidence}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="action-btn" onclick="emrPage.viewEMRDetail('${entry.emr_id}')" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="action-btn danger" onclick="emrPage.deleteEMREntry('${entry.emr_id}')" title="Delete">
                                <i class="fas fa-trash"></i>
                </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    getEMRType(extractedData) {
        if (extractedData.diagnosis?.length > 0) return 'diagnosis';
        if (extractedData.medications?.length > 0) return 'medication';
        if (extractedData.vital_signs && Object.values(extractedData.vital_signs).some(v => v)) return 'vitals';
        if (extractedData.lab_results?.length > 0) return 'lab';
        return 'general';
    }

    formatVitalSigns(vitalSigns) {
        if (!vitalSigns) return '-';

        const vitals = [];
        if (vitalSigns.blood_pressure) vitals.push(`BP: ${vitalSigns.blood_pressure}`);
        if (vitalSigns.heart_rate) vitals.push(`HR: ${vitalSigns.heart_rate}`);
        if (vitalSigns.temperature) vitals.push(`Temp: ${vitalSigns.temperature}`);

        return vitals.length > 0 ? vitals.join(', ') : '-';
    }

    formatConfidence(score) {
        const percentage = Math.round(score * 100);
        const level = score >= 0.8 ? 'high' : score >= 0.6 ? 'medium' : 'low';

        return `
            <div class="confidence-score">
                <div class="confidence-bar">
                    <div class="confidence-fill ${level}" style="width: ${percentage}%"></div>
                </div>
                <span class="confidence-text">${percentage}%</span>
            </div>
        `;
    }

    async viewEMRDetail(emrId) {
        try {
            const response = await fetch(`/emr/${emrId}`);
            if (response.ok) {
                const entry = await response.json();
                this.showEMRDetailModal(entry);
            } else {
                alert('Failed to load EMR details');
            }
        } catch (error) {
            console.error('Error loading EMR detail:', error);
            alert('Error loading EMR details');
        }
    }

    showEMRDetailModal(entry) {
        const modal = document.getElementById('emrDetailModal');
        const content = document.getElementById('emrDetailContent');

        const date = new Date(entry.created_at).toLocaleString();

        content.innerHTML = `
            <div class="emr-detail-section">
                <h4>Basic Information</h4>
                <p><strong>Date:</strong> ${date}</p>
                <p><strong>Confidence:</strong> ${Math.round(entry.confidence_score * 100)}%</p>
                <p><strong>Original Message:</strong></p>
                <div style="background-color: var(--bg-secondary); padding: var(--spacing-md); border-radius: 8px; margin-top: var(--spacing-sm);">
                    ${entry.original_message}
                </div>
            </div>

            ${entry.extracted_data.diagnosis?.length > 0 ? `
                <div class="emr-detail-section">
                    <h4>Diagnoses</h4>
                    <ul class="emr-detail-list">
                        ${entry.extracted_data.diagnosis.map(d => `<li>${d}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}

            ${entry.extracted_data.symptoms?.length > 0 ? `
                <div class="emr-detail-section">
                    <h4>Symptoms</h4>
                    <ul class="emr-detail-list">
                        ${entry.extracted_data.symptoms.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}

            ${entry.extracted_data.medications?.length > 0 ? `
                <div class="emr-detail-section">
                    <h4>Medications</h4>
                    ${entry.extracted_data.medications.map(med => `
                        <div class="medication-item">
                            <div class="medication-name">${med.name}</div>
                            <div class="medication-details">
                                ${med.dosage ? `Dosage: ${med.dosage}` : ''}
                                ${med.frequency ? ` | Frequency: ${med.frequency}` : ''}
                                ${med.duration ? ` | Duration: ${med.duration}` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}

            ${entry.extracted_data.vital_signs && Object.values(entry.extracted_data.vital_signs).some(v => v) ? `
                <div class="emr-detail-section">
                    <h4>Vital Signs</h4>
                    <div class="vital-signs-grid">
                        ${Object.entries(entry.extracted_data.vital_signs).map(([key, value]) =>
                            value ? `
                                <div class="vital-sign-item">
                                    <div class="vital-sign-label">${key.replace('_', ' ').toUpperCase()}</div>
                                    <div class="vital-sign-value">${value}</div>
                                </div>
                            ` : ''
                        ).join('')}
                    </div>
                </div>
            ` : ''}

            ${entry.extracted_data.lab_results?.length > 0 ? `
                <div class="emr-detail-section">
                    <h4>Lab Results</h4>
                    <ul class="emr-detail-list">
                        ${entry.extracted_data.lab_results.map(lab => `
                            <li>
                                <strong>${lab.test_name}:</strong> ${lab.value} ${lab.unit || ''}
                                ${lab.reference_range ? ` (Normal: ${lab.reference_range})` : ''}
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}

            ${entry.extracted_data.procedures?.length > 0 ? `
                <div class="emr-detail-section">
                    <h4>Procedures</h4>
                    <ul class="emr-detail-list">
                        ${entry.extracted_data.procedures.map(p => `<li>${p}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}

            ${entry.extracted_data.notes ? `
                <div class="emr-detail-section">
                    <h4>Notes</h4>
                    <p>${entry.extracted_data.notes}</p>
                </div>
            ` : ''}
        `;

        modal.classList.add('show');
    }

    async deleteEMREntry(emrId) {
        if (!confirm('Are you sure you want to delete this EMR entry?')) {
            return;
        }

        try {
            const response = await fetch(`/emr/${emrId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadEMRData(); // Refresh the data
                this.loadPatientStats(); // Refresh stats
            } else {
                alert('Failed to delete EMR entry');
            }
        } catch (error) {
            console.error('Error deleting EMR entry:', error);
            alert('Error deleting EMR entry');
        }
    }

    filterEntries(query) {
        if (!query.trim()) {
            this.filteredEntries = [...this.emrEntries];
        } else {
            this.filteredEntries = this.emrEntries.filter(entry => {
                const searchText = query.toLowerCase();
                return (
                    entry.original_message.toLowerCase().includes(searchText) ||
                    entry.extracted_data.diagnosis?.some(d => d.toLowerCase().includes(searchText)) ||
                    entry.extracted_data.symptoms?.some(s => s.toLowerCase().includes(searchText)) ||
                    entry.extracted_data.medications?.some(m => m.name.toLowerCase().includes(searchText)) ||
                    entry.extracted_data.notes?.toLowerCase().includes(searchText)
                );
            });
        }
        this.renderEMRTable();
    }

    applyFilters() {
        const dateFilter = document.getElementById('dateFilter').value;
        const typeFilter = document.getElementById('typeFilter').value;

        this.filteredEntries = this.emrEntries.filter(entry => {
            // Date filter
            if (dateFilter !== 'all') {
                const entryDate = new Date(entry.created_at);
                const now = new Date();

                switch (dateFilter) {
                    case 'today':
                        if (entryDate.toDateString() !== now.toDateString()) return false;
                        break;
                    case 'week':
                        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                        if (entryDate < weekAgo) return false;
                        break;
                    case 'month':
                        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                        if (entryDate < monthAgo) return false;
                        break;
                }
            }

            // Type filter
            if (typeFilter !== 'all') {
                const entryType = this.getEMRType(entry.extracted_data);
                if (entryType !== typeFilter) return false;
            }

            return true;
        });

        this.renderEMRTable();
    }

    openSearchModal() {
        document.getElementById('searchModal').classList.add('show');
    }

    async performAdvancedSearch() {
        const semanticQuery = document.getElementById('semanticSearchInput').value.trim();
        const exactQuery = document.getElementById('exactSearchInput').value.trim();

        if (!semanticQuery && !exactQuery) {
            alert('Please enter a search query');
            return;
        }

        this.showLoading(true);

        try {
            let searchResults = [];

            if (semanticQuery) {
                const response = await fetch(`/emr/search/${this.currentPatientId}?query=${encodeURIComponent(semanticQuery)}&limit=50`);
                if (response.ok) {
                    searchResults = await response.json();
                }
            }

            if (exactQuery) {
                const exactResults = this.emrEntries.filter(entry => {
                    const searchText = exactQuery.toLowerCase();
                    return (
                        entry.original_message.toLowerCase().includes(searchText) ||
                        entry.extracted_data.diagnosis?.some(d => d.toLowerCase().includes(searchText)) ||
                        entry.extracted_data.symptoms?.some(s => s.toLowerCase().includes(searchText)) ||
                        entry.extracted_data.medications?.some(m => m.name.toLowerCase().includes(searchText)) ||
                        entry.extracted_data.notes?.toLowerCase().includes(searchText)
                    );
                });

                // Merge results if both searches were performed
                if (semanticQuery) {
                    const exactIds = new Set(exactResults.map(r => r.emr_id));
                    searchResults = searchResults.concat(exactResults.filter(r => !exactIds.has(r.emr_id)));
            } else {
                    searchResults = exactResults;
                }
            }

            this.filteredEntries = searchResults;
            this.renderEMRTable();

        } catch (error) {
            console.error('Error performing search:', error);
            alert('Error performing search');
        } finally {
            this.showLoading(false);
        }
    }

    showLoading(show) {
        const loadingState = document.getElementById('loadingState');
        const tableContainer = document.querySelector('.emr-table-container');

        if (show) {
            loadingState.style.display = 'block';
            tableContainer.style.display = 'none';
        } else {
            loadingState.style.display = 'none';
            tableContainer.style.display = 'block';
        }
    }

    showEmptyState() {
        const emptyState = document.getElementById('emptyState');
        const tableContainer = document.querySelector('.emr-table-container');

        emptyState.style.display = 'block';
        tableContainer.style.display = 'none';
    }

    showErrorState(message) {
        const emptyState = document.getElementById('emptyState');
        const tableContainer = document.querySelector('.emr-table-container');

        // Update the empty state to show error message
        emptyState.querySelector('h3').textContent = 'Error Loading EMR Data';
        emptyState.querySelector('p').textContent = message;
        emptyState.querySelector('.btn').style.display = 'none';

        emptyState.style.display = 'block';
        tableContainer.style.display = 'none';
    }
}

// Initialize the EMR page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.emrPage = new EMRPage();
});
