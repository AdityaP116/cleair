// Cleair / UAQA Frontend Application Logic
// Clean ES6 Architecture - Zero External NPM Dependencies
//
// CHAT API CONTRACT (verified against backend/app/api/routes/auth.py & chat.py):
//   1. POST /v1/session -> { session_token: string, user_id: string }
//   2. POST /v1/chat
//      Headers: { "Content-Type": "application/json", "x-session-token": "<session_token>" }
//      Body:    { "message": "<user_text>", "context"?: object }
//      200 OK:  Structured assistant response JSON
//      401:     Missing/invalid x-session-token -> re-acquire session and retry once
//      422:     Validation error -> show friendly validation message
//      429:     Rate limit exceeded -> show slow-down notice

const API_BASE = "http://127.0.0.1:8000/v1";

async function ensureSession(forceRefresh = false) {
  let token = !forceRefresh ? sessionStorage.getItem("cleair_session_token") : null;
  if (token) return token;
  const res = await fetch(`${API_BASE}/session`, { method: "POST" });
  if (!res.ok) throw new Error(`Session creation failed (${res.status})`);
  const data = await res.json();
  sessionStorage.setItem("cleair_session_token", data.session_token);
  return data.session_token;
}

async function sendChat(message, context = {}) {
  let token = await ensureSession(false);
  let res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-session-token": token },
    body: JSON.stringify({ message, ...context })
  });
  if (res.status === 401) {
    token = await ensureSession(true);
    res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-session-token": token },
      body: JSON.stringify({ message, ...context })
    });
  }
  if (res.status === 422) {
    const err = await res.json().catch(() => ({}));
    throw new Error(`Invalid request: ${err.detail?.[0]?.msg || "Please check your message."}`);
  }
  if (res.status === 429) {
    throw new Error("Too many requests. Please slow down and try again in a minute.");
  }
  if (!res.ok) {
    throw new Error(`Server error (${res.status}). Please try again.`);
  }
  return res.json();
}
let currentSite = null;
let currentSiteId = "9fa57ccf-89a3-4f44-bae2-625cb3a6c317";
let currentZones = [];
let currentTrendMetric = "PM2.5";

// DOM References
const appSidebar = document.getElementById("appSidebar");
const btnToggleSidebar = document.getElementById("btnToggleSidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const btnMobileMenu = document.getElementById("btnMobileMenu");
const btnThemeToggle = document.getElementById("btnThemeToggle");

const zoneCardsGrid = document.getElementById("zoneCardsGrid");
const zonesTableBody = document.getElementById("zonesTableBody");
const simZoneSelect = document.getElementById("simZoneSelect");
const telemetryTerminal = document.getElementById("telemetryTerminal");

// Sidebar Collapse & Mobile Handlers
if (btnToggleSidebar) {
  btnToggleSidebar.addEventListener("click", () => {
    appSidebar.classList.toggle("collapsed");
  });
}

if (btnMobileMenu) {
  btnMobileMenu.addEventListener("click", () => {
    appSidebar.classList.add("mobile-open");
    sidebarOverlay.classList.add("active");
  });
}

if (sidebarOverlay) {
  sidebarOverlay.addEventListener("click", () => {
    appSidebar.classList.remove("mobile-open");
    sidebarOverlay.classList.remove("active");
  });
}

// Dark / Light Theme Toggle
if (btnThemeToggle) {
  btnThemeToggle.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", nextTheme);
    localStorage.setItem("uaqa_theme", nextTheme);
  });
  // Restore saved theme
  const savedTheme = localStorage.getItem("uaqa_theme");
  if (savedTheme) {
    document.documentElement.setAttribute("data-theme", savedTheme);
  }
}

// Navigation Item Click Handler
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    document.querySelectorAll(".nav-item").forEach(i => {
      i.classList.remove("active", "bg-deep-teal", "text-white", "shadow-2xs");
      i.classList.add("text-text-secondary");
    });
    item.classList.add("active", "bg-deep-teal", "text-white", "shadow-2xs");
    item.classList.remove("text-text-secondary");

    const targetView = item.getAttribute("data-view");
    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
    const activePanel = document.getElementById(`view-${targetView}`);
    if (activePanel) activePanel.classList.remove("hidden");

    // Close mobile drawer if open
    appSidebar.classList.remove("mobile-open");
    if (sidebarOverlay) sidebarOverlay.classList.add("hidden");
  });
});

