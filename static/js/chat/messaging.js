// chat/messaging.js
// Send, API call, add/display message, summariseTitle, format content/time

export function attachMessagingUI(app) {
	app.sendMessage = async function () {
		const input = document.getElementById('chatInput');
		const message = input.value.trim();
		if (!message || app.isLoading) return;
		if (!app.currentPatientId) {
			const status = document.getElementById('patientStatus');
			if (status) { status.textContent = 'Select a patient before chatting.'; status.style.color = 'var(--warning-color)'; }
			return;
		}
		input.value = '';
		app.autoResizeTextarea(input);
		app.addMessage('user', message);
		app.showLoading(true);
		try {
			const response = await app.callMedicalAPI(message);
			app.addMessage('assistant', response);
			app.updateCurrentSession();
		} catch (error) {
			console.error('Error sending message:', error);
			let errorMessage = 'I apologize, but I encountered an error processing your request.';
			if (error.message.includes('500')) errorMessage = 'The server encountered an internal error. Please try again in a moment.';
			else if (error.message.includes('404')) errorMessage = 'The requested service was not found. Please check your connection.';
			else if (error.message.includes('fetch')) errorMessage = 'Unable to connect to the server. Please check your internet connection.';
			app.addMessage('assistant', errorMessage);
		} finally {
			app.showLoading(false);
		}
	};

	app.callMedicalAPI = async function (message) {
		try {
			const response = await fetch('/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					user_id: app.currentUser.id,
					patient_id: app.currentPatientId,
					doctor_id: app.currentUser.id,
					session_id: app.currentSession?.id || 'default',
					message: message,
					user_role: app.currentUser.role,
					user_specialty: app.currentUser.specialty,
					title: app.currentSession?.title || 'New Chat'
				})
			});
			if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
			const data = await response.json();
			return data.response || 'I apologize, but I received an empty response. Please try again.';
		} catch (error) {
			console.error('API call failed:', error);
			console.error('Error details:', {
				message: error.message,
				stack: error.stack,
				user: app.currentUser,
				session: app.currentSession,
				patientId: app.currentPatientId
			});
			if (error.name === 'TypeError' && error.message.includes('fetch')) return app.generateMockResponse(message);
			throw error;
		}
	};

	app.generateMockResponse = function (message) {
		const responses = [
			"Based on your question about medical topics, I can provide general information. However, please remember that this is for educational purposes only and should not replace professional medical advice.",
			"That's an interesting medical question. While I can offer some general insights, it's important to consult with healthcare professionals for personalized medical advice.",
			"I understand your medical inquiry. For accurate diagnosis and treatment recommendations, please consult with qualified healthcare providers who can assess your specific situation.",
			"Thank you for your medical question. I can provide educational information, but medical decisions should always be made in consultation with healthcare professionals.",
			"I appreciate your interest in medical topics. Remember that medical information found online should be discussed with healthcare providers for proper evaluation."
		];
		return responses[Math.floor(Math.random() * responses.length)];
	};

	app.addMessage = function (role, content) {
		if (!app.currentSession) app.startNewChat();
		const message = { id: app.generateId(), role, content, timestamp: new Date().toISOString() };
		app.currentSession.messages.push(message);
		app.displayMessage(message);
		if (role === 'user' && app.currentSession.messages.length === 2) app.summariseAndSetTitle(content);
	};

	app.summariseAndSetTitle = async function (text) {
		try {
			const resp = await fetch('/summarise', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, max_words: 5 }) });
			if (resp.ok) {
				const data = await resp.json();
				const title = (data.title || 'New Chat').trim();
				app.currentSession.title = title;
				app.updateCurrentSession();
				app.updateChatTitle();
				app.loadChatSessions();
			} else {
				const fallback = text.length > 50 ? text.substring(0, 50) + '...' : text;
				app.currentSession.title = fallback;
				app.updateCurrentSession();
				app.updateChatTitle();
				app.loadChatSessions();
			}
		} catch (e) {
			const fallback = text.length > 50 ? text.substring(0, 50) + '...' : text;
			app.currentSession.title = fallback;
			app.updateCurrentSession();
			app.updateChatTitle();
			app.loadChatSessions();
		}
	};

	app.displayMessage = function (message) {
		const chatMessages = document.getElementById('chatMessages');
		const messageElement = document.createElement('div');
		messageElement.className = `message ${message.role}-message fade-in`;
		messageElement.id = `message-${message.id}`;
		const avatar = message.role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
		const time = app.formatTime(message.timestamp);
		messageElement.innerHTML = `
			<div class="message-avatar">${avatar}</div>
			<div class="message-content">
				<div class="message-text">${app.formatMessageContent(message.content)}</div>
				<div class="message-time">${time}</div>
			</div>`;
		chatMessages.appendChild(messageElement);
		chatMessages.scrollTop = chatMessages.scrollHeight;
		if (app.currentSession) app.currentSession.lastActivity = new Date().toISOString();
	};

	app.formatMessageContent = function (content) {
		return content
			// Handle headers (1-6 # symbols)
			.replace(/^#{1,6}\s+(.+)$/gm, (match, text, offset, string) => {
				const level = match.match(/^#+/)[0].length;
				return `<h${level}>${text}</h${level}>`;
			})
			// Handle bold text
			.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
			// Handle italic text
			.replace(/\*(.*?)\*/g, '<em>$1</em>')
			// Handle line breaks
			.replace(/\n/g, '<br>')
			// Handle emojis with colors
			.replace(/🔍/g, '<span style="color: var(--primary-color);">🔍</span>')
			.replace(/📋/g, '<span style="color: var(--secondary-color);">📋</span>')
			.replace(/💊/g, '<span style="color: var(--accent-color);">💊</span>')
			.replace(/📚/g, '<span style="color: var(--success-color);">📚</span>')
			.replace(/⚠️/g, '<span style="color: var(--warning-color);">⚠️</span>');
	};

	app.formatTime = function (timestamp) {
		const date = new Date(timestamp);
		const now = new Date();
		const diff = now - date;
		if (diff < 60000) return 'Just now';
		if (diff < 3600000) { const minutes = Math.floor(diff / 60000); return `${minutes} minute${minutes > 1 ? 's' : ''} ago`; }
		if (diff < 86400000) { const hours = Math.floor(diff / 3600000); return `${hours} hour${hours > 1 ? 's' : ''} ago`; }
		return date.toLocaleDateString();
	};
}


