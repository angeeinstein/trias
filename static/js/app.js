// API base URL
const API_BASE = window.location.origin;

// DOM Elements
const tabs = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');
const loading = document.getElementById('loading');

// Search tab
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const searchResults = document.getElementById('search-results');

// Nearby tab
const latInput = document.getElementById('lat-input');
const lonInput = document.getElementById('lon-input');
const radiusInput = document.getElementById('radius-input');
const nearbyBtn = document.getElementById('nearby-btn');
const geolocationBtn = document.getElementById('geolocation-btn');
const nearbyResults = document.getElementById('nearby-results');

// Departures tab
const stopIdInput = document.getElementById('stop-id-input');
const departureLimitInput = document.getElementById('departure-limit');
const departureWindowInput = document.getElementById('departure-window');
const realtimeCheck = document.getElementById('realtime-check');
const departuresBtn = document.getElementById('departures-btn');
const departuresResults = document.getElementById('departures-results');

// Route planning tab
const routeOriginInput = document.getElementById('route-origin');
const routeDestinationInput = document.getElementById('route-destination');
const routeLimitInput = document.getElementById('route-limit');
const routeRealtimeCheck = document.getElementById('route-realtime-check');
const routeBtn = document.getElementById('route-btn');
const routeResults = document.getElementById('route-results');

// Tab switching
tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        
        // Update active tab button
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Update active tab content
        tabContents.forEach(content => content.classList.remove('active'));
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Clear countdown interval when leaving departures tab
        if (tabName !== 'departures' && window.countdownInterval) {
            clearInterval(window.countdownInterval);
            window.countdownInterval = null;
        }
    });
});

// Show/hide loading overlay
function showLoading() {
    loading.classList.remove('hidden');
}

function hideLoading() {
    loading.classList.add('hidden');
}

// Display error message
function showError(container, message) {
    container.innerHTML = `<div class="error-message">❌ ${message}</div>`;
}

// Display info message
function showInfo(container, message) {
    container.innerHTML = `<div class="info-message">ℹ️ ${message}</div>`;
}

// Format time from ISO string
function formatTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleTimeString('de-AT', { hour: '2-digit', minute: '2-digit' });
}

// Format time with seconds from ISO string
function formatTimeWithSeconds(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleTimeString('de-AT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// Calculate and update countdowns
function updateCountdowns() {
    const now = new Date();
    const countdowns = document.querySelectorAll('.countdown[data-target]');
    
    countdowns.forEach(countdown => {
        const targetTime = new Date(countdown.dataset.target);
        const diffMs = targetTime - now;
        
        if (diffMs < 0) {
            countdown.textContent = 'Abgefahren';
            countdown.style.color = '#999';
            return;
        }
        
        const totalSeconds = Math.floor(diffMs / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        
        if (minutes > 60) {
            countdown.textContent = `in ${Math.floor(minutes / 60)}h ${minutes % 60}min`;
        } else if (minutes > 0) {
            countdown.textContent = `in ${minutes}min ${seconds}s`;
        } else {
            countdown.textContent = `in ${seconds}s`;
            countdown.style.fontWeight = 'bold';
            countdown.style.color = '#ef4444';
        }
    });
}

// Search for locations by name
async function searchLocation(query) {
    showLoading();
    searchResults.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/api/search/location?q=${encodeURIComponent(query)}&limit=20`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Fehler beim Laden der Daten');
        }
        
        if (data.results.length === 0) {
            showInfo(searchResults, 'Keine Haltestellen gefunden. Versuchen Sie einen anderen Suchbegriff.');
            return;
        }
        
        displayLocationResults(searchResults, data.results);
    } catch (error) {
        showError(searchResults, error.message);
    } finally {
        hideLoading();
    }
}

// Search for nearby locations
async function searchNearby(lat, lon, radius) {
    showLoading();
    nearbyResults.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/api/search/nearby?lat=${lat}&lon=${lon}&radius=${radius}&limit=50`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Fehler beim Laden der Daten');
        }
        
        if (data.results.length === 0) {
            showInfo(nearbyResults, 'Keine Haltestellen in der Nähe gefunden. Versuchen Sie einen größeren Radius.');
            return;
        }
        
        displayLocationResults(nearbyResults, data.results);
    } catch (error) {
        showError(nearbyResults, error.message);
    } finally {
        hideLoading();
    }
}

// Get departures for a stop
async function getDepartures(stopId, limit, window, realtime) {
    showLoading();
    departuresResults.innerHTML = '';
    
    try {
        const response = await fetch(
            `${API_BASE}/api/departures?stop_id=${encodeURIComponent(stopId)}&limit=${limit}&window=${window}&realtime=${realtime}`
        );
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Fehler beim Laden der Daten');
        }
        
        if (data.departures.length === 0) {
            showInfo(departuresResults, 'Keine Abfahrten in diesem Zeitfenster gefunden.');
            return;
        }
        
        displayDepartures(data.departures);
    } catch (error) {
        showError(departuresResults, error.message);
    } finally {
        hideLoading();
    }
}

