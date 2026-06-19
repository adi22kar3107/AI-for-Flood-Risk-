const MAHARASHTRA_CITIES = [
    "Mumbai", "Thane", "Raigad", "Ratnagiri", "Sindhudurg", "Chiplun",
    "Pune", "Kolhapur", "Satara", "Sangli", "Solapur",
    "Aurangabad", "Latur", "Nanded", "Osmanabad", "Beed", "Parbhani",
    "Nagpur", "Amravati", "Akola", "Buldhana", "Chandrapur", "Gadchiroli", "Yavatmal",
    "Nashik", "Dhule", "Nandurbar", "Jalgaon", "Ahmednagar"
];

const cityInput = document.getElementById('cityInput');
const suggestions = document.getElementById('suggestions');

cityInput.addEventListener('input', () => {
    const q = cityInput.value.trim().toLowerCase();
    if (q.length < 1) { suggestions.classList.add('hidden'); return; }
    const matches = MAHARASHTRA_CITIES.filter(c => c.toLowerCase().startsWith(q));
    if (matches.length === 0) { suggestions.classList.add('hidden'); return; }
    suggestions.innerHTML = matches.slice(0, 6).map(c =>
        `<div class="suggestion-item" onclick="selectCity('${c}')">📍 ${c}</div>`
    ).join('');
    suggestions.classList.remove('hidden');
});

document.addEventListener('click', e => {
    if (!e.target.closest('.search-container')) suggestions.classList.add('hidden');
});

window.selectCity = function (name) {
    cityInput.value = name;
    suggestions.classList.add('hidden');
    runForecast();
};

window.quickSearch = function (name) {
    cityInput.value = name;
    runForecast();
};

cityInput.addEventListener('keydown', e => { if (e.key === 'Enter') runForecast(); });
document.getElementById('forecastBtn').addEventListener('click', runForecast);

let chartInstance = null;

function loadChartJS() {
    return new Promise(resolve => {
        if (window.Chart) { resolve(); return; }
        const s = document.createElement('script');
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js';
        s.onload = resolve;
        document.head.appendChild(s);
    });
}

async function runForecast() {
    const city = cityInput.value.trim();
    if (!city) return;

    const searchError = document.getElementById('searchError');
    const emptyState = document.getElementById('emptyState');
    const forecastSection = document.getElementById('forecastSection');

    searchError.classList.add('hidden');

    const matched = MAHARASHTRA_CITIES.find(c => c.toLowerCase() === city.toLowerCase());
    if (!matched) { searchError.classList.remove('hidden'); return; }

    suggestions.classList.add('hidden');
    setButtonLoading(true);
    emptyState.classList.add('hidden');
    forecastSection.classList.add('hidden');

    try {
        await loadChartJS();
        const data = await fetch(`/api/forecast?city=${encodeURIComponent(matched)}`).then(r => r.json());
        if (data.error) {
            searchError.textContent = '⚠ ' + data.error;
            searchError.classList.remove('hidden');
            return;
        }
        renderForecast(matched, data);
        forecastSection.classList.remove('hidden');
        forecastSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
        searchError.textContent = '⚠ Could not load forecast. Please try again.';
        searchError.classList.remove('hidden');
    } finally {
        setButtonLoading(false);
    }
}

function setButtonLoading(on) {
    document.getElementById('btnText').textContent = on ? 'Loading…' : 'Get Forecast';
    document.getElementById('btnIcon').classList.toggle('hidden', on);
    document.getElementById('btnSpinner').classList.toggle('hidden', !on);
    document.getElementById('forecastBtn').disabled = on;
}

