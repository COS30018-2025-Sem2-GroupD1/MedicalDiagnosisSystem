// ui/doctor.js
// Doctor list load/save, dropdown populate, create-flow, show/save profile

export function attachDoctorUI(app) {
	// Model: list of doctors persisted in localStorage
	app.loadDoctors = function () {
		try {
			const raw = localStorage.getItem('medicalChatbotDoctors');
			const arr = raw ? JSON.parse(raw) : [];
			const seen = new Set();
			return arr.filter(x => x && x.name && !seen.has(x.name) && seen.add(x.name));
		} catch { return []; }
	};

	app.saveDoctors = function () {
		localStorage.setItem('medicalChatbotDoctors', JSON.stringify(app.doctors));
	};

	app.populateDoctorSelect = function () {
		const sel = document.getElementById('profileNameSelect');
		const newSec = document.getElementById('newDoctorSection');
		if (!sel) return;
		sel.innerHTML = '';
		const createOpt = document.createElement('option');
		createOpt.value = '__create__';
		createOpt.textContent = 'Create doctor user...';
		sel.appendChild(createOpt);
		// Ensure no duplicates, include current doctor
		const names = new Set(app.doctors.map(d => d.name));
		if (app.currentUser?.name && !names.has(app.currentUser.name)) {
			app.doctors.unshift({ name: app.currentUser.name });
			names.add(app.currentUser.name);
			app.saveDoctors();
		}
		app.doctors.forEach(d => {
			const opt = document.createElement('option');
			opt.value = d.name;
			opt.textContent = d.name;
			if (app.currentUser?.name === d.name) opt.selected = true;
			sel.appendChild(opt);
		});
		sel.addEventListener('change', () => {
			if (sel.value === '__create__') {
				newSec.style.display = '';
				const input = document.getElementById('newDoctorName');
				if (input) input.value = '';
			} else {
				newSec.style.display = 'none';
			}
		});
		const cancelBtn = document.getElementById('cancelNewDoctor');
		const confirmBtn = document.getElementById('confirmNewDoctor');
		if (cancelBtn) cancelBtn.onclick = () => { newSec.style.display = 'none'; sel.value = app.currentUser?.name || ''; };
		if (confirmBtn) confirmBtn.onclick = () => {
			const name = (document.getElementById('newDoctorName').value || '').trim();
			if (!name) return;
			if (!app.doctors.find(d => d.name === name)) {
				app.doctors.unshift({ name });
				app.saveDoctors();
			}
			app.populateDoctorSelect();
			sel.value = name;
			newSec.style.display = 'none';
		};
	};

	app.showUserModal = function () {
		app.populateDoctorSelect();
		const sel = document.getElementById('profileNameSelect');
		if (sel && sel.options.length === 0) {
			const createOpt = document.createElement('option');
			createOpt.value = '__create__';
			createOpt.textContent = 'Create doctor user...';
			sel.appendChild(createOpt);
		}
		if (sel && !sel.value) sel.value = app.currentUser?.name || '__create__';
		document.getElementById('profileRole').value = app.currentUser.role;
		document.getElementById('profileSpecialty').value = app.currentUser.specialty || '';
		app.showModal('userModal');
	};

	app.saveUserProfile = function () {
		const nameSel = document.getElementById('profileNameSelect');
		const name = nameSel ? nameSel.value : '';
		const role = document.getElementById('profileRole').value;
		const specialty = document.getElementById('profileSpecialty').value.trim();

		if (!name || name === '__create__') {
			alert('Please select or create a doctor name.');
			return;
		}

		if (!app.doctors.find(d => d.name === name)) {
			app.doctors.unshift({ name });
			app.saveDoctors();
		}

		app.currentUser.name = name;
		app.currentUser.role = role;
		app.currentUser.specialty = specialty;

		app.saveUser();
		app.updateUserDisplay();
		app.hideModal('userModal');
	};

	// Doctor modal open/close wiring
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
}