// Get route/trip from origin to destination
async function getRoute(origin, destination, limit, realtime) {
    showLoading();
    routeResults.innerHTML = '';
    
    try {
        const response = await fetch(
            `${API_BASE}/api/trip?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&limit=${limit}&realtime=${realtime}`
        );
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Fehler beim Laden der Daten');
        }
        
        if (!data.trips || data.trips.length === 0) {
            showInfo(routeResults, 'Keine Verbindungen gefunden.');
            return;
        }
        
        displayTrips(data);
    } catch (error) {
        showError(routeResults, error.message);
    } finally {
        hideLoading();
    }
}

// Display location results
function displayLocationResults(container, results) {
    container.innerHTML = results.map(result => {
        const platformInfo = result.platforms > 1 ? ` (${result.platforms} platforms)` : '';
        const stopIds = result.stop_ids || [result.stop_id];
        const stopIdDisplay = stopIds.length > 1 
            ? `${stopIds.length} stops: ${stopIds.slice(0, 3).join(', ')}${stopIds.length > 3 ? '...' : ''}`
            : stopIds[0];
        
        return `
            <div class="result-item" onclick="selectStop('${result.stop_id}', '${escapeHtml(result.stop_name)}')">
                <h3>${escapeHtml(result.stop_name || 'Unbekannt')}${platformInfo}</h3>
                ${result.locality ? `<p>📍 ${escapeHtml(result.locality)}</p>` : ''}
                ${result.latitude && result.longitude ? 
                    `<p>🌐 ${result.latitude.toFixed(6)}, ${result.longitude.toFixed(6)}</p>` : ''}
                <span class="stop-id">${escapeHtml(stopIdDisplay)}</span>
            </div>
        `;
    }).join('');
}

// Display departures
function displayDepartures(departures) {
    departuresResults.innerHTML = '';
    
    departures.forEach((dep, index) => {
        const depDiv = document.createElement('div');
        depDiv.className = 'departure-item';
        depDiv.dataset.index = index;
        depDiv.dataset.actualTime = dep.actual_time;
        depDiv.dataset.hasRealtime = dep.has_realtime;
        
        const delayClass = dep.delay_minutes > 0 ? 'delayed' : (dep.delay_minutes < 0 ? 'early' : '');
        if (delayClass) {
            depDiv.classList.add(delayClass);
        }
        
        let delayBadge = '';
        if (dep.delay_minutes !== null && dep.delay_minutes !== 0) {
            const delayClass2 = dep.delay_minutes > 0 ? 'positive' : 'negative';
            const delaySign = dep.delay_minutes > 0 ? '+' : '';
            delayBadge = `<div class="departure-delay ${delayClass2}">${delaySign}${dep.delay_minutes} min</div>`;
        }
        
        depDiv.innerHTML = `
            <div class="departure-info">
                <div>
                    <span class="departure-line">${escapeHtml(dep.line || '?')}</span>
                    <span class="departure-destination">${escapeHtml(dep.destination || 'Unbekannt')}</span>
                    ${dep.mode ? `<span class="departure-mode">${escapeHtml(dep.mode)}</span>` : ''}
                    ${dep.has_realtime ? '<span class="departure-realtime-badge">🔴 Live</span>' : '<span class="departure-static-badge">📅 Fahrplan</span>'}
                </div>
            </div>
            <div class="departure-time">
                ${dep.has_realtime ? `
                    <div class="departure-actual" data-time="${dep.actual_time}">
                        <div class="time-label">Tatsächlich:</div>
                        <div class="time-value">${formatTime(dep.actual_time)}</div>
                        <div class="countdown" data-target="${dep.actual_time}">Berechne...</div>
                    </div>
                    ${dep.planned_time !== dep.estimated_time ? `
                        <div class="departure-planned">
                            <div class="time-label">Geplant:</div>
                            <div class="time-value">${formatTime(dep.planned_time)}</div>
                        </div>
                    ` : ''}
                ` : `
                    <div class="departure-planned">
                        <div class="time-label">Geplant:</div>
                        <div class="time-value">${formatTime(dep.planned_time)}</div>
                        <div class="countdown" data-target="${dep.planned_time}">Berechne...</div>
                    </div>
                `}
                ${delayBadge}
            </div>
        `;
        
        departuresResults.appendChild(depDiv);
    });
    
    // Start countdown updates
    updateCountdowns();
    if (window.countdownInterval) {
        clearInterval(window.countdownInterval);
    }
    window.countdownInterval = setInterval(updateCountdowns, 1000);
}

