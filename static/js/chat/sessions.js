// chat/sessions.js
// Session sidebar rendering, context menu, rename/delete, local storage helpers

export function attachSessionsUI(app) {
	app.getChatSessions = function () {
		const sessions = localStorage.getItem(`chatSessions_${app.currentUser.id}`);
		return sessions ? JSON.parse(sessions) : [];
	};

	app.saveCurrentSession = function () {
		if (!app.currentSession) return;
		if (app.currentSession.source === 'backend') return; // do not persist backend sessions locally here
		const sessions = app.getChatSessions();
		const existingIndex = sessions.findIndex(s => s.id === app.currentSession.id);
		if (existingIndex >= 0) sessions[existingIndex] = { ...app.currentSession };
		else sessions.unshift(app.currentSession);
		localStorage.setItem(`chatSessions_${app.currentUser.id}`, JSON.stringify(sessions));
	};

	app.updateCurrentSession = function () {
		if (app.currentSession) {
			app.currentSession.lastActivity = new Date().toISOString();
			app.saveCurrentSession();
		}
	};

	app.updateChatTitle = function () {
		const titleElement = document.getElementById('chatTitle');
		if (app.currentSession) titleElement.textContent = app.currentSession.title; else titleElement.textContent = 'Medical AI Assistant';
	};

	app.loadChatSession = function (sessionId) {
		const sessions = app.getChatSessions();
		const session = sessions.find(s => s.id === sessionId);
		if (!session) return;
		app.currentSession = session;
		app.clearChatMessages();
		session.messages.forEach(message => app.displayMessage(message));
		app.updateChatTitle();
		app.loadChatSessions();
	};

	app.deleteChatSession = function (sessionId) {
		const sessions = app.getChatSessions();
		const index = sessions.findIndex(s => s.id === sessionId);
		if (index === -1) return;
		const confirmDelete = confirm('Delete this chat session? This cannot be undone.');
		if (!confirmDelete) return;
		sessions.splice(index, 1);
		localStorage.setItem(`chatSessions_${app.currentUser.id}`, JSON.stringify(sessions));
		if (app.currentSession && app.currentSession.id === sessionId) {
			if (sessions.length > 0) {
				app.currentSession = sessions[0];
				app.clearChatMessages();
				app.currentSession.messages.forEach(m => app.displayMessage(m));
				app.updateChatTitle();
			} else {
				app.currentSession = null;
				app.clearChatMessages();
				app.updateChatTitle();
			}
		}
		app.loadChatSessions();
	};

	app.renameChatSession = function (sessionId, newTitle) {
		const sessions = app.getChatSessions();
		const idx = sessions.findIndex(s => s.id === sessionId);
		if (idx === -1) return;
		sessions[idx] = { ...sessions[idx], title: newTitle };
		localStorage.setItem(`chatSessions_${app.currentUser.id}`, JSON.stringify(sessions));
		if (app.currentSession && app.currentSession.id === sessionId) {
			app.currentSession.title = newTitle;
			app.updateChatTitle();
		}
		app.loadChatSessions();
	};

	app.showSessionMenu = function (anchorEl, sessionId) {
		// Remove existing popover
		document.querySelectorAll('.chat-session-menu-popover').forEach(p => p.remove());
		const rect = anchorEl.getBoundingClientRect();
		const pop = document.createElement('div');
		pop.className = 'chat-session-menu-popover show';
		pop.innerHTML = `
			<div class="chat-session-menu-item" data-action="edit" data-session-id="${sessionId}"><i class="fas fa-pen"></i> Edit Name</div>
			<div class="chat-session-menu-item" data-action="delete" data-session-id="${sessionId}"><i class="fas fa-trash"></i> Delete</div>
		`;
		document.body.appendChild(pop);
		pop.style.top = `${rect.bottom + window.scrollY + 6}px`;
		pop.style.left = `${rect.right + window.scrollX - pop.offsetWidth}px`;
		const onDocClick = (ev) => {
			if (!pop.contains(ev.target) && ev.target !== anchorEl) {
				pop.remove();
				document.removeEventListener('click', onDocClick);
			}
		};
		setTimeout(() => document.addEventListener('click', onDocClick), 0);
		pop.querySelectorAll('.chat-session-menu-item').forEach(item => {
			item.addEventListener('click', (e) => {
				const action = item.getAttribute('data-action');
				const id = item.getAttribute('data-session-id');
				if (action === 'delete') app.deleteChatSession(id);
				else if (action === 'edit') {
					app._pendingEditSessionId = id;
					const sessions = app.getChatSessions();
					const s = sessions.find(x => x.id === id);
					const input = document.getElementById('editSessionTitleInput');
					if (input) input.value = s ? s.title : '';
					app.showModal('editTitleModal');
				}
				pop.remove();
			});
		});
	};

	app.loadChatSessions = function () {
		const sessionsContainer = document.getElementById('chatSessions');
		sessionsContainer.innerHTML = '';
		const sessions = (app.backendSessions && app.backendSessions.length > 0) ? app.backendSessions : app.getChatSessions();
		if (sessions.length === 0) {
			sessionsContainer.innerHTML = '<div class="no-sessions">No chat sessions yet</div>';
			return;
		}
		sessions.forEach(session => {
			const sessionElement = document.createElement('div');
			sessionElement.className = `chat-session ${session.id === app.currentSession?.id ? 'active' : ''}`;
			sessionElement.addEventListener('click', async () => {
				if (session.source === 'backend') {
					app.currentSession = { ...session };
					await app.hydrateMessagesForSession(session.id);
				} else {
					app.loadChatSession(session.id);
				}
			});
			const time = app.formatTime(session.lastActivity);
			sessionElement.innerHTML = `
				<div class="chat-session-row">
					<div class="chat-session-meta">
						<div class="chat-session-title">${session.title}</div>
						<div class="chat-session-time">${time}</div>
					</div>
					<div class="chat-session-actions">
						<button class="chat-session-menu" title="Options" aria-label="Options" data-session-id="${session.id}">
							<i class="fas fa-ellipsis-vertical"></i>
						</button>
					</div>
				</div>
			`;
			sessionsContainer.appendChild(sessionElement);
			const menuBtn = sessionElement.querySelector('.chat-session-menu');
			if (session.source !== 'backend') {
				menuBtn.addEventListener('click', (e) => {
					e.stopPropagation();
					app.showSessionMenu(e.currentTarget, session.id);
				});
			} else {
				menuBtn.disabled = true;
				menuBtn.style.opacity = 0.5;
				menuBtn.title = 'Options available for local sessions only';
			}
		});
	};
}