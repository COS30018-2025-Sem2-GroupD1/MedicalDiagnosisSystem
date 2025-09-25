async function fetchDatabaseStatus() {
    try {
        const response = await fetch('/database');
        const data = await response.json();
        displayStatus(data);
    } catch (error) {
        console.error('Error fetching database status:', error);
        document.getElementById('collections').innerHTML =
            '<div class="error">Error fetching database status. Please try again later.</div>';
    }
}

function displayStatus(data) {
    document.getElementById('timestamp').textContent = `Last updated: ${data.timestamp}`;

    const collectionsDiv = document.getElementById('collections');
    collectionsDiv.innerHTML = '';

    Object.entries(data.collections).forEach(([name, info]) => {
        const collectionDiv = document.createElement('div');
        collectionDiv.className = 'collection';

        const html = `
            <h2>${name}</h2>
            <div class="stats">
                <p>Document count: ${info.document_count}</p>
            </div>
            <div class="fields">
                <h3>Document Fields:</h3>
                <ul>
                    ${info.fields.map(field => {
                        const indexInfo = info.indexes.find(idx =>
                            idx.keys.some(([key]) => key === field)
                        );
                        const indexDetails = indexInfo ?
                            ` (Index: ${indexInfo.keys.map(([key, direction]) =>
                                `${direction === 1 ? '↑' : '↓'}`).join('')})` : '';
                        return `<li>${field}${indexDetails}</li>`;
                    }).join('')}
                </ul>
            </div>
        `;

        collectionDiv.innerHTML = html;
        collectionsDiv.appendChild(collectionDiv);
    });
}

// Fetch status immediately and refresh every 30 seconds
fetchDatabaseStatus();
setInterval(fetchDatabaseStatus, 30000);
