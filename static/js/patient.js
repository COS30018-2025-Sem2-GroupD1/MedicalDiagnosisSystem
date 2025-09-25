document.addEventListener('DOMContentLoaded', () => {
	const form = document.getElementById('patientForm');
	const result = document.getElementById('result');
	const cancelBtn = document.getElementById('cancelBtn');
	const successModal = document.getElementById('patientSuccessModal');
	const successClose = document.getElementById('patientSuccessClose');
	const successReturn = document.getElementById('patientSuccessReturn');
	const successEdit = document.getElementById('patientSuccessEdit');
	const createdIdEl = document.getElementById('createdPatientId');
	const submitBtn = form?.querySelector('button[type="submit"]');
	const titleEl = document.querySelector('h1');

	let isEditMode = false;
	let currentPatientId = null;

	function getPatientIdFromUrl() {
		const urlParams = new URLSearchParams(window.location.search);
		const pidFromUrl = urlParams.get('patient_id');
		if (pidFromUrl && /^\d{8}$/.test(pidFromUrl)) return pidFromUrl;
		return null;
	}

	async function loadPatientIntoForm(patientId) {
		try {
			const resp = await fetch(`/patients/${patientId}`);
			if (!resp.ok) return;
			const data = await resp.json();
			document.getElementById('name').value = data.name || '';
			document.getElementById('age').value = data.age ?? '';
			document.getElementById('sex').value = data.sex || 'Other';
			document.getElementById('address').value = data.address || '';
			document.getElementById('phone').value = data.phone || '';
			document.getElementById('email').value = data.email || '';
			document.getElementById('medications').value = Array.isArray(data.medications) ? data.medications.join('\n') : '';
			document.getElementById('summary').value = data.past_assessment_summary || '';
		} catch (e) {
			console.warn('Failed to load patient profile for editing', e);
		}
	}

	function enableEditMode(patientId) {
		isEditMode = true;
		currentPatientId = patientId;
		if (submitBtn) submitBtn.textContent = 'Update';
		if (titleEl) titleEl.textContent = 'Edit Patient';
	}

	// Initialize: only enter edit mode if patient_id is explicitly in URL
	const pidFromUrl = getPatientIdFromUrl();
	if (pidFromUrl) {
		enableEditMode(pidFromUrl);
		loadPatientIntoForm(pidFromUrl);
	}

	cancelBtn.addEventListener('click', () => {
		window.location.href = '/';
	});

	form.addEventListener('submit', async (e) => {
		e.preventDefault();
		result.textContent = '';
		result.style.color = '';
		const payload = {
			name: document.getElementById('name').value.trim(),
			age: parseInt(document.getElementById('age').value, 10),
			sex: document.getElementById('sex').value,
			address: document.getElementById('address').value.trim() || null,
			phone: document.getElementById('phone').value.trim() || null,
			email: document.getElementById('email').value.trim() || null,
			medications: document.getElementById('medications').value.split('\n').map(s => s.trim()).filter(Boolean),
			past_assessment_summary: document.getElementById('summary').value.trim() || null
		};
		try {
			if (isEditMode && currentPatientId) {
				const resp = await fetch(`/patients/${currentPatientId}`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(payload)
				});
				if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
				result.textContent = 'Patient updated successfully.';
				result.style.color = 'green';
			} else {
				const resp = await fetch('/patients', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(payload)
				});
				if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
				const data = await resp.json();
				const pid = data.patient_id;
				localStorage.setItem('medicalChatbotPatientId', pid);

				// Add to localStorage for future suggestions
				const existingPatients = JSON.parse(localStorage.getItem('medicalChatbotPatients') || '[]');
				const newPatient = {
					patient_id: pid,
					name: payload.name,
					age: payload.age,
					sex: payload.sex
				};
				// Check if patient already exists to avoid duplicates
				const exists = existingPatients.some(p => p.patient_id === pid);
				if (!exists) {
					existingPatients.push(newPatient);
					localStorage.setItem('medicalChatbotPatients', JSON.stringify(existingPatients));
				}

				// Show success modal (stay in create view until user opts to edit)
				if (createdIdEl) createdIdEl.textContent = pid;
				successModal.classList.add('show');
			}
		} catch (err) {
			console.error(err);
			result.textContent = isEditMode ? 'Failed to update patient. Please try again.' : 'Failed to create patient. Please try again.';
			result.style.color = 'crimson';
		}
	});

	// Success modal wiring
	if (successClose) successClose.addEventListener('click', () => successModal.classList.remove('show'));
	if (successReturn) successReturn.addEventListener('click', () => { window.location.href = '/'; });
	if (successEdit) successEdit.addEventListener('click', () => {
		successModal.classList.remove('show');
		const pid = createdIdEl?.textContent?.trim() || localStorage.getItem('medicalChatbotPatientId');
		if (pid && /^\d{8}$/.test(pid)) {
			enableEditMode(pid);
			loadPatientIntoForm(pid);
		}
	});
});
