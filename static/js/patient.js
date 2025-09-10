document.addEventListener('DOMContentLoaded', () => {
	const form = document.getElementById('patientForm');
	const result = document.getElementById('result');
	const cancelBtn = document.getElementById('cancelBtn');
	const successModal = document.getElementById('patientSuccessModal');
	const successClose = document.getElementById('patientSuccessClose');
	const successReturn = document.getElementById('patientSuccessReturn');
	const successEdit = document.getElementById('patientSuccessEdit');
	const createdIdEl = document.getElementById('createdPatientId');

	cancelBtn.addEventListener('click', () => {
		window.location.href = '/';
	});

	form.addEventListener('submit', async (e) => {
		e.preventDefault();
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
			const resp = await fetch('/patients', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (!resp.ok) {
				throw new Error(`HTTP ${resp.status}`);
			}
			const data = await resp.json();
			const pid = data.patient_id;
			localStorage.setItem('medicalChatbotPatientId', pid);
			// Show success modal
			if (createdIdEl) createdIdEl.textContent = pid;
			successModal.classList.add('show');
		} catch (err) {
			console.error(err);
			result.textContent = 'Failed to create patient. Please try again.';
			result.style.color = 'crimson';
		}
	});

	// Success modal wiring
	if (successClose) successClose.addEventListener('click', () => successModal.classList.remove('show'));
	if (successReturn) successReturn.addEventListener('click', () => { window.location.href = '/'; });
	if (successEdit) successEdit.addEventListener('click', () => { successModal.classList.remove('show'); });
});
