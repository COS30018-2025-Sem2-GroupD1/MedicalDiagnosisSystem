async function updateHealth() {
	try {
		const response = await fetch('/health');
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
		document.getElementById('status').innerHTML = statusHtml;
	} catch (error) {
		document.getElementById('status').innerHTML = '<p class="status-error">Error fetching health status</p>';
	}
}

document.addEventListener('DOMContentLoaded', () => {
	updateHealth();
	setInterval(updateHealth, 30000);
});
