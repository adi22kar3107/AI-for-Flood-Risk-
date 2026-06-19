// ─────────────────────────────────────────────────────────────────────────────
// Initialize Leaflet Map — centered on Maharashtra
// ─────────────────────────────────────────────────────────────────────────────
const map = L.map('map', {
    zoomControl: false,
    attributionControl: true,
}).setView([19.75, 76.50], 7);

// Add zoom control in top-right
L.control.zoom({ position: 'topright' }).addTo(map);

// Dark satellite-style tile layer
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
}).addTo(map);

// ─────────────────────────────────────────────────────────────────────────────
// Maharashtra GeoJSON Boundary
// We load it from a CDN that serves Indian state boundaries
// ─────────────────────────────────────────────────────────────────────────────
// Served by Flask — pre-cached from GitHub at startup, avoids CORS
const MAHARASHTRA_GEOJSON_URL = '/api/maharashtra_boundary';

let maharashtraLayer = null;

async function loadMaharashtraBoundary() {
    try {
        const res = await fetch(MAHARASHTRA_GEOJSON_URL);
        const geoData = await res.json();

        // Flask serves the pre-filtered Maharashtra feature collection
        // (NAME_1 === 'Maharashtra' confirmed from GeoJSON source)
        const maharashtraFeature = geoData;

        if (maharashtraFeature.features && maharashtraFeature.features.length > 0) {
            maharashtraLayer = L.geoJSON(maharashtraFeature, {
                style: {
                    color: '#3b82f6',
                    weight: 2.5,
                    opacity: 0.8,
                    fillColor: '#1e3a5f',
                    fillOpacity: 0.15,
                    dashArray: '6 3',
                },
                interactive: false
            }).addTo(map);

            // Fit map to Maharashtra bounds with padding
            map.fitBounds(maharashtraLayer.getBounds(), { padding: [20, 20] });
        } else {
            console.warn('Maharashtra boundary not found in GeoJSON, using fallback bounds.');
            loadFallbackBoundary();
        }
    } catch (err) {
        console.warn('Could not load boundary GeoJSON:', err);
        loadFallbackBoundary();
    }
}

function loadFallbackBoundary() {
    // Approximate Maharashtra bounding box as a rectangle fallback
    const bounds = [[15.6, 72.6], [22.1, 80.9]];
    L.rectangle(bounds, {
        color: '#3b82f6',
        weight: 2,
        opacity: 0.6,
        fill: false,
        dashArray: '8 4',
        interactive: false
    }).addTo(map);
}

// ─────────────────────────────────────────────────────────────────────────────
// Risk Color + Style Utilities
// ─────────────────────────────────────────────────────────────────────────────
function getRiskColor(risk) {
    if (risk > 70) return '#ef4444';   // Red  – High
    if (risk > 30) return '#f59e0b';   // Amber – Moderate
    return '#10b981';                  // Green – Low
}

function getRiskGlow(risk) {
    if (risk > 70) return 'rgba(239,68,68,0.45)';
    if (risk > 30) return 'rgba(245,158,11,0.45)';
    return 'rgba(16,185,129,0.45)';
}

function getRiskFill(risk) {
    if (risk > 70) return 'rgba(239,68,68,0.18)';
    if (risk > 30) return 'rgba(245,158,11,0.14)';
    return 'rgba(16,185,129,0.10)';
}