// Display trips/routes
function displayTrips(data) {
    let html = `
        <div class="route-header">
            <h3>Von: ${escapeHtml(data.origin.name)}</h3>
            <h3>Nach: ${escapeHtml(data.destination.name)}</h3>
        </div>
    `;
    
    html += data.trips.map((trip, idx) => {
        const startTime = formatTime(trip.start_time);
        const endTime = formatTime(trip.end_time);
        const duration = parseDuration(trip.duration);
        
        let legsHtml = trip.legs.map(leg => {
            if (leg.type === 'continuous' && leg.mode === 'walk') {
                return `
                    <div class="trip-leg walk-leg">
                        <div class="leg-icon">🚶</div>
                        <div class="leg-details">
                            <div class="leg-mode">Fußweg</div>
                            <div class="leg-route">${escapeHtml(leg.from)} → ${escapeHtml(leg.to)}</div>
                            ${leg.duration ? `<div class="leg-duration">${parseDuration(leg.duration)}</div>` : ''}
                        </div>
                        <div class="leg-times">
                            <div>${formatTime(leg.departure_time)}</div>
                            <div>${formatTime(leg.arrival_time)}</div>
                        </div>
                    </div>
                `;
            } else {
                const modeIcon = getModeIcon(leg.mode);
                return `
                    <div class="trip-leg transit-leg">
                        <div class="leg-icon">${modeIcon}</div>
                        <div class="leg-details">
                            <div class="leg-line">${escapeHtml(leg.line)}</div>
                            <div class="leg-mode">${escapeHtml(leg.mode)}${leg.destination ? ` → ${escapeHtml(leg.destination)}` : ''}</div>
                            <div class="leg-route">${escapeHtml(leg.from)} → ${escapeHtml(leg.to)}</div>
                        </div>
                        <div class="leg-times">
                            <div>${formatTime(leg.departure_time)}</div>
                            <div>${formatTime(leg.arrival_time)}</div>
                        </div>
                    </div>
                `;
            }
        }).join('');
        
        return `
            <div class="trip-card">
                <div class="trip-header">
                    <div class="trip-number">Verbindung ${idx + 1}</div>
                    <div class="trip-summary">
                        <span class="trip-time">${startTime} → ${endTime}</span>
                        ${duration ? `<span class="trip-duration">${duration}</span>` : ''}
                    </div>
                </div>
                <div class="trip-legs">
                    ${legsHtml}
                </div>
            </div>
        `;
    }).join('');
    
    routeResults.innerHTML = html;
}

// Get mode icon
function getModeIcon(mode) {
    const icons = {
        'tram': '🚊',
        'bus': '🚌',
        'train': '🚆',
        'metro': '🚇',
        'subway': '🚇',
        'rail': '🚆'
    };
    return icons[mode.toLowerCase()] || '🚆';
}

// Parse ISO 8601 duration (PT15M, PT1H30M, etc.)
function parseDuration(duration) {
    if (!duration) return '';
    
    const match = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
    if (!match) return duration;
    
    const hours = parseInt(match[1] || 0);
    const minutes = parseInt(match[2] || 0);
    
    if (hours > 0) {
        return `${hours}h ${minutes}min`;
    }
    return `${minutes}min`;
}

