document.addEventListener('DOMContentLoaded', () => {
	const form = document.getElementById('patientForm');
	const result = document.getElementById('result');
	const cancelBtn = document.getElementById('cancelBtn');

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
			result.textContent = `Created patient ${data.name} (${pid}). Redirecting...`;
			localStorage.setItem('medicalChatbotPatientId', pid);
			setTimeout(() => window.location.href = '/', 800);
		} catch (err) {
			console.error(err);
			result.textContent = 'Failed to create patient. Please try again.';
			result.style.color = 'crimson';
		}
	});
});
