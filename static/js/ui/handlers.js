// ui/handlers.js
// DOM wiring helpers: sidebar open/close, modal wiring, textarea autosize, export/clear

export function attachUIHandlers(app) {
	// Sidebar toggle implementation
	app.toggleSidebar = function () {
		const sidebar = document.getElementById('sidebar');
		if (sidebar) sidebar.classList.toggle('show');
	};

	// Textarea autosize
	app.autoResizeTextarea = function (textarea) {
		if (!textarea) return;
		textarea.style.height = 'auto';
		textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
	};

	// Export current chat as JSON
	app.exportChat = function () {
		if (!app.currentSession || app.currentSession.messages.length === 0) {
			alert('No chat to export.');
			return;
		}
		const chatData = {
			user: app.currentUser?.name || 'Unknown',
			session: app.currentSession.title,
			date: new Date().toISOString(),
			messages: app.currentSession.messages
		};
		const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `medical-chat-${app.currentSession.title.replace(/[^a-z0-9]/gi, '-')}.json`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	};

	// Clear current chat
	app.clearChat = function () {
		if (confirm('Are you sure you want to clear this chat? This action cannot be undone.')) {
			app.clearChatMessages();
			if (app.currentSession) {
				app.currentSession.messages = [];
				app.currentSession.title = 'New Chat';
				app.updateChatTitle();
			}
		}
	};

	// Generic modal helpers
	app.showModal = function (modalId) {
		document.getElementById(modalId)?.classList.add('show');
	};
	app.hideModal = function (modalId) {
		document.getElementById(modalId)?.classList.remove('show');
	};
}


