// ui/patient.js
// Patient selection, typeahead search, load/hydrate, patient modal wiring

export function attachPatientUI(app) {
	// State helpers
	app.loadSavedPatientId = function () {
		const pid = localStorage.getItem('medicalChatbotPatientId');
		if (pid && /^\d{8}$/.test(pid)) {
			app.currentPatientId = pid;
			const status = document.getElementById('patientStatus');
			if (status) {
				status.textContent = `Patient: ${pid}`;
				status.style.color = 'var(--text-secondary)';
			}
			const input = document.getElementById('patientIdInput');
			if (input) input.value = pid;
		}
	};

	app.savePatientId = function () {
		if (app.currentPatientId) localStorage.setItem('medicalChatbotPatientId', app.currentPatientId);
		else localStorage.removeItem('medicalChatbotPatientId');
	};

	app.loadPatient = async function () {
		console.log('[DEBUG] loadPatient called');
		const input = document.getElementById('patientIdInput');
		const status = document.getElementById('patientStatus');
		const id = (input?.value || '').trim();
		console.log('[DEBUG] Patient ID from input:', id);
		if (!/^\d{8}$/.test(id)) {
			console.log('[DEBUG] Invalid patient ID format');
			if (status) { status.textContent = 'Invalid patient ID. Use 8 digits.'; status.style.color = 'var(--warning-color)'; }
			return;
		}
		console.log('[DEBUG] Setting current patient ID:', id);
		app.currentPatientId = id;
		app.savePatientId();
		if (status) { status.textContent = `Patient: ${id}`; status.style.color = 'var(--text-secondary)'; }
		await app.fetchAndRenderPatientSessions();
	};

	app.fetchAndRenderPatientSessions = async function () {
		if (!app.currentPatientId) return;
		try {
			const resp = await fetch(`/patients/${app.currentPatientId}/sessions`);
			if (resp.ok) {
				const data = await resp.json();
				const sessions = Array.isArray(data.sessions) ? data.sessions : [];
				app.backendSessions = sessions.map(s => ({
					id: s.session_id,
					title: s.title || 'New Chat',
					messages: [],
					createdAt: s.created_at || new Date().toISOString(),
					lastActivity: s.last_activity || new Date().toISOString(),
					source: 'backend'
				}));
				if (app.backendSessions.length > 0) {
					app.currentSession = app.backendSessions[0];
					await app.hydrateMessagesForSession(app.currentSession.id);
				}
			} else {
				console.warn('Failed to fetch patient sessions', resp.status);
				app.backendSessions = [];
			}
		} catch (e) {
			console.error('Failed to load patient sessions', e);
			app.backendSessions = [];
		}
		app.loadChatSessions();
	};

	app.hydrateMessagesForSession = async function (sessionId) {
		try {
			const resp = await fetch(`/sessions/${sessionId}/messages?limit=1000`);
			if (!resp.ok) return;
			const data = await resp.json();
			const msgs = Array.isArray(data.messages) ? data.messages : [];
			const normalized = msgs.map(m => ({
				id: m._id || app.generateId(),
				role: m.role,
				content: m.content,
				timestamp: m.timestamp
			}));
			if (app.currentSession && app.currentSession.id === sessionId) {
				app.currentSession.messages = normalized;
				app.clearChatMessages();
				app.currentSession.messages.forEach(m => app.displayMessage(m));
				app.updateChatTitle();
			}
		} catch (e) {
			console.error('Failed to hydrate session messages', e);
		}
	};

	// Bind patient input + typeahead + load button
	app.bindPatientHandlers = function () {
		console.log('[DEBUG] bindPatientHandlers called');
		const loadBtn = document.getElementById('loadPatientBtn');
		console.log('[DEBUG] Load button found:', !!loadBtn);
		if (loadBtn) loadBtn.addEventListener('click', () => app.loadPatient());
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
					app.currentPatientId = p.patient_id;
					app.savePatientId();
					patientInput.value = p.patient_id;
					hideSuggestions();
					const status = document.getElementById('patientStatus');
					if (status) { status.textContent = `Patient: ${p.patient_id}`; status.style.color = 'var(--text-secondary)'; }
					await app.fetchAndRenderPatientSessions();
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
					const resp = await fetch(`/patients/search?q=${encodeURIComponent(q)}&limit=8`, { headers: { 'Accept': 'application/json' } });
					console.log('[DEBUG] Search response status:', resp.status);
					if (resp.ok) {
						const data = await resp.json();
						console.log('[DEBUG] Search results:', data);
						renderSuggestions(data.results || []);
					} else {
						console.warn('Search request failed', resp.status);
					}
				} catch (e) { 
					console.error('[DEBUG] Search error:', e);
				}
			}, 200);
		});
		patientInput.addEventListener('keydown', async (e) => {
			if (e.key === 'Enter') {
				const value = patientInput.value.trim();
				console.log('[DEBUG] Patient input Enter pressed with value:', value);
				if (/^\d{8}$/.test(value)) {
					console.log('[DEBUG] Loading patient with 8-digit ID');
					await app.loadPatient();
					hideSuggestions();
				} else {
					console.log('[DEBUG] Searching for patient by name/partial ID');
					try {
						const resp = await fetch(`/patients/search?q=${encodeURIComponent(value)}&limit=1`);
						console.log('[DEBUG] Search response status:', resp.status);
						if (resp.ok) {
							const data = await resp.json();
							console.log('[DEBUG] Search results for Enter:', data);
							const first = (data.results || [])[0];
							if (first) {
								console.log('[DEBUG] Found patient, setting as current:', first);
								app.currentPatientId = first.patient_id;
								app.savePatientId();
								patientInput.value = first.patient_id;
								hideSuggestions();
								const status = document.getElementById('patientStatus');
								if (status) { status.textContent = `Patient: ${first.patient_id}`; status.style.color = 'var(--text-secondary)'; }
								await app.fetchAndRenderPatientSessions();
								return;
							}
						}
					} catch (e) {
						console.error('[DEBUG] Search error on Enter:', e);
					}
					const status = document.getElementById('patientStatus');
					if (status) { status.textContent = 'No matching patient found'; status.style.color = 'var(--warning-color)'; }
				}
			}
		});
		document.addEventListener('click', (ev) => {
			if (!suggestionsEl) return;
			if (!suggestionsEl.contains(ev.target) && ev.target !== patientInput) hideSuggestions();
		});
	};

	// Patient modal wiring
	document.addEventListener('DOMContentLoaded', () => {
		const profileBtn = document.getElementById('patientMenuBtn');
		const modal = document.getElementById('patientModal');
		const closeBtn = document.getElementById('patientModalClose');
		const logoutBtn = document.getElementById('patientLogoutBtn');
		const createBtn = document.getElementById('patientCreateBtn');
		if (profileBtn && modal) {
			profileBtn.addEventListener('click', async () => {
				const pid = app?.currentPatientId;
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
					app.currentPatientId = null;
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
}