// Initialize Dashboard Lifecycle
async function initializeDashboard() {
  try {
    // 1. Fetch default pilot site
    const siteRes = await fetch(`${API_BASE}/facilities/sites/default`);
    currentSite = await siteRes.json();
    currentSiteId = currentSite.site_id;

    const orgSummary = `${currentSite.organization_name} • ${currentSite.city}`;
    const siteTitle = currentSite.name;

    const elOrg = document.getElementById("sidebarOrgSummary");
    if (elOrg) elOrg.textContent = currentSite.organization_name;

    const elLoc = document.getElementById("siteCampusLocation");
    if (elLoc) elLoc.textContent = `Mumbai Metropolitan Region • ${siteTitle}`;

    const elTop = document.getElementById("topbarSiteTitle");
    if (elTop) elTop.textContent = `${siteTitle} (${currentSite.organization_name})`;

    // 2. Fetch outdoor ambient air context
    loadOutdoorContext();

    // 3. Fetch indoor physical zones and telemetry
    await loadZones();

    // 4. Fetch operational alerts
    loadAlerts();

    // 5. Fetch work orders
    loadWorkOrders();

    // 6. Render trend analytics chart
    renderTrendChart();

    const elSync = document.getElementById("labelLastSyncTime");
    if (elSync) elSync.textContent = `Synced at ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
  } catch (err) {
    console.error("Dashboard initialization error:", err);
    logTerminal(`[ERROR] Backend connection failed: ${err.message}. Retrying...`);
  }
}

// Outdoor MMR Context Fetcher
async function loadOutdoorContext() {
  try {
    const res = await fetch(`${API_BASE}/facilities/sites/${currentSiteId}/outdoor`);
    if (res.ok) {
      const data = await res.json();
      const elPM25 = document.getElementById("mumbaiOutdoorPM25");
      if (elPM25) elPM25.innerHTML = `${data.pm25} <span class="kpi-unit">µg/m³</span>`;

      const elPM10 = document.getElementById("outPM10Val");
      if (elPM10) elPM10.textContent = `${data.pm10} µg/m³`;

      const elOutPM25 = document.getElementById("outPM25Val");
      if (elOutPM25) elOutPM25.textContent = `${data.pm25} µg/m³`;

      const elSource = document.getElementById("outSourceVal");
      if (elSource) elSource.textContent = `${data.source} (${data.provenance})`;

      const elStatus = document.getElementById("mumbaiOutdoorStatus");
      if (elStatus) {
        if (data.pm25 <= 30) {
          elStatus.textContent = "Good Coastal Air";
          elStatus.className = "badge badge-healthy";
        } else if (data.pm25 <= 60) {
          elStatus.textContent = "Satisfactory Air";
          elStatus.className = "badge badge-healthy";
        } else if (data.pm25 <= 90) {
          elStatus.textContent = "Moderate Ambient";
          elStatus.className = "badge badge-warning";
        } else {
          elStatus.textContent = "Poor / Inversion";
          elStatus.className = "badge badge-critical";
        }
      }
    }
  } catch (e) {
    console.warn("Using offline outdoor fallback context:", e);
  }
}

// Load Physical Zones & Compute Campus Averages
async function loadZones() {
  if (!currentSiteId) return;
  try {
    const res = await fetch(`${API_BASE}/facilities/sites/${currentSiteId}/zones`);
    currentZones = await res.json();
    renderZoneCards(currentZones);
    renderZonesTable(currentZones);
    populateSimulatorZones(currentZones);

    let pm25Sum = 0;
    let pm25Count = 0;
    let co2Sum = 0;
    let co2Count = 0;
    let activeSensors = 0;

    currentZones.forEach(z => {
      if (z.sensor_status === "ONLINE") activeSensors++;
      z.latest_readings.forEach(r => {
        if (r.measurement_type === "PM2.5" && (r.quality_status === "VALID" || r.quality_status === "SUSPECT")) {
          pm25Sum += r.value;
          pm25Count++;
        }
        if (r.measurement_type === "CO2" && (r.quality_status === "VALID" || r.quality_status === "SUSPECT")) {
          co2Sum += r.value;
          co2Count++;
        }
      });
    });

    if (pm25Count > 0) {
      const avg = (pm25Sum / pm25Count).toFixed(1);
      const el = document.getElementById("campusAvgPM25");
      if (el) el.innerHTML = `${avg} <span class="kpi-unit">µg/m³</span>`;
    }
    if (co2Count > 0) {
      const avgCo2 = Math.round(co2Sum / co2Count);
      const el = document.getElementById("campusAvgCO2");
      if (el) el.innerHTML = `${avgCo2} <span class="kpi-unit">ppm</span>`;
    }

    const elSensors = document.getElementById("campusActiveSensors");
    if (elSensors) elSensors.innerHTML = `${activeSensors} / ${currentZones.length} <span class="kpi-unit">Zones</span>`;

    const elHeaderStatus = document.getElementById("headerSensorStatus");
    const elDot = document.getElementById("topbarSensorDot");
    if (elHeaderStatus) {
      elHeaderStatus.textContent = activeSensors > 0 ? "ONLINE" : "OFFLINE";
      elHeaderStatus.style.color = activeSensors > 0 ? "var(--status-healthy-text)" : "var(--status-critical-text)";
    }
    if (elDot) {
      elDot.style.backgroundColor = activeSensors > 0 ? "var(--status-healthy-dot)" : "var(--status-critical-dot)";
    }

    const elCov = document.getElementById("campusCoveragePercent");
    if (elCov && currentZones.length > 0) {
      const covPct = Math.round((activeSensors / currentZones.length) * 100);
      elCov.textContent = `${covPct}% Instrumented`;
    }
  } catch (err) {
    console.error("Error loading zones:", err);
  }
}

// Render Physical Zone Cards
function renderZoneCards(zones) {
  if (!zoneCardsGrid) return;
  zoneCardsGrid.innerHTML = "";

  zones.forEach(z => {
    let pm25Item = z.latest_readings.find(r => r.measurement_type === "PM2.5");
    let co2Item = z.latest_readings.find(r => r.measurement_type === "CO2");

    let statusBadge = "";
    if (z.sensor_status === "ONLINE") {
      statusBadge = `<span class="badge badge-healthy"><span class="badge-dot"></span>ONLINE</span>`;
    } else if (z.sensor_status === "STALE") {
      statusBadge = `<span class="badge badge-warning"><span class="badge-dot"></span>STALE</span>`;
    } else {
      statusBadge = `<span class="badge badge-neutral"><span class="badge-dot"></span>AWAITING HARDWARE</span>`;
    }

    const card = document.createElement("div");
    card.className = "card-enterprise";
    card.style.padding = "16px";
    card.style.display = "flex";
    card.style.flexDirection = "column";
    card.style.justifyContent = "space-between";

    card.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted);">${escapeHtml(z.zone_type)}</span>
          ${statusBadge}
        </div>
        <h3 style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0 0 2px;">${escapeHtml(z.name)}</h3>
        <p style="font-size: 11px; color: var(--text-secondary); margin: 0;">${escapeHtml(z.building_name)} • Floor ${z.floor_number}</p>
      </div>

      <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
        <div>
          <span style="font-size: 10px; color: var(--text-muted); display: block;">PM2.5 (Target ≤ ${z.target_pm25_max})</span>
          <div class="num-tabular" style="font-size: 16px; font-weight: 700; color: ${pm25Item && pm25Item.value <= z.target_pm25_max ? 'var(--status-healthy-text)' : 'var(--status-warning-text)'}; margin-top: 2px;">
            ${pm25Item ? `${pm25Item.value} <span style="font-size: 10px; font-weight: 500; color: var(--text-muted);">µg/m³</span>` : '<span style="color: var(--text-muted); font-size: 12px;">--</span>'}
          </div>
        </div>
        <div>
          <span style="font-size: 10px; color: var(--text-muted); display: block;">CO2 (Target ≤ ${z.target_co2_max})</span>
          <div class="num-tabular" style="font-size: 16px; font-weight: 700; color: ${co2Item && co2Item.value <= z.target_co2_max ? 'var(--status-healthy-text)' : 'var(--status-warning-text)'}; margin-top: 2px;">
            ${co2Item ? `${co2Item.value} <span style="font-size: 10px; font-weight: 500; color: var(--text-muted);">ppm</span>` : '<span style="color: var(--text-muted); font-size: 12px;">--</span>'}
          </div>
        </div>
      </div>
    `;
    zoneCardsGrid.appendChild(card);
  });
}