function renderForecast(cityName, days) {
    const avgRisk = days.reduce((s, d) => s + d.risk, 0) / days.length;
    const peakRisk = Math.max(...days.map(d => d.risk));
    const peakDay = days.find(d => d.risk === peakRisk);
    const overallSev = classify(avgRisk);

    document.getElementById('cityName').textContent = cityName;
    const badge = document.getElementById('overallBadge');
    badge.textContent = `Overall: ${overallSev}`;
    badge.className = `overall-badge ${overallSev.toLowerCase()}`;

    document.getElementById('summaryChips').innerHTML = `
        <div class="csb-chip">⚡ Avg Risk <strong>${avgRisk.toFixed(1)}%</strong></div>
        <div class="csb-chip">🔺 Peak <strong>${peakRisk.toFixed(1)}%</strong> on ${peakDay.label}</div>
        <div class="csb-chip">🌧 Max Rain <strong>${Math.max(...days.map(d => d.rainfall_24h))} mm</strong></div>
    `;

    renderGrid(days);
    renderChart(days);
    renderTable(days);
    renderRecommendations(days, overallSev);
}

function renderGrid(days) {
    document.getElementById('forecastGrid').innerHTML = days.map((d, i) => {
        const color = getRiskColor(d.risk);
        const sevClass = d.severity.toLowerCase();
        const icon = getWeatherIcon(d.rainfall_24h, d.temp);
        const riskClass = d.risk > 70 ? 'high-risk' : d.risk > 30 ? 'mod-risk' : 'low-risk';
        const todayPill = i === 0 ? '<span class="today-pill">TODAY</span>' : '';
        return `
            <div class="day-card ${i === 0 ? 'today' : ''} ${riskClass}" style="animation-delay:${i * 0.06}s">
                <div class="day-label">${d.label}</div>
                <div class="day-date">${d.date} ${todayPill}</div>
                <div class="day-weather-icon">${icon}</div>
                <div class="day-risk-value" style="color:${color}">${d.risk}<span class="day-risk-pct">%</span></div>
                <div class="day-bar-wrap"><div class="day-bar" style="width:${d.risk}%;background:${color}"></div></div>
                <div class="day-severity ${sevClass}">${d.severity}</div>
                <div class="day-mini-stats">
                    <div class="dms-row"><span class="dms-label">🌧 Rain</span><span class="dms-val">${d.rainfall_24h} mm</span></div>
                    <div class="dms-row"><span class="dms-label">🌡 Temp</span><span class="dms-val">${d.temp}°C</span></div>
                    <div class="dms-row"><span class="dms-label">💧 Hum.</span><span class="dms-val">${d.humidity}%</span></div>
                </div>
            </div>`;
    }).join('');
}