// ─────────────────────────────────────────────────────────────────────────────
// Stats counters at top of map
// ─────────────────────────────────────────────────────────────────────────────
function updateStatsBar(data) {
    const high = data.filter(d => d.severity === 'High').length;
    const mod  = data.filter(d => d.severity === 'Moderate').length;
    const low  = data.filter(d => d.severity === 'Low').length;
    const avgRisk = (data.reduce((s, d) => s + d.risk, 0) / data.length).toFixed(1);

    const el = document.getElementById('statsBar');
    if (el) {
        el.innerHTML = `
            <div class="stat-chip high-chip">
                <span class="stat-dot high"></span>
                <strong>${high}</strong> High Risk
            </div>
            <div class="stat-chip mod-chip">
                <span class="stat-dot moderate"></span>
                <strong>${mod}</strong> Moderate
            </div>
            <div class="stat-chip low-chip">
                <span class="stat-dot low"></span>
                <strong>${low}</strong> Low Risk
            </div>
            <div class="stat-chip avg-chip">
                ⚡ Avg Risk: <strong>${avgRisk}%</strong>
            </div>
        `;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Popup HTML builder
// ─────────────────────────────────────────────────────────────────────────────
function buildPopup(region, color) {
    const w = region.weather;
    const severityClass = region.severity.toLowerCase();
    return `
        <div class="map-popup-card">
            <div class="popup-header">
                <h4 class="popup-city">${region.name}</h4>
                <span class="badge ${severityClass}">${region.severity}</span>
            </div>
            <div class="popup-risk-value" style="color:${color}; text-shadow: 0 0 12px ${color}66;">
                ${region.risk}%
                <span class="popup-risk-label">Flood Risk</span>
            </div>
            <div class="popup-risk-bar-wrap">
                <div class="popup-risk-bar" style="width:${region.risk}%; background:${color}; box-shadow: 0 0 8px ${color}88;"></div>
            </div>
            <div class="popup-weather-grid">
                <div class="pw-item">🌡️ <span>${w.temp}°C</span></div>
                <div class="pw-item">💧 <span>${w.humidity}%</span></div>
                <div class="pw-item">🌧️ <span>${w.rainfall_24h} mm</span></div>
                <div class="pw-item">🏞️ <span>${w.river_level} m</span></div>
                <div class="pw-item">🌱 <span>${w.soil_moisture}%</span></div>
                <div class="pw-item">💨 <span>${w.wind_speed} km/h</span></div>
            </div>
            <div class="popup-footer">📍 Click to view in directory</div>
        </div>
    `;
}

// ─────────────────────────────────────────────────────────────────────────────
// Map Markers & Pulse Rings
// ─────────────────────────────────────────────────────────────────────────────
let mapMarkers = [];
let markerMap = {};
let latestRegionData = [];

function clearMarkers() {
    mapMarkers.forEach(layer => map.removeLayer(layer));
    mapMarkers = [];
}

function plotRegions(data) {
    clearMarkers();
    markerMap = {};
    latestRegionData = data;

    data.forEach(region => {
        const color     = getRiskColor(region.risk);
        const fillColor = getRiskFill(region.risk);
        const radius    = 14 + (region.risk / 100) * 18;   // size scales with risk

        // Outer pulse ring (large, semi-transparent)
        if (region.risk > 30) {
            const pulse = L.circleMarker([region.lat, region.lng], {
                radius: radius + 10,
                fillColor: fillColor,
                color: color,
                weight: 1.5,
                opacity: 0.35,
                fillOpacity: 0.12,
                interactive: false,
                className: `pulse-ring pulse-ring-${region.severity.toLowerCase()}`
            }).addTo(map);
            mapMarkers.push(pulse);
        }

        // Main circle marker
        const circle = L.circleMarker([region.lat, region.lng], {
            radius: radius,
            fillColor: color,
            color: '#fff',
            weight: region.risk > 70 ? 2.5 : 1.5,
            opacity: 0.9,
            fillOpacity: region.risk > 70 ? 0.75 : 0.55,
        }).addTo(map);

        circle.bindPopup(buildPopup(region, color), {
            maxWidth: 280,
            className: 'flood-popup'
        });

        // Click marker: Highlight corresponding list item and scroll it into view
        circle.on('click', () => {
            selectDistrictListItem(region.name);
        });

        markerMap[region.name] = circle;
        mapMarkers.push(circle);
    });

    updateStatsBar(data);
    populateDistrictDirectory(data);
}

// Highlight district item in sidebar list
function selectDistrictListItem(name) {
    document.querySelectorAll('.district-item').forEach(item => {
        item.classList.remove('active');
    });
    const el = document.getElementById(`district-item-${name}`);
    if (el) {
        el.classList.add('active');
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Populate District Directory list in Sidebar
function populateDistrictDirectory(data) {
    const container = document.getElementById('districtsList');
    if (!container) return;

    if (!data || data.length === 0) {
        container.innerHTML = `<div class="districts-placeholder">No data available</div>`;
        return;
    }

    // Sort by risk descending, then by name
    const sortedData = [...data].sort((a, b) => b.risk - a.risk || a.name.localeCompare(b.name));

    container.innerHTML = sortedData.map(region => {
        const severityClass = region.severity.toLowerCase();
        return `
            <div class="district-item" id="district-item-${region.name}" onclick="handleDistrictClick('${region.name}', ${region.lat}, ${region.lng})">
                <div class="district-info">
                    <span class="district-name">${region.name}</span>
                    <span class="district-meta">🌧️ ${region.weather.rainfall_24h} mm | 🏞️ ${region.weather.river_level} m</span>
                </div>
                <div class="district-risk-indicator">
                    <span class="mini-risk-badge ${severityClass}">${region.risk}%</span>
                </div>
            </div>
        `;
    }).join('');

    // Trigger search filter to maintain filter state if user is typing
    filterDistricts();
}

// Click district card in sidebar -> center map and open marker popup
window.handleDistrictClick = function(name, lat, lng) {
    document.querySelectorAll('.district-item').forEach(item => {
        item.classList.remove('active');
    });
    const el = document.getElementById(`district-item-${name}`);
    if (el) el.classList.add('active');

    map.setView([lat, lng], 9.5, { animate: true, duration: 1 });
    
    if (markerMap[name]) {
        markerMap[name].openPopup();
    }
};

// Filter districts based on search input
function filterDistricts() {
    const searchInput = document.getElementById('districtSearch');
    if (!searchInput) return;

    const query = searchInput.value.toLowerCase().trim();
    const items = document.querySelectorAll('.district-item');

    items.forEach(item => {
        const name = item.id.replace('district-item-', '').toLowerCase();
        if (name.includes(query)) {
            item.classList.remove('hidden');
        } else {
            item.classList.add('hidden');
        }
    });
}

// Attach Search event listener
const searchInput = document.getElementById('districtSearch');
if (searchInput) {
    searchInput.addEventListener('input', filterDistricts);
}

// ─────────────────────────────────────────────────────────────────────────────
// Fetch Region Data from API
// ─────────────────────────────────────────────────────────────────────────────
async function loadRegionData() {
    const loadingOverlay = document.getElementById('mapLoadingOverlay');
    if (loadingOverlay) loadingOverlay.classList.remove('hidden');

    try {
        const response = await fetch('/api/regions');
        const data = await response.json();
        plotRegions(data);
    } catch (error) {
        console.error('Error loading regional data:', error);
    } finally {
        if (loadingOverlay) loadingOverlay.classList.add('hidden');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot sequence
// ─────────────────────────────────────────────────────────────────────────────
loadMaharashtraBoundary();
loadRegionData();

// Auto-refresh every 5 minutes to stay current
setInterval(loadRegionData, 300_000);
