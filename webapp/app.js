const tele = window.Telegram.WebApp;
tele.expand();

// Use relative URL so it works through the same tunnel
const API_URL = window.location.origin;
const userId = tele.initDataUnsafe?.user?.id || 'demo_user';
const SUPER_ADMIN_ID = "1241907317";
let socket;

// Identify Admin
if (userId.toString() === SUPER_ADMIN_ID) {
    document.getElementById('nav-admin').style.display = 'block';
}

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

    socket.onerror = (error) => {
        console.error('WebSocket Error Detail:', error);
        document.getElementById('trade-timer').innerText = 'CONNECTION ERROR';
        document.getElementById('trade-timer').style.color = '#ff4976';
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

// Responsive chart
const resizeObserver = new ResizeObserver(entries => {
    if (entries.length === 0 || !entries[0].contentRect) return;
    const { width, height } = entries[0].contentRect;
    chart.applyOptions({ width, height });
});
resizeObserver.observe(chartContainer);

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
    document.getElementById('admin-section').style.display = 'none';

    if (tab === 'dashboard') {
        document.getElementById('chart-section').style.display = 'block';
        document.getElementById('assets-section').style.display = 'block';
        document.getElementById('history-section').style.display = 'block';
    } else if (tab === 'signals') {
        document.getElementById('scanner-section').style.display = 'block';
        runMarketScan();
    } else if (tab === 'history') {
        document.getElementById('history-section').style.display = 'block';
    } else if (tab === 'admin') {
        document.getElementById('admin-section').style.display = 'block';
        loadAdminUsers();
    }
}

let lastLoadedUsers = [];

async function loadAdminUsers() {
    const listBody = document.getElementById('user-list-body');
    if (!listBody) return;

    listBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color: #333;">Loading users...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/api/admin/users?admin_id=${userId}`);
        lastLoadedUsers = await res.json();

        // Update Stats
        const total = lastLoadedUsers.length;
        const verified = lastLoadedUsers.filter(u => u.kyc_status === 'approved').length;

        document.getElementById('total-users-count').innerText = total;
        document.getElementById('verified-users-count').innerText = verified;

        renderUserList(lastLoadedUsers);
    } catch (e) {
        console.error('Admin Load Error:', e);
        listBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#ff4976; padding:20px;">Error loading users.</td></tr>';
    }
}

function renderUserList(users) {
    const listBody = document.getElementById('user-list-body');
    listBody.innerHTML = '';

    if (users.length === 0) {
        listBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color: #333;">No users found.</td></tr>';
        return;
    }

    users.forEach(u => {
        const tr = document.createElement('tr');
        const isVerified = u.kyc_status === 'approved';
        const joinedDate = u.joined_at ? u.joined_at.split('T')[0] : 'N/A';
        const expiryDate = u.plan_expires_at ? u.plan_expires_at.split('T')[0] : 'N/A';

        tr.innerHTML = `
            <td>
                <div class="user-cell" onclick="showUserDetails('${u.telegram_id}')" style="cursor:pointer;">
                    <span class="cell-main">${u.full_name || 'Anonymous User'}</span>
                    <span class="cell-sub">ID: ${u.telegram_id}</span>
                    <span class="cell-sub">Joined: ${joinedDate}</span>
                </div>
            </td>
            <td>
                <span class="cell-main">${u.subscription_plan.toUpperCase()}</span>
                <span class="cell-sub">Exp: ${expiryDate}</span>
            </td>
            <td class="cell-contact">
                <div>${u.email || 'No email'}</div>
                <div>${u.phone || 'No phone'}</div>
                <div class="cell-sub">${u.country || 'N/A'}</div>
            </td>
            <td>
                <span class="status-badge-new ${isVerified ? 'status-verified' : 'status-unverified'}">
                    ${isVerified ? 'Verified' : 'Unverified'}
                </span>
            </td>
            <td>
                <div class="actions-cell">
                    ${!isVerified ? `<button class="icon-btn icon-verify" onclick="adminAction('${u.telegram_id}', 'approve_kyc')" title="Verify User">✅</button>` : ''}
                    <button class="icon-btn icon-upgrade" onclick="adminAction('${u.telegram_id}', 'upgrade_plan')" title="Upgrade User Plan">↑</button>
                    <button class="icon-btn icon-ban" onclick="adminAction('${u.telegram_id}', '${u.is_banned ? 'unban' : 'ban'}')" title="${u.is_banned ? 'Unban' : 'Ban'}">🚫</button>
                    <button class="icon-btn icon-delete" onclick="adminAction('${u.telegram_id}', 'delete')" title="Delete User">🗑️</button>
                </div>
            </td>
        `;
        listBody.appendChild(tr);
    });
}

