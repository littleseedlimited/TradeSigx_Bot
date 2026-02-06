const tele = window.Telegram.WebApp;
tele.expand();

// Use relative URL so it works through the same tunnel
const API_URL = window.location.origin;
const userId = tele.initDataUnsafe?.user?.id || 'demo_user';
let socket;

function connectWebSocket() {
    // Standardize to native WebSocket for FastAPI compatibility
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${userId}`;

    console.log('Connecting to:', wsUrl);
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('Connected to TradeSigx API via WebSocket');
        document.getElementById('trade-timer').innerText = 'LIVE';
        document.getElementById('trade-timer').style.color = '#00d4ff';
    };

    socket.onclose = () => {
        console.log('WebSocket disconnected. Retrying in 5s...');
        document.getElementById('trade-timer').innerText = 'RECONNECTING...';
        document.getElementById('trade-timer').style.color = '#ff4976';
        setTimeout(connectWebSocket, 5000);
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'signal') {
                handleNewSignal(data.data);
            } else if (data.type === 'market_update') {
                updateChartRealtime(data.data);
            }
        } catch (e) {
            console.error('WS Message Error:', e);
        }
    };
}

// Handle incoming signal push
function handleNewSignal(signal) {
    tele.HapticFeedback.notificationOccurred('success');

    const alert = document.getElementById('signal-alert');
    document.getElementById('signal-asset').innerText = `Asset: ${signal.asset}`;
    document.getElementById('signal-direction').innerText = `Direction: ${signal.direction} • Confidence: ${signal.confidence}%`;
    document.getElementById('signal-entry-time').innerText = `Entry Time: ${signal.entry_time}`;
    alert.style.display = 'block';

    setTimeout(() => alert.style.display = 'none', 10000);

    // Add to history
    addToHistory(signal);
}

function addToHistory(signal) {
    const list = document.getElementById('history-list');
    const empty = list.querySelector('.empty');
    if (empty) empty.remove();

    const item = document.createElement('div');
    item.className = 'history-item';
    const emoji = signal.direction === 'BUY' ? '🟢' : '🔴';
    item.innerHTML = `<span>${emoji} ${signal.asset} (${signal.direction})</span> <span style="color:#00d4ff">${signal.confidence}%</span>`;
    if (list.firstChild) list.insertBefore(item, list.firstChild);
    else list.appendChild(item);
}

// Initialize Chart
const chartContainer = document.getElementById('chart-container');
const chart = LightweightCharts.createChart(chartContainer, {
    layout: { backgroundColor: 'transparent', textColor: '#a0a0c0' },
    grid: { vertLines: { color: 'rgba(255, 255, 255, 0.05)' }, horzLines: { color: 'rgba(255, 255, 255, 0.05)' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: 'rgba(255, 255, 255, 0.1)' },
    timeScale: { borderColor: 'rgba(255, 255, 255, 0.1)' },
});

const candleSeries = chart.addCandlestickSeries({
    upColor: '#00d4ff',
    downColor: '#ff4976',
    borderDownColor: '#ff4976',
    borderUpColor: '#00d4ff',
    wickDownColor: '#ff4976',
    wickUpColor: '#00d4ff',
});

// Fallback Mock Data Generator (if API fails)
function generateMockData() {
    let data = [];
    let time = Math.floor(Date.now() / 1000) - 100 * 60;
    let value = 100 + Math.random() * 1000;
    for (let i = 0; i < 100; i++) {
        const open = value + (Math.random() - 0.5) * 2;
        const high = open + Math.random() * 1.5;
        const low = open - Math.random() * 1.5;
        const close = (high + low) / 2;
        data.push({ time, open, high, low, close });
        value = close;
        time += 60;
    }
    return data;
}

// Real Data Fetcher
async function fetchRealData(symbol) {
    try {
        const cleanSymbol = symbol.replace('=X', '').replace('/USD', '').replace('USDT', '');
        const fsym = cleanSymbol.split('/')[0] || cleanSymbol;
        const tsym = 'USD';

        const response = await fetch(`https://min-api.cryptocompare.com/data/v2/histominute?fsym=${fsym}&tsym=${tsym}&limit=100`);
        const json = await response.json();

        if (json.Response === "Success" && json.Data && json.Data.Data.length > 0) {
            return json.Data.Data.map(d => ({
                time: d.time,
                open: d.open,
                high: d.high,
                low: d.low,
                close: d.close
            }));
        }
    } catch (e) {
        console.error("Chart Fetch Error:", e);
    }
    return generateMockData();
}

async function updateChart(symbol) {
    const data = await fetchRealData(symbol);
    if (data.length > 0) {
        candleSeries.setData(data);
        chart.timeScale().fitContent();
    }
}

// Initial Load
updateChart('BTC/USDT');
connectWebSocket();