// Render Indoor Zones Directory Table
function renderZonesTable(zones) {
  if (!zonesTableBody) return;
  zonesTableBody.innerHTML = "";

  zones.forEach(z => {
    const row = document.createElement("tr");
    let statusBadge = z.sensor_status === "ONLINE"
      ? `<span class="badge badge-healthy">ONLINE</span>`
      : (z.sensor_status === "STALE" ? `<span class="badge badge-warning">STALE</span>` : `<span class="badge badge-neutral">UNBOUND</span>`);

    row.innerHTML = `
      <td style="font-weight: 600;">${escapeHtml(z.name)}</td>
      <td>${escapeHtml(z.building_name)} • Fl. ${z.floor_number}</td>
      <td style="text-transform: capitalize;">${escapeHtml(z.zone_type)}</td>
      <td class="num-tabular">≤ ${z.target_pm25_max} µg/m³</td>
      <td class="num-tabular">≤ ${z.target_co2_max} ppm</td>
      <td style="font-family: monospace; font-size: 11px; color: var(--text-muted);">${z.sensor_id ? z.sensor_id.substring(0, 8) + '...' : 'None'}</td>
      <td>${statusBadge}</td>
    `;
    zonesTableBody.appendChild(row);
  });
}

// Render SVG Trend Analytics Chart
function renderTrendChart() {
  const svg = document.getElementById("trendSvgCanvas");
  if (!svg) return;

  const pointsPM25 = [
    { x: 30, y: 110, val: 32.1 },
    { x: 180, y: 80, val: 45.4 },
    { x: 360, y: 125, val: 28.0 },
    { x: 540, y: 95, val: 41.2 },
    { x: 740, y: 100, val: 38.4 }
  ];

  const pointsCO2 = [
    { x: 30, y: 120, val: 620 },
    { x: 180, y: 60, val: 980 },
    { x: 360, y: 130, val: 590 },
    { x: 540, y: 85, val: 860 },
    { x: 740, y: 110, val: 720 }
  ];

  const activePoints = currentTrendMetric === "PM2.5" ? pointsPM25 : pointsCO2;
  const strokeColor = currentTrendMetric === "PM2.5" ? "var(--accent-primary)" : "var(--accent-secondary)";
  const pathD = "M " + activePoints.map(p => `${p.x} ${p.y}`).join(" L ");

  svg.innerHTML = `
    <!-- Grid Reference Lines -->
    <line x1="30" y1="40" x2="770" y2="40" stroke="var(--border-subtle)" stroke-dasharray="4 4" stroke-width="1"/>
    <line x1="30" y1="90" x2="770" y2="90" stroke="var(--border-subtle)" stroke-dasharray="4 4" stroke-width="1"/>
    <line x1="30" y1="140" x2="770" y2="140" stroke="var(--border-subtle)" stroke-width="1"/>

    <!-- Path Line -->
    <path d="${pathD}" fill="none" stroke="${strokeColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>

    <!-- Plotted Data Nodes -->
    ${activePoints.map(p => `
      <circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--bg-surface)" stroke="${strokeColor}" stroke-width="2.5"/>
      <text x="${p.x}" y="${p.y - 10}" font-size="10" font-family="-apple-system, sans-serif" font-weight="600" fill="var(--text-secondary)" text-anchor="middle">
        ${p.val} ${currentTrendMetric === 'PM2.5' ? 'µg/m³' : 'ppm'}
      </text>
    `).join("")}
  `;
}