function showUserDetails(telegramId) {
    const user = lastLoadedUsers.find(u => u.telegram_id === telegramId);
    if (!user) return;

    const modalArea = document.getElementById('modal-user-info');
    const overlay = document.getElementById('admin-modal-overlay');

    let html = '';
    const fields = [
        ['ID', 'telegram_id'], ['DB ID', 'id'], ['Name', 'full_name'], ['Email', 'email'],
        ['Phone', 'phone'], ['Country', 'country'], ['Plan', 'subscription_plan'],
        ['Expiry', 'plan_expires_at'], ['KYC', 'kyc_status'], ['KYC Submitted', 'kyc_submitted_at'],
        ['Banned', 'is_banned'], ['Ban Reason', 'ban_reason'], ['Admin', 'is_admin'],
        ['Super', 'is_super_admin'], ['Balance', 'wallet_balance'], ['Signals Today', 'signals_used_today'],
        ['Timezone', 'timezone'], ['Autotrade', 'autotrade_enabled'], ['Joined', 'joined_at']
    ];

    fields.forEach(([label, key]) => {
        let val = user[key];
        if (typeof val === 'boolean') val = val ? 'YES' : 'NO';
        if (key === 'wallet_balance') val = `$${val.toFixed(2)}`;
        html += `<div class="detail-row"><span class="detail-label">${label}</span><span class="detail-value">${val || 'N/A'}</span></div>`;
    });

    modalArea.innerHTML = html;
    overlay.style.display = 'flex';
    tele.HapticFeedback.impactOccurred('medium');
}

function closeAdminModal() {
    document.getElementById('admin-modal-overlay').style.display = 'none';
}

// Search Functionality
document.getElementById('admin-user-search')?.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase();
    const filtered = lastLoadedUsers.filter(u =>
        u.telegram_id.toString().includes(term) ||
        (u.username && u.username.toLowerCase().includes(term)) ||
        (u.full_name && u.full_name.toLowerCase().includes(term)) ||
        (u.email && u.email.toLowerCase().includes(term))
    );
    renderUserList(filtered);
});

async function adminAction(targetId, action) {
    if (action === 'delete' && !confirm('Are you sure you want to delete this user?')) return;

    try {
        const res = await fetch(`${API_URL}/api/admin/user-action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                admin_id: userId.toString(),
                target_id: targetId.toString(),
                action: action
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            tele.HapticFeedback.notificationOccurred('success');
            loadAdminUsers();
        } else {
            alert('Action failed: ' + data.message);
        }
    } catch (e) {
        console.error('Admin Action Error:', e);
    }
}


// Refresh button
document.getElementById('refresh-users')?.addEventListener('click', loadAdminUsers);

// Expose admin functions to global scope
window.adminAction = adminAction;
window.showUserDetails = showUserDetails;
window.closeAdminModal = closeAdminModal;

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

// Auto-switch to signals or admin if URL suggests
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('tab') === 'signals') {
    setTimeout(() => switchTab('signals'), 500);
} else if (urlParams.get('tab') === 'admin') {
    setTimeout(() => switchTab('admin'), 500);
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