// Live timestamp
function startTimer() {
    setInterval(() => {
        const now = new Date();
        const time = now.toLocaleTimeString('en-US', { hour12: false });
        if (socket && socket.connected) {
            document.getElementById('trade-timer').innerText = `LIVE: ${time}`;
        }
    }, 1000);
}
startTimer();

// Handle Trading Actions
function handleTrade(direction) {
    const symbol = document.querySelector('.asset-btn.active').getAttribute('data-symbol');
    const assetTitle = document.getElementById('asset-title').innerText;

    tele.MainButton.setText(`EXECUTING ${direction} ON ${assetTitle}...`);
    tele.MainButton.show();
    tele.HapticFeedback.impactOccurred('heavy');

    // Send to API
    fetch(`${API_URL}/api/execute-trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            asset: symbol,
            direction: direction,
            user_id: userId
        })
    }).then(res => res.json()).then(data => {
        tele.MainButton.setText('TRADE EXECUTED ✅');
        tele.MainButton.setParams({ color: '#00c853' });
        setTimeout(() => tele.MainButton.hide(), 2000);
    });
}

document.getElementById('btn-buy').addEventListener('click', () => handleTrade('BUY'));
document.getElementById('btn-sell').addEventListener('click', () => handleTrade('SELL'));

// Handle Asset Selection
document.querySelectorAll('.asset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.asset-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const symbol = btn.getAttribute('data-symbol');
        document.getElementById('asset-title').innerText = btn.innerText.split(' ').slice(1).join(' ');
        updateChart(symbol);
        tele.HapticFeedback.selectionChanged();
    });
});

// Tab Switching
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const tab = item.getAttribute('data-tab');
        switchTab(tab);
    });
});

function switchTab(tab) {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelector(`.nav-item[data-tab="${tab}"]`).classList.add('active');

    // Hide all sections
    document.getElementById('chart-section').style.display = 'none';
    document.getElementById('assets-section').style.display = 'none';
    document.getElementById('history-section').style.display = 'none';
    document.getElementById('scanner-section').style.display = 'none';

    if (tab === 'dashboard') {
        document.getElementById('chart-section').style.display = 'block';
        document.getElementById('assets-section').style.display = 'block';
        document.getElementById('history-section').style.display = 'block';
    } else if (tab === 'signals') {
        document.getElementById('scanner-section').style.display = 'block';
        runMarketScan();
    } else if (tab === 'history') {
        document.getElementById('history-section').style.display = 'block';
    }
}

async function runMarketScan() {
    const grid = document.getElementById('scanner-grid');
    const status = document.getElementById('scanner-status');

    grid.innerHTML = '<div class="scanner-placeholder">🔍 Analyzing all markets... Please wait...</div>';
    status.innerText = 'SCANNING...';
    status.style.color = '#ffaa00';

    try {
        const response = await fetch(`${API_URL}/api/market-scan`);
        const data = await response.json();

        if (!data.signals || data.signals.length === 0) {
            grid.innerHTML = '<div class="scanner-placeholder">⚠️ No assets found with >= 85% confidence right now. Try again later.</div>';
            status.innerText = 'WAITING';
            return;
        }

        grid.innerHTML = '';
        data.signals.forEach(sig => {
            const card = document.createElement('div');
            card.className = 'scanner-card glass';
            card.innerHTML = `
                <div class="info">
                    <h4>${sig.asset.replace('=X', '')}</h4>
                    <p>${sig.direction} • ${sig.expiry} • ATR ${sig.trend}</p>
                </div>
                <div class="confidence-badge">${sig.confidence}%</div>
            `;
            card.onclick = () => {
                // Return to dashboard and select this asset
                switchTab('dashboard');
                document.getElementById('asset-title').innerText = sig.asset.replace('=X', '');
                updateChart(sig.asset);
                handleNewSignal(sig); // Show full details
                tele.HapticFeedback.impactOccurred('medium');
            };
            grid.appendChild(card);
        });

        status.innerText = 'COMPLETED';
        status.style.color = '#00ff88';
        tele.HapticFeedback.notificationOccurred('success');

    } catch (e) {
        console.error('Scan Error:', e);
        grid.innerHTML = '<div class="scanner-placeholder">❌ Connection Error. Ensure bot server is running.</div>';
        status.innerText = 'ERROR';
    }
}

// Auto-switch to signals if URL suggests (e.g., from Quick Analysis)
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('tab') === 'signals') {
    setTimeout(() => switchTab('signals'), 500);
}

// Mock Wallet Connection
document.getElementById('connect-wallet').addEventListener('click', () => {
    tele.MainButton.setText('Connecting Wallet...');
    tele.MainButton.show();
    setTimeout(() => {
        tele.MainButton.setText('Wallet Connected: EQ...42');
        tele.MainButton.setParams({ color: '#00d4ff' });
        document.getElementById('connect-wallet').innerText = '0x123...abc';
        setTimeout(() => tele.MainButton.hide(), 2000);
    }, 1500);
});