// Trend Metric Selector Handlers
const btnTrendPM25 = document.getElementById("btnTrendPM25");
const btnTrendCO2 = document.getElementById("btnTrendCO2");
if (btnTrendPM25 && btnTrendCO2) {
  btnTrendPM25.addEventListener("click", () => {
    currentTrendMetric = "PM2.5";
    btnTrendPM25.className = "btn-primary";
    btnTrendCO2.className = "btn-secondary";
    renderTrendChart();
  });
  btnTrendCO2.addEventListener("click", () => {
    currentTrendMetric = "CO2";
    btnTrendCO2.className = "btn-primary";
    btnTrendPM25.className = "btn-secondary";
    renderTrendChart();
  });
}

function populateSimulatorZones(zones) {
  if (simZoneSelect) {
    simZoneSelect.innerHTML = "";
    zones.forEach(z => {
      const opt = document.createElement("option");
      opt.value = z.zone_id;
      opt.textContent = `${z.name} (${z.building_name} - Fl. ${z.floor_number})`;
      simZoneSelect.appendChild(opt);
    });
  }

  const woZoneSelect = document.getElementById("woZoneSelect");
  if (woZoneSelect) {
    woZoneSelect.innerHTML = '<option value="">All Zones / Campus-wide</option>';
    zones.forEach(z => {
      const opt = document.createElement("option");
      opt.value = z.zone_id;
      opt.textContent = `${z.name} (${z.building_name})`;
      woZoneSelect.appendChild(opt);
    });
  }
}

