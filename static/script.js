document.addEventListener('DOMContentLoaded', () => {
    // Extract region and type from URL path
    const pathParts = window.location.pathname.split('/').filter(p => p);
    // Path format: /view/{region_name}/{render_type}
    const regionName = pathParts[1] || 'Unknown';
    const renderType = pathParts[2] || 'sim';

    document.title = `THE LIFESTREAM [${renderType.toUpperCase()}]`;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/${regionName}/${renderType}`;

    const overlay = document.getElementById('status-overlay');
    const headerTitle = document.getElementById('region-title');
    const topStats = document.getElementById('top-stats');
    const tableHeader = document.getElementById('table-header');
    const tableBody = document.getElementById('table-body');
    const chartContainer = document.getElementById('chart-container');
    const canvas = document.getElementById('sparkline');
    const ctx = canvas.getContext('2d');

    headerTitle.textContent = `THE_LIFESTREAM [${renderType.toUpperCase()}]`;

    // Set up table headers based on type
    if (renderType === 'sim') {
        tableHeader.innerHTML = `
            <div class="col-1">USER</div>
            <div class="col-2">SCRIPTS (T/A)</div>
            <div class="col-3">TIME (ms)</div>
            <div class="col-4">MEMORY</div>
            <div class="col-5">CMPLX</div>
        `;
    } else {
        tableHeader.innerHTML = `
            <div class="col-1">ZONE</div>
            <div class="col-2">OCCUPANCY</div>
            <div class="col-3">DYNAMIC</div>
            <div class="col-4">LI (EST)</div>
            <div class="col-5">STATE</div>
        `;
        chartContainer.style.display = 'block';
    }

    let currentState = [];
    const rowHeightVH = 6; // height of each row in vh

    function connectWebSocket() {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('Connected to WebSocket');
            overlay.style.opacity = '0';
            setTimeout(() => overlay.style.display = 'none', 500);
        };

        ws.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                handleData(payload);
            } catch(e) {
                console.error("Error parsing message", e);
            }
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected. Reconnecting in 2s...');
            overlay.style.display = 'flex';
            overlay.style.opacity = '1';
            document.getElementById('status-text').textContent = 'CONNECTION LOST';
            setTimeout(connectWebSocket, 2000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error', error);
        };
    }

    function drawSparkline(history) {
        if (!history || history.length < 2) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const chartW = canvas.width;
        const chartH = canvas.height;

        let min_val = Math.min(...history);
        let max_val = Math.max(...history);

        if (max_val === min_val) {
            min_val -= 10;
            max_val += 10;
        }

        const size = history.length;
        const points = [];

        for (let j = 0; j < size; j++) {
            const val = history[j];
            const px = (j / Math.max(1, size - 1)) * chartW;
            const py = chartH - ((val - min_val) / (max_val - min_val)) * chartH;
            points.push({x: px, y: py});
        }

        // Draw filled polygon
        ctx.beginPath();
        ctx.moveTo(points[0].x, chartH);
        points.forEach(p => ctx.lineTo(p.x, p.y));
        ctx.lineTo(points[points.length-1].x, chartH);
        ctx.closePath();
        ctx.fillStyle = "rgba(0, 255, 209, 0.2)"; // Cyan with alpha (~50/255)
        ctx.fill();

        // Draw outline line
        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        points.forEach(p => ctx.lineTo(p.x, p.y));
        ctx.strokeStyle = "#00ffd1"; // ACCENT_CYAN
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    function handleData(payload) {
        const data = payload.data || {};
        const primsHistory = payload.primsHistory || [];
        const isSim = renderType === 'sim';

        if (!isSim && primsHistory.length > 0) {
            drawSparkline(primsHistory);
        }

        // Update Stats
        updateStats(data, isSim);

        // Update Table
        let newItems = [];
        if (isSim) {
            newItems = data.users || [];
        } else {
            newItems = data.zones || [];
        }

        renderTable(newItems, isSim);
    }

    function updateStats(data, isSim) {
        let statsHtml = '';
        if (isSim) {
            const agents = data.agents || 0;
            const fps = data.fps || 0.0;
            const dilation = data.dilation || 0.0;
            const lag = data.lag || 0;

            let lagClass = lag > 10 ? 'val-bad' : '';

            statsHtml = `
                <div class="stat-box"><span class="stat-label">Roleplayers</span><span class="stat-value">${agents}</span></div>
                <div class="stat-box"><span class="stat-label">FPS</span><span class="stat-value">${fps.toFixed(1)}</span></div>
                <div class="stat-box"><span class="stat-label">Time Dilation</span><span class="stat-value">${dilation.toFixed(2)}</span></div>
                <div class="stat-box"><span class="stat-label">Lag</span><span class="stat-value ${lagClass}">${lag} %</span></div>
            `;
        } else {
            const remainingPrims = data.remaining_prims || 0;
            let primClass = remainingPrims < 100 ? 'val-bad' : '';

            statsHtml = `
                <div class="stat-box"><span class="stat-label">Remaining Prims</span><span class="stat-value ${primClass}">${remainingPrims}</span></div>
            `;
        }
        topStats.innerHTML = statsHtml;
    }

    function renderTable(newItems, isSim) {
        const currentMap = new Map();
        currentState.forEach(item => currentMap.set(item.uuid || item.name, item));

        const newMap = new Map();
        newItems.forEach((item, index) => {
            // some zones might not have uuid, use name as fallback key
            const key = item.uuid || item.name;
            item._key = key;
            item._index = index;
            newMap.set(key, item);
        });

        currentState.forEach(item => {
            const key = item.uuid || item.name;
            if (!newMap.has(key)) {
                const rowEl = document.getElementById(`row-${key}`);
                if (rowEl) {
                    rowEl.classList.add('fade-out');
                    setTimeout(() => rowEl.remove(), 500);
                }
            }
        });

        newItems.forEach((item, index) => {
            const key = item._key;
            let rowEl = document.getElementById(`row-${key}`);
            const isNew = !currentMap.has(key);
            const prevItem = currentMap.get(key);

            if (!rowEl) {
                rowEl = document.createElement('div');
                rowEl.id = `row-${key}`;
                rowEl.className = 'row pulse-new';
                tableBody.appendChild(rowEl);
            }

            rowEl.style.transform = `translateY(${index * rowHeightVH}vh)`;

            if (isSim) {
                updateSimRow(rowEl, item, prevItem, isNew);
            } else {
                updateZoneRow(rowEl, item, prevItem, isNew);
            }
        });

        currentState = newItems;
    }

    function updateSimRow(rowEl, item, prevItem, isNew) {
        let name = item.name || 'Unknown';
        name = (name || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        const isOOC = item.isOOC || false;
        if (isOOC && item.display_name) {
            name = item.display_name;
        }

        const total = item.total || 0;
        const active = item.active || 0;
        const scriptsText = `${total} / ${active}`;

        const time = item.time || 0.0;
        const timeText = `${time.toFixed(2)} ms`;

        const mem = item.memory || 0;
        let memoryText = '';
        if (mem < 1024 * 1024) {
            memoryText = `${Math.floor(mem / 1024)} kB`;
        } else {
            memoryText = `${(mem / (1024.0 * 1024.0)).toFixed(1)} MB`;
        }

        const complexityText = String(item.complexity || 0);

        let nameClass = isOOC ? 'val-ooc' : '';

        // Determine if text values changed for flash
        const prevTotal = prevItem?.total || 0;
        const prevActive = prevItem?.active || 0;
        const prevScriptsText = prevItem ? `${prevTotal} / ${prevActive}` : null;

        const prevTime = prevItem?.time || 0.0;
        const prevTimeText = prevItem ? `${prevTime.toFixed(2)} ms` : null;

        const prevMem = prevItem?.memory || 0;
        let prevMemoryText = null;
        if (prevItem) {
             if (prevMem < 1024 * 1024) {
                prevMemoryText = `${Math.floor(prevMem / 1024)} kB`;
            } else {
                prevMemoryText = `${(prevMem / (1024.0 * 1024.0)).toFixed(1)} MB`;
            }
        }

        const prevComplexityText = prevItem ? String(prevItem.complexity || 0) : null;

        const nameHtml = `<div class="col-1 ${nameClass}">${name} ${isOOC ? '(OOC)' : ''}</div>`;
        const scriptHtml = `<div class="col-2 ${getDiffClass(scriptsText, prevScriptsText, isNew)}">${scriptsText}</div>`;
        const timeHtml = `<div class="col-3 ${getDiffClass(timeText, prevTimeText, isNew)}">${timeText}</div>`;
        const memHtml = `<div class="col-4 ${getDiffClass(memoryText, prevMemoryText, isNew)}">${memoryText}</div>`;
        const cmplxHtml = `<div class="col-5 ${getDiffClass(complexityText, prevComplexityText, isNew)}">${complexityText}</div>`;

        rowEl.innerHTML = nameHtml + scriptHtml + timeHtml + memHtml + cmplxHtml;
    }

    function updateZoneRow(rowEl, item, prevItem, isNew) {
        const rawName = item.name || 'Unknown Zone';
        const name = (rawName || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        const occupancyText = item.occupancyText || "0";
        const dynamicText = item.dynamicText || "Static";
        const liEstText = item.liEstText || "-";
        const rezStatusText = item.rezStatusText || "-";
        const isDynamic = item.isDynamic || false;

        let stateClass = '';
        if (isDynamic) {
            const statusLower = rezStatusText.toLowerCase();
            if (statusLower === 'deployed' || statusLower === 'rezzing') stateClass = 'val-good';
            else if (statusLower === 'idle' || statusLower === 'derezzing') stateClass = 'val-ooc';
        } else {
            stateClass = 'val-dim';
        }

        const prevOcc = prevItem?.occupancyText || null;
        const prevDyn = prevItem?.dynamicText || null;
        const prevLi = prevItem?.liEstText || null;
        const prevRez = prevItem?.rezStatusText || null;

        const nameHtml = `<div class="col-1">${name}</div>`;
        const occHtml = `<div class="col-2 ${getDiffClass(occupancyText, prevOcc, isNew)}">${occupancyText}</div>`;
        const dynHtml = `<div class="col-3 ${getDiffClass(dynamicText, prevDyn, isNew)}">${dynamicText}</div>`;
        const liHtml = `<div class="col-4 ${getDiffClass(liEstText, prevLi, isNew)}">${liEstText}</div>`;
        const stateHtml = `<div class="col-5 ${stateClass} ${getDiffClass(rezStatusText, prevRez, isNew)}">${rezStatusText}</div>`;

        rowEl.innerHTML = nameHtml + occHtml + dynHtml + liHtml + stateHtml;
    }

    function getDiffClass(current, prev, isNew) {
        if (isNew) return '';
        if (current !== prev) {
            // Remove the animation class and trigger reflow to restart animation
            return 'value-change';
        }
        return '';
    }

    // Start connection
    connectWebSocket();
});
