// Tab switching functionality
function setupTabs() {
	const tabs = document.querySelectorAll('.tab-button');
	tabs.forEach(tab => {
		tab.addEventListener('click', () => {
			// Deactivate all tabs
			tabs.forEach(t => {
				t.classList.remove('active');
				document.getElementById(t.dataset.tab).classList.remove('active');
			});
			// Activate clicked tab
			tab.classList.add('active');
			document.getElementById(tab.dataset.tab).classList.add('active');
		});
	});
}

// Health status functionality
async function updateHealth() {
	try {
		const response = await fetch('/system/health');
		const data = await response.json();
		const statusHtml = `
			<p>Status: <span class="status-${data.status === 'healthy' ? 'ok' : 'error'}">${data.status}</span></p>
			<p>Timestamp: ${data.timestamp}</p>
			<h3>Components:</h3>
			${Object.entries(data.components).map(([key, value]) => `
				<div class="component">
					${key}: <span class="status-${value === 'operational' ? 'ok' : 'error'}">${value}</span>
				</div>
			`).join('')}
		`;
		document.getElementById('health-status').innerHTML = statusHtml;
	} catch (error) {
		document.getElementById('health-status').innerHTML = '<p class="status-error">Error fetching health status</p>';
	}
}

// Database status functionality
async function updateDatabase() {
	try {
		const response = await fetch('/system/database');
		const data = await response.json();
		displayDatabaseStatus(data);
	} catch (error) {
		console.error('Error fetching database status:', error);
		document.getElementById('collections').innerHTML =
			'<div class="error">Error fetching database status. Please try again later.</div>';
	}
}

function displayDatabaseStatus(data) {
	document.getElementById('db-timestamp').textContent = `Last updated: ${new Date(data.timestamp).toLocaleString()}`;

	const collectionsDiv = document.getElementById('collections');
	collectionsDiv.innerHTML = '';

	Object.entries(data.collections).forEach(([name, info]) => {
		const collectionDiv = document.createElement('div');
		collectionDiv.className = 'collection fade-in';

		const html = `
			<h2>${name}</h2>
			<div class="stats">
				<p><i class="fas fa-file-alt"></i> Document count: ${info.document_count}</p>
			</div>
			<div class="fields">
				<h3>Document Fields:</h3>
				<ul>
					${info.fields.map(field => {
						const indexInfo = info.indexes.find(idx =>
							idx.keys.some(([key]) => key === field)
						);
						const indexIcon = indexInfo ?
							`<i class="fas fa-bolt" title="Indexed"></i>` :
							`<i class="fas fa-minus" title="Not indexed"></i>`;
						return `<li>${indexIcon} ${field}</li>`;
					}).join('')}
				</ul>
			</div>
		`;

		collectionDiv.innerHTML = html;
		collectionsDiv.appendChild(collectionDiv);
	});
}

// Initialize everything
document.addEventListener('DOMContentLoaded', () => {
	setupTabs();
	updateHealth();
	updateDatabase();
	// Refresh data every 30 seconds
	setInterval(updateHealth, 30000);
	setInterval(updateDatabase, 30000);
});