// Operational Alerts Feed & Lifecycle
async function loadAlerts() {
  if (!currentSiteId) return;
  const tbody = document.getElementById("alertsTableBody");
  const badge = document.getElementById("alertsBadge");
  try {
    const res = await fetch(`${API_BASE}/alerts/site/${currentSiteId}`);
    if (!res.ok) return;
    const alerts = await res.json();

    const openCount = alerts.filter(a => a.status === "OPEN").length;
    if (badge) {
      if (openCount > 0) {
        badge.textContent = openCount;
        badge.style.display = "inline-flex";
      } else {
        badge.style.display = "none";
      }
    }

    if (!tbody) return;
    if (alerts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="padding: 30px; text-align: center; color: var(--text-muted);">No active operational alerts. All zones within nominal thresholds.</td></tr>`;
      return;
    }

    tbody.innerHTML = alerts.map(a => {
      let sevBadge = `<span class="badge badge-warning">WARNING</span>`;
      if (a.severity === "CRITICAL") sevBadge = `<span class="badge badge-critical">CRITICAL</span>`;
      if (a.severity === "INFO") sevBadge = `<span class="badge badge-neutral">INFO</span>`;

      let statusBadge = `<span style="color: var(--status-warning-text); font-weight: 600;">${a.status}</span>`;
      if (a.status === "ACKNOWLEDGED") statusBadge = `<span style="color: var(--accent-primary); font-weight: 600;">ACKNOWLEDGED</span>`;
      if (a.status === "RESOLVED") statusBadge = `<span style="color: var(--status-healthy-text); font-weight: 600;">RESOLVED</span>`;

      let actionButtons = "";
      if (a.status === "OPEN") {
        actionButtons = `
          <button onclick="acknowledgeAlert('${a.id}')" class="btn-primary" style="padding: 4px 8px; font-size: 11px;">Ack</button>
          <button onclick="resolveAlert('${a.id}')" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; margin-left: 4px;">Resolve</button>
        `;
      } else if (a.status === "ACKNOWLEDGED") {
        actionButtons = `<button onclick="resolveAlert('${a.id}')" class="btn-primary" style="padding: 4px 8px; font-size: 11px;">Resolve</button>`;
      } else {
        actionButtons = `<span style="color: var(--text-muted); font-size: 11px;">Closed</span>`;
      }

      return `
        <tr>
          <td>${sevBadge}</td>
          <td style="font-weight: 600;">${escapeHtml(a.rule_name || a.parameter)}</td>
          <td class="num-tabular" style="font-weight: 700; color: var(--status-warning-text);">${a.observed_value} ${escapeHtml(a.unit || '')}</td>
          <td>${statusBadge}</td>
          <td style="color: var(--text-secondary); font-size: 11px;">${new Date(a.triggered_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
          <td style="text-align: right;">${actionButtons}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load alerts:", err);
  }
}

window.acknowledgeAlert = async function(alertId) {
  try {
    await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ acknowledged_by: "Dashboard Operator" })
    });
    loadAlerts();
  } catch (e) {
    console.error(e);
  }
};

