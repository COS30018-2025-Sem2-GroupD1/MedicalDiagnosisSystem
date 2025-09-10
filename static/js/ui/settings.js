// ui/settings.js
// Settings UI: theme/font preferences, showLoading overlay, settings modal wiring

export function attachSettingsUI(app) {
	app.loadUserPreferences = function () {
		const preferences = localStorage.getItem('medicalChatbotPreferences');
		if (preferences) {
			const prefs = JSON.parse(preferences);
			app.setTheme(prefs.theme || 'auto');
			app.setFontSize(prefs.fontSize || 'medium');
		}
	};

	app.setupTheme = function () {
		if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
			app.setTheme('auto');
		}
	};

	app.setTheme = function (theme) {
		const root = document.documentElement;
		if (theme === 'auto') {
			const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
			root.setAttribute('data-theme', isDark ? 'dark' : 'light');
		} else {
			root.setAttribute('data-theme', theme);
		}
		const sel = document.getElementById('themeSelect');
		if (sel) sel.value = theme;
		app.savePreferences();
	};

	app.setFontSize = function (size) {
		const root = document.documentElement;
		root.style.fontSize = size === 'small' ? '14px' : size === 'large' ? '18px' : '16px';
		app.savePreferences();
	};

	app.savePreferences = function () {
		const preferences = {
			theme: document.getElementById('themeSelect')?.value,
			fontSize: document.getElementById('fontSize')?.value,
			autoSave: document.getElementById('autoSave')?.checked,
			notifications: document.getElementById('notifications')?.checked
		};
		localStorage.setItem('medicalChatbotPreferences', JSON.stringify(preferences));
	};

	app.showLoading = function (show) {
		app.isLoading = show;
		const overlay = document.getElementById('loadingOverlay');
		const sendBtn = document.getElementById('sendBtn');
		if (!overlay || !sendBtn) return;
		if (show) {
			overlay.classList.add('show');
			sendBtn.disabled = true;
		} else {
			overlay.classList.remove('show');
			sendBtn.disabled = false;
		}
	};

	// Settings modal open/close wiring
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
}


