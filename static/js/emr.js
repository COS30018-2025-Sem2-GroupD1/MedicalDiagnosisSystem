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

        // Tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Modal handlers
        this.setupModalHandlers();
        
        // File upload handlers
        this.setupFileUploadHandlers();
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

        // Document Preview Modal
        const documentPreviewModal = document.getElementById('documentPreviewModal');
        const documentPreviewModalClose = document.getElementById('documentPreviewModalClose');
        const documentPreviewCancel = document.getElementById('documentPreviewCancel');
        const saveDocumentAnalysis = document.getElementById('saveDocumentAnalysis');

        if (documentPreviewModalClose) {
            documentPreviewModalClose.addEventListener('click', () => {
                documentPreviewModal.classList.remove('show');
            });
        }

        if (documentPreviewCancel) {
            documentPreviewCancel.addEventListener('click', () => {
                documentPreviewModal.classList.remove('show');
            });
        }

        if (saveDocumentAnalysis) {
            saveDocumentAnalysis.addEventListener('click', () => {
                this.saveDocumentAnalysis();
            });
        }
    }

    setupFileUploadHandlers() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const uploadProgress = document.getElementById('uploadProgress');

        // Click to upload
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                fileInput.click();
            });
        }

        if (uploadArea) {
            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });
        }

        // File input change
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileUpload(e.target.files);
                }
            });
        }

        // Drag and drop
        if (uploadArea) {
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                
                if (e.dataTransfer.files.length > 0) {
                    this.handleFileUpload(e.dataTransfer.files);
                }
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

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        // Load specific tab data
        switch (tabName) {
            case 'diagnosis':
                this.renderDiagnosisTab();
                break;
            case 'medications':
                this.renderMedicationsTab();
                break;
            case 'vitals':
                this.renderVitalsTab();
                break;
            case 'lab':
                this.renderLabTab();
                break;
            case 'procedures':
                this.renderProceduresTab();
                break;
        }
    }

    renderDiagnosisTab() {
        const timeline = document.getElementById('diagnosisTimeline');
        const diagnoses = [];

        this.emrEntries.forEach(entry => {
            if (entry.extracted_data.diagnosis && entry.extracted_data.diagnosis.length > 0) {
                entry.extracted_data.diagnosis.forEach(diagnosis => {
                    diagnoses.push({
                        name: diagnosis,
                        date: new Date(entry.created_at).toLocaleDateString(),
                        confidence: Math.round(entry.confidence_score * 100)
                    });
                });
            }
        });

        if (diagnoses.length === 0) {
            timeline.innerHTML = '<p class="no-data">No diagnoses found in EMR entries.</p>';
            return;
        }

        timeline.innerHTML = diagnoses.map(diagnosis => `
            <div class="diagnosis-item">
                <div class="diagnosis-date">${diagnosis.date}</div>
                <div class="diagnosis-name">${diagnosis.name}</div>
                <div class="diagnosis-confidence">${diagnosis.confidence}%</div>
            </div>
        `).join('');
    }

    renderMedicationsTab() {
        const grid = document.getElementById('medicationsGrid');
        const medications = [];

        this.emrEntries.forEach(entry => {
            if (entry.extracted_data.medications && entry.extracted_data.medications.length > 0) {
                entry.extracted_data.medications.forEach(med => {
                    medications.push({
                        name: med.name,
                        dosage: med.dosage || 'Not specified',
                        frequency: med.frequency || 'Not specified',
                        duration: med.duration || 'Not specified',
                        date: new Date(entry.created_at).toLocaleDateString()
                    });
                });
            }
        });

        if (medications.length === 0) {
            grid.innerHTML = '<p class="no-data">No medications found in EMR entries.</p>';
            return;
        }

        grid.innerHTML = medications.map(med => `
            <div class="medication-card">
                <div class="medication-name">${med.name}</div>
                <div class="medication-details">
                    <div class="medication-detail">
                        <strong>Dosage:</strong> <span>${med.dosage}</span>
                    </div>
                    <div class="medication-detail">
                        <strong>Frequency:</strong> <span>${med.frequency}</span>
                    </div>
                    <div class="medication-detail">
                        <strong>Duration:</strong> <span>${med.duration}</span>
                    </div>
                    <div class="medication-detail">
                        <strong>Date:</strong> <span>${med.date}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderVitalsTab() {
        const tableBody = document.getElementById('vitalsTableBody');
        const vitalsData = [];

        this.emrEntries.forEach(entry => {
            if (entry.extracted_data.vital_signs) {
                const vitals = entry.extracted_data.vital_signs;
                if (Object.values(vitals).some(v => v)) {
                    vitalsData.push({
                        date: new Date(entry.created_at).toLocaleDateString(),
                        blood_pressure: vitals.blood_pressure || '-',
                        heart_rate: vitals.heart_rate || '-',
                        temperature: vitals.temperature || '-',
                        respiratory_rate: vitals.respiratory_rate || '-',
                        oxygen_saturation: vitals.oxygen_saturation || '-'
                    });
                }
            }
        });

        if (vitalsData.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="no-data">No vital signs found in EMR entries.</td></tr>';
            return;
        }

        tableBody.innerHTML = vitalsData.map(vitals => `
            <tr>
                <td>${vitals.date}</td>
                <td>${vitals.blood_pressure}</td>
                <td>${vitals.heart_rate}</td>
                <td>${vitals.temperature}</td>
                <td>${vitals.respiratory_rate}</td>
                <td>${vitals.oxygen_saturation}</td>
            </tr>
        `).join('');
    }

    renderLabTab() {
        const container = document.getElementById('labResultsContainer');
        const labResults = [];

        this.emrEntries.forEach(entry => {
            if (entry.extracted_data.lab_results && entry.extracted_data.lab_results.length > 0) {
                entry.extracted_data.lab_results.forEach(lab => {
                    labResults.push({
                        test_name: lab.test_name,
                        value: lab.value,
                        unit: lab.unit || '',
                        reference_range: lab.reference_range || 'Not specified',
                        date: new Date(entry.created_at).toLocaleDateString()
                    });
                });
            }
        });

        if (labResults.length === 0) {
            container.innerHTML = '<p class="no-data">No lab results found in EMR entries.</p>';
            return;
        }

        container.innerHTML = labResults.map(lab => `
            <div class="lab-result-item">
                <div class="lab-result-header">
                    <div class="lab-test-name">${lab.test_name}</div>
                    <div class="lab-test-value">${lab.value} ${lab.unit}</div>
                </div>
                <div class="lab-test-details">
                    <span><strong>Date:</strong> ${lab.date}</span>
                    <span><strong>Reference Range:</strong> ${lab.reference_range}</span>
                </div>
            </div>
        `).join('');
    }

    renderProceduresTab() {
        const timeline = document.getElementById('proceduresTimeline');
        const procedures = [];

        this.emrEntries.forEach(entry => {
            if (entry.extracted_data.procedures && entry.extracted_data.procedures.length > 0) {
                entry.extracted_data.procedures.forEach(procedure => {
                    procedures.push({
                        name: procedure,
                        date: new Date(entry.created_at).toLocaleDateString(),
                        confidence: Math.round(entry.confidence_score * 100)
                    });
                });
            }
        });

        if (procedures.length === 0) {
            timeline.innerHTML = '<p class="no-data">No procedures found in EMR entries.</p>';
            return;
        }

        timeline.innerHTML = procedures.map(procedure => `
            <div class="procedure-item">
                <div class="procedure-date">${procedure.date}</div>
                <div class="procedure-name">${procedure.name}</div>
                <div class="procedure-status">${procedure.confidence}%</div>
            </div>
        `).join('');
    }

    async handleFileUpload(files) {
        if (!this.currentPatientId) {
            alert('Please select a patient first');
            return;
        }

        const file = files[0]; // Handle only the first file for now
        
        // Validate file type
        const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/jpg', 'image/png', 'image/tiff'];
        if (!allowedTypes.includes(file.type)) {
            alert('Unsupported file type. Please upload PDF, DOC, DOCX, JPG, PNG, or TIFF files.');
            return;
        }

        // Validate file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            alert('File size exceeds 10MB limit.');
            return;
        }

        this.showUploadProgress(true);
        
        try {
            // Create FormData
            const formData = new FormData();
            formData.append('patient_id', this.currentPatientId);
            formData.append('file', file);

            // Upload and analyze document
            const response = await fetch('/emr/preview-document', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to analyze document');
            }

            const result = await response.json();
            this.showDocumentPreview(result);

        } catch (error) {
            console.error('Error uploading file:', error);
            alert(`Error analyzing document: ${error.message}`);
        } finally {
            this.showUploadProgress(false);
        }
    }

    showUploadProgress(show) {
        const uploadProgress = document.getElementById('uploadProgress');
        const uploadArea = document.getElementById('uploadArea');
        
        if (show) {
            uploadProgress.style.display = 'block';
            uploadArea.style.display = 'none';
        } else {
            uploadProgress.style.display = 'none';
            uploadArea.style.display = 'block';
        }
    }

    showDocumentPreview(analysisResult) {
        const modal = document.getElementById('documentPreviewModal');
        const content = document.getElementById('documentPreviewContent');
        
        // Store the analysis result for saving
        this.currentDocumentAnalysis = analysisResult;

        content.innerHTML = this.renderDocumentPreview(analysisResult);
        modal.classList.add('show');
    }

    renderDocumentPreview(data) {
        const { filename, confidence_score, extracted_data } = data;
        
        return `
            <div class="document-preview-section">
                <h4><i class="fas fa-file"></i> Document Information</h4>
                <p><strong>Filename:</strong> ${filename}</p>
                <p><strong>Confidence Score:</strong> ${Math.round(confidence_score * 100)}%</p>
            </div>

            ${extracted_data.overview ? `
                <div class="document-preview-section">
                    <h4><i class="fas fa-eye"></i> Overview</h4>
                    <textarea class="editable-field" id="overviewField" rows="3">${extracted_data.overview}</textarea>
                </div>
            ` : ''}

            <div class="document-preview-section">
                <h4><i class="fas fa-stethoscope"></i> Diagnoses</h4>
                <ul class="editable-list" id="diagnosisList">
                    ${(extracted_data.diagnosis || []).map(diagnosis => `
                        <li>
                            <input type="text" value="${diagnosis}" class="diagnosis-input">
                            <button type="button" onclick="emrPage.removeListItem(this)"><i class="fas fa-trash"></i></button>
                        </li>
                    `).join('')}
                </ul>
                <button type="button" class="add-item-btn" onclick="emrPage.addDiagnosis()">
                    <i class="fas fa-plus"></i> Add Diagnosis
                </button>
            </div>

            <div class="document-preview-section">
                <h4><i class="fas fa-exclamation-triangle"></i> Symptoms</h4>
                <ul class="editable-list" id="symptomsList">
                    ${(extracted_data.symptoms || []).map(symptom => `
                        <li>
                            <input type="text" value="${symptom}" class="symptom-input">
                            <button type="button" onclick="emrPage.removeListItem(this)"><i class="fas fa-trash"></i></button>
                        </li>
                    `).join('')}
                </ul>
                <button type="button" class="add-item-btn" onclick="emrPage.addSymptom()">
                    <i class="fas fa-plus"></i> Add Symptom
                </button>
            </div>

            <div class="document-preview-section">
                <h4><i class="fas fa-pills"></i> Medications</h4>
                <div id="medicationsList">
                    ${(extracted_data.medications || []).map((med, index) => `
                        <div class="medication-preview-item">
                            <h5>Medication ${index + 1}</h5>
                            <div class="medication-detail-row">
                                <div>
                                    <label>Name</label>
                                    <input type="text" value="${med.name || ''}" class="med-name-input">
                                </div>
                                <div>
                                    <label>Dosage</label>
                                    <input type="text" value="${med.dosage || ''}" class="med-dosage-input">
                                </div>
                            </div>
                            <div class="medication-detail-row">
                                <div>
                                    <label>Frequency</label>
                                    <input type="text" value="${med.frequency || ''}" class="med-frequency-input">
                                </div>
                                <div>
                                    <label>Duration</label>
                                    <input type="text" value="${med.duration || ''}" class="med-duration-input">
                                </div>
                            </div>
                            <button type="button" onclick="emrPage.removeMedication(this)" style="margin-top: 10px; background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                                <i class="fas fa-trash"></i> Remove
                            </button>
                        </div>
                    `).join('')}
                </div>
                <button type="button" class="add-item-btn" onclick="emrPage.addMedication()">
                    <i class="fas fa-plus"></i> Add Medication
                </button>
            </div>

            ${extracted_data.vital_signs ? `
                <div class="document-preview-section">
                    <h4><i class="fas fa-heartbeat"></i> Vital Signs</h4>
                    <div class="vital-signs-preview-grid">
                        <div class="vital-sign-preview-item">
                            <label>Blood Pressure</label>
                            <input type="text" value="${extracted_data.vital_signs.blood_pressure || ''}" id="bpInput">
                        </div>
                        <div class="vital-sign-preview-item">
                            <label>Heart Rate</label>
                            <input type="text" value="${extracted_data.vital_signs.heart_rate || ''}" id="hrInput">
                        </div>
                        <div class="vital-sign-preview-item">
                            <label>Temperature</label>
                            <input type="text" value="${extracted_data.vital_signs.temperature || ''}" id="tempInput">
                        </div>
                        <div class="vital-sign-preview-item">
                            <label>Respiratory Rate</label>
                            <input type="text" value="${extracted_data.vital_signs.respiratory_rate || ''}" id="rrInput">
                        </div>
                        <div class="vital-sign-preview-item">
                            <label>Oxygen Saturation</label>
                            <input type="text" value="${extracted_data.vital_signs.oxygen_saturation || ''}" id="o2Input">
                        </div>
                    </div>
                </div>
            ` : ''}

            <div class="document-preview-section">
                <h4><i class="fas fa-flask"></i> Lab Results</h4>
                <div id="labResultsList">
                    ${(extracted_data.lab_results || []).map((lab, index) => `
                        <div class="lab-result-preview-item">
                            <h5>Lab Test ${index + 1}</h5>
                            <div class="lab-result-detail-row">
                                <div>
                                    <label>Test Name</label>
                                    <input type="text" value="${lab.test_name || ''}" class="lab-name-input">
                                </div>
                                <div>
                                    <label>Value</label>
                                    <input type="text" value="${lab.value || ''}" class="lab-value-input">
                                </div>
                                <div>
                                    <label>Unit</label>
                                    <input type="text" value="${lab.unit || ''}" class="lab-unit-input">
                                </div>
                            </div>
                            <div class="lab-result-detail-row">
                                <div>
                                    <label>Reference Range</label>
                                    <input type="text" value="${lab.reference_range || ''}" class="lab-range-input">
                                </div>
                            </div>
                            <button type="button" onclick="emrPage.removeLabResult(this)" style="margin-top: 10px; background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                                <i class="fas fa-trash"></i> Remove
                            </button>
                        </div>
                    `).join('')}
                </div>
                <button type="button" class="add-item-btn" onclick="emrPage.addLabResult()">
                    <i class="fas fa-plus"></i> Add Lab Result
                </button>
            </div>

            <div class="document-preview-section">
                <h4><i class="fas fa-procedures"></i> Procedures</h4>
                <ul class="editable-list" id="proceduresList">
                    ${(extracted_data.procedures || []).map(procedure => `
                        <li>
                            <input type="text" value="${procedure}" class="procedure-input">
                            <button type="button" onclick="emrPage.removeListItem(this)"><i class="fas fa-trash"></i></button>
                        </li>
                    `).join('')}
                </ul>
                <button type="button" class="add-item-btn" onclick="emrPage.addProcedure()">
                    <i class="fas fa-plus"></i> Add Procedure
                </button>
            </div>

            <div class="document-preview-section">
                <h4><i class="fas fa-sticky-note"></i> Notes</h4>
                <textarea class="editable-field" id="notesField" rows="4">${extracted_data.notes || ''}</textarea>
            </div>
        `;
    }

    addDiagnosis() {
        const list = document.getElementById('diagnosisList');
        const li = document.createElement('li');
        li.innerHTML = `
            <input type="text" value="" class="diagnosis-input" placeholder="Enter diagnosis">
            <button type="button" onclick="emrPage.removeListItem(this)"><i class="fas fa-trash"></i></button>
        `;
        list.appendChild(li);
    }

    addSymptom() {
        const list = document.getElementById('symptomsList');
        const li = document.createElement('li');
        li.innerHTML = `
            <input type="text" value="" class="symptom-input" placeholder="Enter symptom">
            <button type="button" onclick="emrPage.removeListItem(this)"><i class="fas fa-trash"></i></button>
        `;
        list.appendChild(li);
    }

    addMedication() {
        const list = document.getElementById('medicationsList');
        const index = list.children.length;
        const div = document.createElement('div');
        div.className = 'medication-preview-item';
        div.innerHTML = `
            <h5>Medication ${index + 1}</h5>
            <div class="medication-detail-row">
                <div>
                    <label>Name</label>
                    <input type="text" value="" class="med-name-input" placeholder="Medication name">
                </div>
                <div>
                    <label>Dosage</label>
                    <input type="text" value="" class="med-dosage-input" placeholder="Dosage">
                </div>
            </div>
            <div class="medication-detail-row">
                <div>
                    <label>Frequency</label>
                    <input type="text" value="" class="med-frequency-input" placeholder="Frequency">
                </div>
                <div>
                    <label>Duration</label>
                    <input type="text" value="" class="med-duration-input" placeholder="Duration">
                </div>
            </div>
            <button type="button" onclick="emrPage.removeMedication(this)" style="margin-top: 10px; background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                <i class="fas fa-trash"></i> Remove
            </button>
        `;
        list.appendChild(div);
    }

    addLabResult() {
        const list = document.getElementById('labResultsList');
        const index = list.children.length;
        const div = document.createElement('div');
        div.className = 'lab-result-preview-item';
        div.innerHTML = `
            <h5>Lab Test ${index + 1}</h5>
            <div class="lab-result-detail-row">
                <div>
                    <label>Test Name</label>
                    <input type="text" value="" class="lab-name-input" placeholder="Test name">
                </div>
                <div>
                    <label>Value</label>
                    <input type="text" value="" class="lab-value-input" placeholder="Test value">
                </div>
                <div>
                    <label>Unit</label>
                    <input type="text" value="" class="lab-unit-input" placeholder="Unit">
                </div>
            </div>
            <div class="lab-result-detail-row">
                <div>
                    <label>Reference Range</label>
                    <input type="text" value="" class="lab-range-input" placeholder="Normal range">
                </div>
            </div>
            <button type="button" onclick="emrPage.removeLabResult(this)" style="margin-top: 10px; background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                <i class="fas fa-trash"></i> Remove
            </button>
        `;
        list.appendChild(div);
    }

    addProcedure() {
        const list = document.getElementById('proceduresList');
        const li = document.createElement('li');
        li.innerHTML = `
            <input type="text" value="" class="procedure-input" placeholder="Enter procedure">
            <button type="button" onclick="emrPage.removeListItem(this)"><i class="fas fa-trash"></i></button>
        `;
        list.appendChild(li);
    }

    removeListItem(button) {
        button.parentElement.remove();
    }

    removeMedication(button) {
        button.parentElement.remove();
    }

    removeLabResult(button) {
        button.parentElement.remove();
    }

    async saveDocumentAnalysis() {
        if (!this.currentDocumentAnalysis) {
            alert('No document analysis to save');
            return;
        }

        try {
            // Collect all the edited data
            const extractedData = this.collectEditedData();
            
            const formData = new FormData();
            formData.append('patient_id', this.currentPatientId);
            formData.append('filename', this.currentDocumentAnalysis.filename);
            formData.append('extracted_data', JSON.stringify(extractedData));
            formData.append('confidence_score', this.currentDocumentAnalysis.confidence_score);

            const response = await fetch('/emr/save-document-analysis', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save document analysis');
            }

            const result = await response.json();
            
            // Close modal and refresh EMR data
            document.getElementById('documentPreviewModal').classList.remove('show');
            this.loadEMRData();
            this.loadPatientStats();
            
            alert('Document analysis saved successfully!');

        } catch (error) {
            console.error('Error saving document analysis:', error);
            alert(`Error saving document analysis: ${error.message}`);
        }
    }

    collectEditedData() {
        const data = {
            overview: document.getElementById('overviewField')?.value || '',
            diagnosis: Array.from(document.querySelectorAll('.diagnosis-input')).map(input => input.value).filter(val => val.trim()),
            symptoms: Array.from(document.querySelectorAll('.symptom-input')).map(input => input.value).filter(val => val.trim()),
            medications: Array.from(document.querySelectorAll('.medication-preview-item')).map(item => ({
                name: item.querySelector('.med-name-input')?.value || '',
                dosage: item.querySelector('.med-dosage-input')?.value || '',
                frequency: item.querySelector('.med-frequency-input')?.value || '',
                duration: item.querySelector('.med-duration-input')?.value || ''
            })).filter(med => med.name.trim()),
            vital_signs: {
                blood_pressure: document.getElementById('bpInput')?.value || null,
                heart_rate: document.getElementById('hrInput')?.value || null,
                temperature: document.getElementById('tempInput')?.value || null,
                respiratory_rate: document.getElementById('rrInput')?.value || null,
                oxygen_saturation: document.getElementById('o2Input')?.value || null
            },
            lab_results: Array.from(document.querySelectorAll('.lab-result-preview-item')).map(item => ({
                test_name: item.querySelector('.lab-name-input')?.value || '',
                value: item.querySelector('.lab-value-input')?.value || '',
                unit: item.querySelector('.lab-unit-input')?.value || '',
                reference_range: item.querySelector('.lab-range-input')?.value || ''
            })).filter(lab => lab.test_name.trim()),
            procedures: Array.from(document.querySelectorAll('.procedure-input')).map(input => input.value).filter(val => val.trim()),
            notes: document.getElementById('notesField')?.value || ''
        };

        // Clean up empty vital signs
        if (Object.values(data.vital_signs).every(val => !val)) {
            data.vital_signs = null;
        }

        return data;
    }
}

// Initialize the EMR page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.emrPage = new EMRPage();
});