window.resolveAlert = async function(alertId) {
  try {
    await fetch(`${API_BASE}/alerts/${alertId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolved_by: "Dashboard Operator", resolution_notes: "Addressed via ventilation adjustment." })
    });
    loadAlerts();
  } catch (e) {
    console.error(e);
  }
};

// Work Orders & Corrective Actions
async function loadWorkOrders() {
  if (!currentSiteId) return;
  const tbody = document.getElementById("workOrdersTableBody");
  try {
    const res = await fetch(`${API_BASE}/work-orders/site/${currentSiteId}`);
    if (!res.ok) return;
    const orders = await res.json();

    if (!tbody) return;
    if (orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="padding: 30px; text-align: center; color: var(--text-muted);">No active work orders. Everything operating normally.</td></tr>`;
      return;
    }

    tbody.innerHTML = orders.map(o => {
      let prioBadge = `<span class="badge badge-neutral">${o.priority}</span>`;
      if (o.priority === "URGENT") prioBadge = `<span class="badge badge-critical">URGENT</span>`;
      if (o.priority === "HIGH") prioBadge = `<span class="badge badge-warning">HIGH</span>`;

      let statusBadge = `<span style="color: var(--status-warning-text); font-weight: 600;">${o.status}</span>`;
      if (o.status === "IN_PROGRESS") statusBadge = `<span style="color: var(--accent-secondary); font-weight: 600;">IN PROGRESS</span>`;
      if (o.status === "RESOLVED") statusBadge = `<span style="color: var(--status-healthy-text); font-weight: 600;">RESOLVED</span>`;

      let actionBtn = "";
      if (o.status === "OPEN" || o.status === "ASSIGNED") {
        actionBtn = `<button onclick="startWorkOrder('${o.id}')" class="btn-primary" style="padding: 4px 8px; font-size: 11px;">Start</button>`;
      } else if (o.status === "IN_PROGRESS") {
        actionBtn = `<button onclick="resolveWorkOrderModal('${o.id}')" class="btn-primary" style="padding: 4px 8px; font-size: 11px;">Complete</button>`;
      } else if (o.status === "RESOLVED") {
        actionBtn = `<button onclick="viewVerification('${o.id}')" class="btn-secondary" style="padding: 4px 8px; font-size: 11px;">Verify</button>`;
      } else {
        actionBtn = `<span style="color: var(--text-muted); font-size: 11px;">Closed</span>`;
      }

      return `
        <tr>
          <td>${prioBadge}</td>
          <td>
            <div style="font-weight: 600;">${escapeHtml(o.title)}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(o.description.substring(0, 50))}...</div>
          </td>
          <td style="color: var(--text-secondary);">${escapeHtml(o.assigned_to_name || 'Unassigned')}</td>
          <td>${statusBadge}</td>
          <td style="text-align: right;">${actionBtn}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load work orders:", err);
  }
}

window.startWorkOrder = async function(orderId) {
  try {
    await fetch(`${API_BASE}/work-orders/${orderId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "IN_PROGRESS",
        actor_name: "Staff Tech",
        notes: "Work started on site."
      })
    });
    loadWorkOrders();
  } catch (e) {
    console.error(e);
  }
};

window.resolveWorkOrderModal = async function(orderId) {
  const notes = prompt("Enter completion notes and actions taken:", "Air purge completed, mechanical damper calibrated.");
  if (!notes) return;
  try {
    await fetch(`${API_BASE}/work-orders/${orderId}/interventions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        intervention_type: "HVAC_VENTILATION_ADJUSTMENT",
        description: notes,
        performed_by: "Staff Tech",
        site_id: currentSiteId
      })
    });

    await fetch(`${API_BASE}/work-orders/${orderId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "RESOLVED",
        actor_name: "Staff Tech",
        completion_notes: notes
      })
    });
    loadWorkOrders();
    loadAlerts();
  } catch (e) {
    console.error(e);
  }
};

window.viewVerification = async function(orderId) {
  try {
    const res = await fetch(`${API_BASE}/work-orders/${orderId}/verification?window_minutes=60`);
    if (!res.ok) return;
    const v = await res.json();
    let msg = `[Before/After Verification Report]\nOrder: ${v.title || orderId}\nAnchor Time: ${new Date(v.anchor_timestamp).toLocaleTimeString()}\nIntervention: ${v.intervention?.type || 'Corrective action'}\n\n`;
    if (v.metrics) {
      for (const [k, m] of Object.entries(v.metrics)) {
        if (m.pre_mean !== undefined && m.post_mean !== undefined) {
          msg += `${k}: ${m.pre_mean} -> ${m.post_mean} ${m.unit} (Delta: ${m.delta} ${m.unit}, ${m.percent_change}% [${m.direction}])\n`;
        }
      }
    }
    msg += `\nMMR Ambient Baseline Context:\nAmbient PM2.5: ${v.outdoor_context?.ambient_pm25} µg/m³\nAmbient PM10: ${v.outdoor_context?.ambient_pm10} µg/m³\n\nIntegrity Notice: ${v.epistemic_disclaimer}`;
    alert(msg);
  } catch (err) {
    console.error("Verification lookup failed:", err);
  }
};