// Select a stop (switch to departures tab and fill in stop ID)
function selectStop(stopId, stopName) {
    stopIdInput.value = stopId;
    
    // Switch to departures tab
    tabs.forEach(t => t.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    
    document.querySelector('[data-tab="departures"]').classList.add('active');
    document.getElementById('departures-tab').classList.add('active');
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event Listeners

// Search button
searchBtn.addEventListener('click', () => {
    const query = searchInput.value.trim();
    if (query) {
        searchLocation(query);
    } else {
        showError(searchResults, 'Bitte geben Sie einen Suchbegriff ein.');
    }
});

// Enter key in search input
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchBtn.click();
    }
});

// Nearby search button
nearbyBtn.addEventListener('click', () => {
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    const radius = parseInt(radiusInput.value);
    
    if (isNaN(lat) || isNaN(lon)) {
        showError(nearbyResults, 'Bitte geben Sie gültige Koordinaten ein.');
        return;
    }
    
    if (isNaN(radius) || radius < 100) {
        showError(nearbyResults, 'Bitte geben Sie einen gültigen Radius (min. 100m) ein.');
        return;
    }
    
    searchNearby(lat, lon, radius);
});

// Geolocation button
geolocationBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
        showError(nearbyResults, 'Geolocation wird von Ihrem Browser nicht unterstützt.');
        return;
    }
    
    showLoading();
    navigator.geolocation.getCurrentPosition(
        (position) => {
            hideLoading();
            latInput.value = position.coords.latitude.toFixed(6);
            lonInput.value = position.coords.longitude.toFixed(6);
            
            // Automatically search
            nearbyBtn.click();
        },
        (error) => {
            hideLoading();
            showError(nearbyResults, 'Standort konnte nicht ermittelt werden: ' + error.message);
        }
    );
});

// Departures button
departuresBtn.addEventListener('click', () => {
    const stopId = stopIdInput.value.trim();
    const limit = parseInt(departureLimitInput.value);
    const window = parseInt(departureWindowInput.value);
    const realtime = realtimeCheck.checked;
    
    if (!stopId) {
        showError(departuresResults, 'Bitte geben Sie eine Haltestellen-ID ein.');
        return;
    }
    
    getDepartures(stopId, limit, window, realtime);
});

// Enter key in stop ID input
stopIdInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        departuresBtn.click();
    }
});

// Route planning button
routeBtn.addEventListener('click', () => {
    const origin = routeOriginInput.value.trim();
    const destination = routeDestinationInput.value.trim();
    const limit = parseInt(routeLimitInput.value);
    const realtime = routeRealtimeCheck.checked;
    
    if (!origin || !destination) {
        showError(routeResults, 'Bitte geben Sie Start und Ziel ein.');
        return;
    }
    
    getRoute(origin, destination, limit, realtime);
});

// Enter key in route inputs
routeOriginInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        routeDestinationInput.focus();
    }
});

routeDestinationInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        routeBtn.click();
    }
});

// Auto-refresh departures every 30 seconds when on departures tab
let autoRefreshInterval = null;

function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(() => {
        const departuresTab = document.getElementById('departures-tab');
        if (departuresTab.classList.contains('active') && stopIdInput.value.trim()) {
            // Silently refresh without showing loading overlay
            const stopId = stopIdInput.value.trim();
            const limit = parseInt(departureLimitInput.value);
            const window = parseInt(departureWindowInput.value);
            const realtime = realtimeCheck.checked;
            
            fetch(`${API_BASE}/api/departures?stop_id=${encodeURIComponent(stopId)}&limit=${limit}&window=${window}&realtime=${realtime}`)
                .then(response => response.json())
                .then(data => {
                    if (data.departures && data.departures.length > 0) {
                        displayDepartures(data.departures);
                    }
                })
                .catch(error => console.error('Auto-refresh failed:', error));
        }
    }, 30000); // 30 seconds
}

// Start auto-refresh when viewing departures
document.querySelector('[data-tab="departures"]').addEventListener('click', startAutoRefresh);

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Stop auto-refresh when switching tabs
tabs.forEach(tab => {
    if (tab.dataset.tab !== 'departures') {
        tab.addEventListener('click', stopAutoRefresh);
    }
});