function renderChart(days) {
    const ctx = document.getElementById('riskChart').getContext('2d');
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: days.map(d => d.label),
            datasets: [
                {
                    label: 'Flood Risk %',
                    data: days.map(d => d.risk),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.08)',
                    pointBackgroundColor: days.map(d => getRiskColor(d.risk)),
                    pointBorderColor: days.map(d => getRiskColor(d.risk)),
                    pointRadius: 6, pointHoverRadius: 9,
                    borderWidth: 2.5, tension: 0.4, fill: true, yAxisID: 'y',
                },
                {
                    label: 'Rainfall (mm)',
                    data: days.map(d => d.rainfall_24h),
                    borderColor: '#818cf8', backgroundColor: 'transparent',
                    pointBackgroundColor: '#818cf8', pointRadius: 4,
                    borderWidth: 1.5, tension: 0.4, borderDash: [6, 3], yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { family: 'Outfit', size: 12 } } },
                tooltip: {
                    backgroundColor: 'rgba(15,23,42,0.95)', borderColor: 'rgba(59,130,246,0.4)', borderWidth: 1,
                    titleColor: '#e2e8f0', bodyColor: '#94a3b8',
                    callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}${ctx.datasetIndex === 0 ? '%' : ' mm'}` }
                }
            },
            scales: {
                x: { ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 12 } }, grid: { color: 'rgba(255,255,255,0.04)' } },
                y: { min: 0, max: 100, ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 12 }, callback: v => v + '%' }, grid: { color: 'rgba(255,255,255,0.06)' }, position: 'left' },
                y1: { min: 0, ticks: { color: '#818cf8', font: { family: 'Outfit', size: 12 }, callback: v => v + ' mm' }, grid: { drawOnChartArea: false }, position: 'right' }
            }
        }
    });
}

function renderTable(days) {
    document.getElementById('tableBody').innerHTML = days.map(d => `
        <tr>
            <td><strong>${d.label}</strong> <span style="color:var(--text-secondary);font-size:0.78rem">${d.date}</span></td>
            <td>${d.rainfall_24h}</td>
            <td>${d.temp}</td>
            <td>${d.humidity}</td>
            <td>${d.river_level}</td>
            <td>${d.soil_moisture}</td>
            <td>${d.wind_speed}</td>
            <td style="color:${getRiskColor(d.risk)};font-weight:700">${d.risk}%</td>
            <td><span class="severity-cell ${d.severity.toLowerCase()}">${d.severity}</span></td>
        </tr>`
    ).join('');
}

function renderRecommendations(days, overallSev) {
    const highDays = days.filter(d => d.severity === 'High');
    const allRecs = {
        High: [
            { emoji: '🚨', title: 'Activate Emergency Protocols', text: 'Alert local disaster management authorities and prepare evacuation routes for low-lying areas.' },
            { emoji: '🏠', title: 'Secure Properties', text: 'Move valuables to upper floors. Reinforce doors and windows. Avoid basements during peak rainfall.' },
            { emoji: '🚫', title: 'Avoid River Crossings', text: 'Do not attempt to cross rivers or flooded roads. Water levels can rise rapidly without warning.' },
            { emoji: '📻', title: 'Monitor Official Alerts', text: 'Stay tuned to Maharashtra SDMA updates and IMD weather bulletins for real-time advisories.' },
        ],
        Moderate: [
            { emoji: '⚠️', title: 'Stay Prepared', text: 'Keep emergency kits ready. Ensure drainage around your property is clear to prevent waterlogging.' },
            { emoji: '🌧', title: 'Track Rainfall Closely', text: 'Monitor hourly rainfall updates. Be ready to escalate precautions if conditions worsen.' },
            { emoji: '🚗', title: 'Limit Non-Essential Travel', text: 'Avoid travel during heavy rainfall windows, especially near ghats or low-lying roads.' },
        ],
        Low: [
            { emoji: '✅', title: 'Conditions Normal', text: 'No immediate flood risk. Maintain standard weather awareness and check forecasts regularly.' },
            { emoji: '🌱', title: 'Agricultural Advisory', text: 'Moderate soil moisture — good conditions for irrigation management. Avoid over-watering.' },
        ]
    };

    const recs = allRecs[overallSev] || allRecs['Low'];
    const highNote = highDays.length > 0 ? `
        <div class="rec-card" style="border-color:rgba(239,68,68,0.3);grid-column:1/-1">
            <span class="rec-emoji">📅</span>
            <div class="rec-text">
                <h4 style="color:var(--risk-high)">High-Risk Days: ${highDays.map(d => d.label).join(', ')}</h4>
                <p>Exercise maximum caution on these days. Avoid non-essential outdoor activities and stay near emergency shelters.</p>
            </div>
        </div>` : '';

    document.getElementById('recommendationPanel').innerHTML = `
        <div class="rec-header"><span style="font-size:1.5rem">💡</span><h3>Recommendations & Advisories</h3></div>
        <div class="rec-grid">
            ${highNote}
            ${recs.map(r => `
                <div class="rec-card">
                    <span class="rec-emoji">${r.emoji}</span>
                    <div class="rec-text"><h4>${r.title}</h4><p>${r.text}</p></div>
                </div>`).join('')}
        </div>`;
}

function getRiskColor(risk) {
    if (risk > 70) return '#ef4444';
    if (risk > 30) return '#f59e0b';
    return '#10b981';
}

function classify(risk) {
    if (risk > 70) return 'High';
    if (risk > 30) return 'Moderate';
    return 'Low';
}

function getWeatherIcon(rainfall, temp) {
    if (rainfall > 100) return '⛈️';
    if (rainfall > 40) return '🌧️';
    if (rainfall > 10) return '🌦️';
    if (temp > 35) return '☀️';
    if (temp > 28) return '⛅';
    return '🌤️';
}