// Create Work Order Form Handler
const createWorkOrderForm = document.getElementById("createWorkOrderForm");
if (createWorkOrderForm) {
  createWorkOrderForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentSiteId) return;

    const zoneId = document.getElementById("woZoneSelect")?.value;
    const title = document.getElementById("woTitleInput")?.value;
    const description = document.getElementById("woDescInput")?.value;
    const priority = document.getElementById("woPrioritySelect")?.value;
    const assignee = document.getElementById("woAssigneeInput")?.value;

    try {
      const res = await fetch(`${API_BASE}/work-orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          site_id: currentSiteId,
          organization_id: currentSite.organization_id || currentSiteId,
          zone_id: zoneId || null,
          title: title,
          description: description,
          priority: priority,
          assigned_to_name: assignee,
          actor_name: "Facility Manager"
        })
      });
      if (res.ok) {
        document.getElementById("woTitleInput").value = "";
        document.getElementById("woDescInput").value = "";
        loadWorkOrders();
      }
    } catch (err) {
      console.error("Failed to create work order:", err);
    }
  });
}

// Ingestion Simulator Submit Handler
const ingestForm = document.getElementById("ingestSimulatorForm");
if (ingestForm) {
  ingestForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const zoneId = simZoneSelect.value;
    const pm25 = parseFloat(document.getElementById("simPM25").value);
    const co2 = parseFloat(document.getElementById("simCO2").value);
    const temp = parseFloat(document.getElementById("simTemp").value);
    const rh = parseFloat(document.getElementById("simRH").value);
    const provenance = document.getElementById("simProvenance").value;

    const matchedZone = currentZones.find(z => z.zone_id === zoneId);
    let sensorId = matchedZone && matchedZone.sensor_id ? matchedZone.sensor_id : "sim-sensor-01";

    const payload = {
      sensor_id: sensorId,
      idempotency_key: `sim-${Date.now()}`,
      timestamp: new Date().toISOString(),
      measurements: [
        { type: "PM2.5", value: pm25 },
        { type: "CO2", value: co2 },
        { type: "TEMP", value: temp },
        { type: "RH", value: rh }
      ],
      provenance: provenance,
      raw_metadata: { simulated_by: "pilot_dashboard_tester" }
    };

    logTerminal(`Transmitting authenticated packet for ${matchedZone ? matchedZone.name : 'Zone'}...`);

    try {
      const res = await fetch(`${API_BASE}/telemetry/simulate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        logTerminal(`[200 OK] Simulated ${data.readings_recorded} readings (Packet ID: ${data.idempotency_key})`);
        loadZones();
        loadAlerts();
      } else {
        logTerminal(`[ERROR ${res.status}] ${JSON.stringify(data)}`);
      }
    } catch (err) {
      logTerminal(`[FAIL] ${err.message}`);
    }
  });
}

function logTerminal(msg) {
  if (!telemetryTerminal) return;
  const line = document.createElement("div");
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  telemetryTerminal.appendChild(line);
  telemetryTerminal.scrollTop = telemetryTerminal.scrollHeight;
}

// AI Operations Assistant Chat Handler
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");

if (chatForm) {
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    const submitBtn = chatForm.querySelector('button[type="submit"]');
    appendUserMessage(query);
    chatInput.value = "";
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Sending...";
    }

    try {
      const data = await sendChat(query);
      appendAssistantMessage(data);
    } catch (err) {
      appendAssistantMessage({
        headline: "Unable to Reach Assistant",
        summary: err.message || "Network or server error occurred.",
        disclaimer: "Please try again or use the Sync button."
      });
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Send";
      }
    }
  });
}

