document.addEventListener('DOMContentLoaded', () => {
    // Extract region and type from URL path
    const pathParts = window.location.pathname.split('/').filter(p => p);
    // Path format: /view/{region_name}/{render_type}
    const regionName = pathParts[1] || 'Unknown';
    const renderType = pathParts[2] || 'sim';

    document.title = `The Lifestream`;

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

    headerTitle.textContent = `The Lifestream`;

    // Set up table headers based on type
    if (renderType === 'sim') {
        tableHeader.style.display = 'block';
        tableHeader.style.whiteSpace = 'pre';
        tableHeader.style.borderBottom = 'none'; // remove old css border

        // Columns: USER(30), SCRIPTS(13), TIME(10), MEMORY(9), CMPLX(7)
        // Gutters: 3 spaces between each.
        // Total chars: 30 + 3 + 13 + 3 + 10 + 3 + 9 + 3 + 7 = 81
        const headerStr = padRight("USER", 30) + "   " +
                          padRight("SCRIPTS (T/A)", 14) + "   " +
                          padRight("TIME", 9) + "   " +
                          padRight("MEMORY", 8) + "   " +
                          padRight("CMPLX", 7);
        const dividerStr = "─".repeat(89);

        tableHeader.innerHTML = `<div>${headerStr}</div><div style="color: var(--accent-cyan);">${dividerStr}</div>`;
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


    // --- Padding Helpers ---
    function padRight(str, length) {
        str = String(str);
        if (str.length >= length) return str.substring(0, length);
        return str + ' '.repeat(length - str.length);
    }

    function padLeft(str, length) {
        str = String(str);
        if (str.length >= length) return str.substring(0, length);
        return ' '.repeat(length - str.length) + str;
    }

    function escapeHtml(unsafe) {
        return (unsafe || "").toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
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
            let users = data.users || [];

            // Group users: IC, OOC, Others
            let icUsers = [];
            let oocUsers = [];
            let otherUsers = [];

            users.forEach(user => {
                const category = user.category !== undefined ? user.category : 0;

                if (category === 0) {
                    icUsers.push(user);
                } else if (category === 1) {
                    oocUsers.push(user);
                } else {
                    otherUsers.push(user);
                }
            });

            // Sort each group alphabetically
            const sortFnIC = (a, b) => {
                let nameA = (a.name || '').toLowerCase();
                let nameB = (b.name || '').toLowerCase();
                if (nameA < nameB) return -1;
                if (nameA > nameB) return 1;
                return 0;
            };

            const sortFnOOC = (a, b) => {
                let nameA = (a.display_name || a.name || '').toLowerCase();
                let nameB = (b.display_name || b.name || '').toLowerCase();
                if (nameA < nameB) return -1;
                if (nameA > nameB) return 1;
                return 0;
            };

            icUsers.sort(sortFnIC);
            oocUsers.sort(sortFnOOC);
            otherUsers.sort(sortFnIC);

            newItems = [...icUsers, ...oocUsers, ...otherUsers];
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
        const category = item.category !== undefined ? item.category : 0;

        if (category === 1 && item.display_name) {
            name = item.display_name;
        }

        let prefix = "";
        let suffix = "";
        if (category === 0) {
            prefix = "<<";
            suffix = ">>";
        } else if (category === 1) {
            prefix = "OOC:";
        }

        // Truncate name if necessary so prefix+name+suffix <= 16
        const maxNameLen = 30 - prefix.length - suffix.length;
        if (name.length > maxNameLen) {
            name = name.substring(0, maxNameLen);
        }

        const rawUserStr = prefix + name + suffix;
        const paddedUserStr = padRight(rawUserStr, 30);

        // Build display HTML with color spans inside the padded text
        let userHtml = escapeHtml(paddedUserStr);
        if (category === 0) {
            // Apply val-good color to the << and >>
            userHtml = userHtml.replace("&lt;&lt;", '<span class="val-good">&lt;&lt;</span>');
            userHtml = userHtml.replace("&gt;&gt;", '<span class="val-good">&gt;&gt;</span>');
        } else if (category === 1) {
            userHtml = userHtml.replace("OOC:", '<span class="val-ooc">OOC:</span>');
        }

        const total = item.total || 0;
        const active = item.active || 0;

        // Format scripts: 3 chars right aligned, " / ", 3 chars left aligned
        const tStr = padLeft(total, 3);
        const aStr = padRight(active, 3);
        const rawScriptsStr = `${tStr} / ${aStr}`;
        // The length of rawScriptsStr is exactly 3 + 3 + 3 = 9.
        // We want it centered in 13.
        // Left pad 2, right pad 2.
        const paddedScriptsStr = "  " + rawScriptsStr + "  ";

        const time = item.time || 0.0;
        // Right align to 9: ##.## ms
        const paddedTimeStr = padLeft(`${time.toFixed(2)} ms`, 7);

        const mem = item.memory || 0;
        // Forced MB, 1 decimal place. Right aligned to 9.
        const memMB = (mem / (1024.0 * 1024.0)).toFixed(1);
        const paddedMemStr = padLeft(`${memMB} MB`, 9);

        const complexity = item.complexity || 0;
        // Right aligned to 7.
        const paddedCmplxStr = padLeft(String(complexity), 7);

        // Determine if text values changed for flash
        const prevTotal = prevItem?.total || 0;
        const prevActive = prevItem?.active || 0;
        const prevScriptsText = prevItem ? `  ${padLeft(prevTotal, 3)} / ${padRight(prevActive, 3)}  ` : null;

        const prevTime = prevItem?.time || 0.0;
        const prevTimeText = prevItem ? padLeft(`${prevTime.toFixed(2)} ms`, 7) : null;

        const prevMem = prevItem?.memory || 0;
        const prevMemMB = prevItem ? (prevMem / (1024.0 * 1024.0)).toFixed(1) : null;
        const prevMemText = prevItem ? padLeft(`${prevMemMB} MB`, 9) : null;

        const prevComplexityText = prevItem ? padLeft(String(prevItem.complexity || 0), 7) : null;

        let timeStateClass = '';
        const timeMs = parseFloat(time);
        if (timeMs > 5.0) timeStateClass = 'val-bad';
        else if (timeMs > 1.0) timeStateClass = 'val-warn';

        let memStateClass = '';
        const memMB_num = mem / (1024.0 * 1024.0);
        if (memMB_num > 10.0) memStateClass = 'val-bad';
        else if (memMB_num > 7.0) memStateClass = 'val-warn';

        let cmplxStateClass = '';
        if (complexity > 500000) cmplxStateClass = 'val-bad';
        else if (complexity > 200000) cmplxStateClass = 'val-warn';

        const scriptDiffClass = getDiffClass(paddedScriptsStr, prevScriptsText, isNew);
        const scriptClass = scriptDiffClass;
        const scriptHtml = scriptClass ? `<span class="${scriptClass}">${escapeHtml(paddedScriptsStr)}</span>` : escapeHtml(paddedScriptsStr);

        const timeDiffClass = getDiffClass(paddedTimeStr, prevTimeText, isNew);
        const timeClass = [timeDiffClass, timeStateClass].filter(Boolean).join(' ');
        const timeHtml = timeClass ? `<span class="${timeClass}">${escapeHtml(paddedTimeStr)}</span>` : escapeHtml(paddedTimeStr);

        const memDiffClass = getDiffClass(paddedMemStr, prevMemText, isNew);
        const memClass = [memDiffClass, memStateClass].filter(Boolean).join(' ');
        const memHtml = memClass ? `<span class="${memClass}">${escapeHtml(paddedMemStr)}</span>` : escapeHtml(paddedMemStr);

        const cmplxDiffClass = getDiffClass(paddedCmplxStr, prevComplexityText, isNew);
        const cmplxClass = [cmplxDiffClass, cmplxStateClass].filter(Boolean).join(' ');
        const cmplxHtml = cmplxClass ? `<span class="${cmplxClass}">${escapeHtml(paddedCmplxStr)}</span>` : escapeHtml(paddedCmplxStr);

        // Combine with 3-space gutters.
        // USER(30) + 3 + SCRIPTS(13) + 3 + TIME(10) + 3 + MEMORY(9) + 3 + CMPLX(7)
        const rowInnerHtml = userHtml + "   " + scriptHtml + "   " + timeHtml + "   " + memHtml + "   " + cmplxHtml;

        rowEl.innerHTML = rowInnerHtml;
        rowEl.classList.add('sim-row');
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