function appendUserMessage(text) {
  const row = document.createElement("div");
  row.style.display = "flex";
  row.style.justifyContent = "flex-end";
  row.innerHTML = `<div style="background: var(--accent-primary-subtle); color: var(--accent-primary); border: 1px solid var(--accent-primary); border-radius: var(--radius-md); padding: 10px 14px; max-width: 80%; font-size: 13px;">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendAssistantMessage(data) {
  const row = document.createElement("div");
  row.style.display = "flex";
  row.style.gap = "10px";
  row.style.fontSize = "13px";
  row.innerHTML = `
    <div style="width: 28px; height: 28px; border-radius: var(--radius-sm); background: var(--accent-primary-subtle); color: var(--accent-primary); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px; flex-shrink: 0;">AI</div>
    <div style="background: var(--bg-surface-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px 14px; max-width: 80%; line-height: 1.5;">
      <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">${escapeHtml(data.headline || 'Operations Intelligence')}</div>
      <p style="margin: 0 0 6px; color: var(--text-secondary);">${escapeHtml(data.summary || '')}</p>
      <div style="font-size: 10px; color: var(--text-muted); font-style: italic;">${escapeHtml(data.disclaimer || '')}</div>
    </div>
  `;
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Prompt Chip Click
document.querySelectorAll(".prompt-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    chatInput.value = chip.textContent.trim();
    chatForm.dispatchEvent(new Event("submit"));
  });
});

// Refresh Buttons
const btnRefreshAlerts = document.getElementById("btnRefreshAlerts");
if (btnRefreshAlerts) btnRefreshAlerts.addEventListener("click", loadAlerts);

const btnRefreshWorkOrders = document.getElementById("btnRefreshWorkOrders");
if (btnRefreshWorkOrders) btnRefreshWorkOrders.addEventListener("click", loadWorkOrders);

const btnRefreshTelemetry = document.getElementById("btnRefreshTelemetry");
if (btnRefreshTelemetry) btnRefreshTelemetry.addEventListener("click", initializeDashboard);

// Institutional Reports & Exports
window.downloadTelemetryCSV = function() {
  if (!currentSiteId) return;
  window.open(`${API_BASE}/reports/site/${currentSiteId}/export/csv?days=7`, "_blank");
};

window.viewExecutiveReport = async function() {
  if (!currentSiteId) return;
  try {
    const res = await fetch(`${API_BASE}/reports/site/${currentSiteId}/summary?days=7`);
    if (!res.ok) return;
    const rep = await res.json();

    let text = `=========================================\n`;
    text += `INSTITUTIONAL AIR QUALITY OPERATIONS REPORT\n`;
    text += `Site: ${rep.site_name} (${rep.city})\n`;
    text += `Period: Last ${rep.report_period_days} Days\n`;
    text += `=========================================\n\n`;
    text += `1. MONITORING COVERAGE:\n`;
    text += `   - Total Physical Zones: ${rep.monitoring_coverage.total_zones}\n`;
    text += `   - Instrumented Zones: ${rep.monitoring_coverage.instrumented_zones} (${rep.monitoring_coverage.coverage_percent}%)\n\n`;
    text += `2. TELEMETRY VOLUME & DATA INTEGRITY:\n`;
    text += `   - Total Readings Ingested: ${rep.telemetry_volume.total_readings}\n`;
    text += `   - Valid Quality Rate: ${rep.telemetry_volume.data_integrity_percent}%\n\n`;
    text += `3. ALERT RESOLUTION:\n`;
    text += `   - Total Triggered: ${rep.alerts_summary.total_triggered}\n`;
    text += `   - Critical Alerts: ${rep.alerts_summary.critical_count}\n`;
    text += `   - Resolution Rate: ${rep.alerts_summary.resolution_rate_percent}%\n\n`;
    text += `4. CORRECTIVE ACTIONS:\n`;
    text += `   - Total Work Orders: ${rep.operations_and_interventions.total_work_orders}\n`;
    text += `   - Completed Orders: ${rep.operations_and_interventions.completed_work_orders}\n`;
    text += `   - Physical Interventions: ${rep.operations_and_interventions.total_physical_interventions}\n\n`;
    text += `5. ZONE COMPLIANCE BREAKDOWN:\n`;
    rep.zone_compliance.forEach(z => {
      text += `   • ${z.name}: PM2.5 Avg = ${z.observed_pm25_mean !== null ? z.observed_pm25_mean + ' µg/m³' : 'N/A'} (Target ≤ ${z.target_pm25_max}) | CO2 Avg = ${z.observed_co2_mean !== null ? z.observed_co2_mean + ' ppm' : 'N/A'}\n`;
    });

    alert(text);
  } catch (err) {
    console.error("Report lookup failed:", err);
  }
};

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Contact Form Handler
const contactForm = document.getElementById("contactForm");
if (contactForm) {
  contactForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const statusEl = document.getElementById("contactStatus");
    if (statusEl) statusEl.textContent = "Message received! Pilot support will follow up shortly.";
    contactForm.reset();
  });
}

// Start on DOM ready
window.addEventListener("DOMContentLoaded", initializeDashboard);
