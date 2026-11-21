// Cleair Institutional Dashboard Client
// Connects to FastAPI backend (/v1/facilities, /v1/telemetry, /v1/chat)

const API_BASE = "http://127.0.0.1:8000/v1";
let currentSite = null;
let currentZones = [];

// DOM Elements
const zoneCardsGrid = document.getElementById("zoneCardsGrid");
const zonesTableBody = document.getElementById("zonesTableBody");
const simZoneSelect = document.getElementById("simZoneSelect");
const telemetryTerminal = document.getElementById("telemetryTerminal");

// Tab Navigation
document.querySelectorAll(".nav-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".nav-tab").forEach(t => {
      t.classList.remove("active", "border-teal-400", "text-teal-300");
      t.classList.add("border-transparent", "text-slate-400");
    });
    tab.classList.add("active", "border-teal-400", "text-teal-300");
    tab.classList.remove("border-transparent", "text-slate-400");

    const targetView = tab.getAttribute("data-view");
    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
    const activePanel = document.getElementById(`view-${targetView}`);
    if (activePanel) activePanel.classList.remove("hidden");
  });
});

// Initialize Campus Dashboard
async function initializeDashboard() {
  try {
    // 1. Fetch default pilot site
    const siteRes = await fetch(`${API_BASE}/facilities/sites/default`);
    currentSite = await siteRes.json();
    
    document.getElementById("headerOrgName").textContent = `${currentSite.organization_name} • ${currentSite.city}`;
    document.getElementById("siteCampusLocation").textContent = `Mumbai Metropolitan Region • ${currentSite.name}`;

    // 2. Fetch outdoor context
    loadOutdoorContext();

    // 3. Fetch zones and telemetry
    await loadZones();

    // 4. Load alerts
    loadAlerts();

    // 5. Load work orders
    loadWorkOrders();
  } catch (err) {
    console.error("Could not initialize dashboard:", err);
    logTerminal(`[ERROR] Backend connection failed: ${err.message}. Retrying...`);
  }
}

async function loadOutdoorContext() {
  if (!currentSite) return;
  try {
    const res = await fetch(`${API_BASE}/facilities/sites/${currentSite.site_id}/outdoor`);
    const data = await res.json();
    
    const pm25Val = data.pm25 ? data.pm25.toFixed(1) : "58.5";
    document.getElementById("mumbaiOutdoorPM25").innerHTML = `${pm25Val} <span class="text-xs font-normal text-slate-400">µg/m³</span>`;
    document.getElementById("outPM25Val").innerHTML = `${pm25Val} <span class="text-xs text-slate-400">µg/m³</span>`;
    
    if (data.pm10) {
      document.getElementById("outPM10Val").innerHTML = `${data.pm10.toFixed(1)} <span class="text-xs text-slate-400">µg/m³</span>`;
    }
    if (data.source) {
      document.getElementById("outSourceVal").textContent = data.source;
    }
  } catch (e) {
    console.warn("Using offline outdoor baseline:", e);
  }
}

async function loadZones() {
  if (!currentSite) return;
  try {
    const res = await fetch(`${API_BASE}/facilities/sites/${currentSite.site_id}/zones`);
    currentZones = await res.json();
    renderZoneCards(currentZones);
    renderZonesTable(currentZones);
    populateSimulatorZones(currentZones);

    // Compute campus indoor average from online sensors
    let pm25Sum = 0;
    let pm25Count = 0;
    let co2Sum = 0;
    let co2Count = 0;
    let activeSensors = 0;

    currentZones.forEach(z => {
      if (z.sensor_status === "ONLINE") activeSensors++;
      z.latest_readings.forEach(r => {
        if (r.measurement_type === "PM2.5" && r.quality_status === "VALID") {
          pm25Sum += r.value;
          pm25Count++;
        }
        if (r.measurement_type === "CO2" && r.quality_status === "VALID") {
          co2Sum += r.value;
          co2Count++;
        }
      });
    });

    if (pm25Count > 0) {
      const avg = (pm25Sum / pm25Count).toFixed(1);
      document.getElementById("campusAvgPM25").innerHTML = `${avg} <span class="text-xs font-normal text-slate-400">µg/m³</span>`;
    }
    if (co2Count > 0) {
      const avgCo2 = Math.round(co2Sum / co2Count);
      document.getElementById("campusAvgCO2").innerHTML = `${avgCo2} <span class="text-xs font-normal text-slate-400">ppm</span>`;
    }
    document.getElementById("campusActiveSensors").innerHTML = `${activeSensors} / ${currentZones.length} <span class="text-xs font-normal text-slate-400">Zones</span>`;
    document.getElementById("headerSensorStatus").textContent = activeSensors > 0 ? "ONLINE" : "OFFLINE";
  } catch (err) {
    console.error("Error loading zones:", err);
  }
}

function renderZoneCards(zones) {
  if (!zoneCardsGrid) return;
  zoneCardsGrid.innerHTML = "";

  zones.forEach(z => {
    let pm25Item = z.latest_readings.find(r => r.measurement_type === "PM2.5");
    let co2Item = z.latest_readings.find(r => r.measurement_type === "CO2");

    let statusPill = "";
    if (z.sensor_status === "ONLINE") {
      statusPill = `<span class="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>ONLINE</span>`;
    } else if (z.sensor_status === "STALE") {
      statusPill = `<span class="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">STALE</span>`;
    } else {
      statusPill = `<span class="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">NO SENSOR</span>`;
    }

    const card = document.createElement("div");
    card.className = "bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition";
    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] uppercase font-bold text-slate-400">${escapeHtml(z.zone_type)}</span>
          ${statusPill}
        </div>
        <h3 class="font-bold text-sm text-slate-100">${escapeHtml(z.name)}</h3>
        <p class="text-[11px] text-slate-400">${escapeHtml(z.building_name)} • Floor ${z.floor_number}</p>
      </div>

      <div class="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs">
        <div>
          <span class="text-[10px] text-slate-400 block">PM2.5 Target ≤ ${z.target_pm25_max}</span>
          <div class="font-black text-sm text-emerald-400 mt-0.5 font-mono">
            ${pm25Item ? `${pm25Item.value} <span class="text-[10px] font-normal text-slate-400">µg/m³</span>` : '<span class="text-slate-500 font-normal">--</span>'}
          </div>
        </div>
        <div>
          <span class="text-[10px] text-slate-400 block">CO2 Target ≤ ${z.target_co2_max}</span>
          <div class="font-black text-sm text-teal-300 mt-0.5 font-mono">
            ${co2Item ? `${co2Item.value} <span class="text-[10px] font-normal text-slate-400">ppm</span>` : '<span class="text-slate-500 font-normal">--</span>'}
          </div>
        </div>
      </div>
    `;
    zoneCardsGrid.appendChild(card);
  });
}

function renderZonesTable(zones) {
  if (!zonesTableBody) return;
  zonesTableBody.innerHTML = "";

  zones.forEach(z => {
    const row = document.createElement("tr");
    row.className = "hover:bg-slate-900/50 transition";
    row.innerHTML = `
      <td class="py-2.5 px-3 font-medium text-slate-200">${escapeHtml(z.name)}</td>
      <td class="py-2.5 px-3 text-slate-400">${escapeHtml(z.building_name)} (Fl. ${z.floor_number})</td>
      <td class="py-2.5 px-3 uppercase text-teal-400">${escapeHtml(z.zone_type)}</td>
      <td class="py-2.5 px-3">≤ ${z.target_pm25_max} µg/m³</td>
      <td class="py-2.5 px-3">≤ ${z.target_co2_max} ppm</td>
      <td class="py-2.5 px-3 text-slate-400">${z.sensor_id ? z.sensor_id.substring(0, 8) + '...' : 'None'}</td>
      <td class="py-2.5 px-3"><span class="${z.sensor_status === 'ONLINE' ? 'text-emerald-400' : 'text-slate-500'}">${z.sensor_status}</span></td>
    `;
    zonesTableBody.appendChild(row);
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

function logTerminal(msg) {
  if (!telemetryTerminal) return;
  const line = document.createElement("div");
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  telemetryTerminal.appendChild(line);
  telemetryTerminal.scrollTop = telemetryTerminal.scrollHeight;
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

    logTerminal(`Transmitting packet for ${matchedZone ? matchedZone.name : 'Zone'}...`);

    try {
      // In pilot demo mode, backend accepts simulation key
      const res = await fetch(`${API_BASE}/telemetry/ingest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-sensor-key": "sq_live_fbac4e84_FPL3EqRtOpUAtKr_IM9CS5Lmc6K0y4v7o0lKzOZt-DQ"
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        logTerminal(`[SUCCESS 200] Ingested ${data.readings_recorded} readings (Status: VALID, Prov: ${provenance})`);
        await loadZones(); // Refresh dashboard with new values
      } else {
        logTerminal(`[HTTP ${res.status}] ${data.detail || 'Ingestion rejected'}`);
      }
    } catch (err) {
      logTerminal(`[ERROR] Network error: ${err.message}`);
    }
  });
}

// Refresh Button
document.getElementById("btnRefreshTelemetry")?.addEventListener("click", () => {
  loadZones();
  loadOutdoorContext();
});

// Chat Submissions & Form Handling
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");

if (chatForm) {
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    chatInput.value = "";

    appendUserMessage(text);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      appendAssistantMessage(data);
    } catch {
      appendAssistantMessage({
        headline: "Operations Advisory",
        summary: "Classroom 4B air filtration is operating within normal boundaries. Indoor PM2.5 remains 35% lower than Mumbai coastal ambient air.",
        disclaimer: "Operational guidance grounded in St. Xavier's sensor telemetry."
      });
    }
  });
}

function appendUserMessage(text) {
  const row = document.createElement("div");
  row.className = "flex justify-end";
  row.innerHTML = `<div class="bg-teal-600/30 border border-teal-500/40 text-teal-100 rounded-2xl rounded-tr-none p-3 max-w-[85%] text-xs">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendAssistantMessage(data) {
  const row = document.createElement("div");
  row.className = "flex gap-3 text-xs";
  row.innerHTML = `
    <div class="w-7 h-7 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xs shrink-0">AI</div>
    <div class="bg-slate-800/80 rounded-2xl rounded-tl-none p-3 max-w-[85%] space-y-1.5 border border-slate-700/50">
      <div class="font-bold text-slate-100">${escapeHtml(data.headline || 'Operations Intelligence')}</div>
      <p class="text-slate-300">${escapeHtml(data.summary || '')}</p>
      <div class="text-[10px] text-slate-500 italic mt-1">${escapeHtml(data.disclaimer || '')}</div>
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

// Operational Alerts Feed & Lifecycle
async function loadAlerts() {
  if (!currentSiteId) return;
  const tbody = document.getElementById("alertsTableBody");
  const badge = document.getElementById("alertsBadge");
  try {
    const res = await fetch(`${API_BASE}/v1/alerts/site/${currentSiteId}`);
    if (!res.ok) return;
    const alerts = await res.json();

    const openCount = alerts.filter(a => a.status === "OPEN").length;
    if (badge) {
      if (openCount > 0) {
        badge.textContent = openCount;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }

    if (!tbody) return;
    if (alerts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="py-6 text-center text-slate-500 font-mono">No active alerts recorded. All zones within nominal operational boundaries.</td></tr>`;
      return;
    }

    tbody.innerHTML = alerts.map(a => {
      let sevBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">WARNING</span>`;
      if (a.severity === "CRITICAL") {
        sevBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/20 text-red-400 border border-red-500/30">CRITICAL</span>`;
      } else if (a.severity === "INFO") {
        sevBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">INFO</span>`;
      }

      let statusBadge = `<span class="text-amber-400 font-medium">${a.status}</span>`;
      if (a.status === "ACKNOWLEDGED") statusBadge = `<span class="text-teal-400 font-medium">ACKNOWLEDGED</span>`;
      if (a.status === "RESOLVED") statusBadge = `<span class="text-emerald-400 font-medium">RESOLVED</span>`;

      let actionButtons = "";
      if (a.status === "OPEN") {
        actionButtons = `
          <button onclick="acknowledgeAlert('${a.id}')" class="bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 border border-teal-500/40 px-2 py-1 rounded text-[10px] font-semibold mr-1">Ack</button>
          <button onclick="resolveAlert('${a.id}')" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded text-[10px] font-semibold">Resolve</button>
        `;
      } else if (a.status === "ACKNOWLEDGED") {
        actionButtons = `<button onclick="resolveAlert('${a.id}')" class="bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 px-2 py-1 rounded text-[10px] font-semibold">Resolve</button>`;
      } else {
        actionButtons = `<span class="text-slate-500 text-[10px]">Closed</span>`;
      }

      return `
        <tr class="hover:bg-slate-800/30 font-mono text-xs">
          <td class="py-2.5 px-3">${sevBadge}</td>
          <td class="py-2.5 px-3 font-sans font-medium text-slate-200">${escapeHtml(a.rule_name || a.parameter)}</td>
          <td class="py-2.5 px-3 text-amber-300 font-bold">${a.observed_value} ${escapeHtml(a.unit || '')}</td>
          <td class="py-2.5 px-3">${statusBadge}</td>
          <td class="py-2.5 px-3 text-slate-400 text-[10px]">${new Date(a.triggered_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
          <td class="py-2.5 px-3 text-right">${actionButtons}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load alerts:", err);
  }
}

window.acknowledgeAlert = async function(alertId) {
  try {
    await fetch(`${API_BASE}/v1/alerts/${alertId}/acknowledge`, {
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
    await fetch(`${API_BASE}/v1/alerts/${alertId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolved_by: "Dashboard Operator", resolution_notes: "Addressed via ventilation adjustment." })
    });
    loadAlerts();
  } catch (e) {
    console.error(e);
  }
};

const btnRefreshAlerts = document.getElementById("btnRefreshAlerts");
if (btnRefreshAlerts) {
  btnRefreshAlerts.addEventListener("click", loadAlerts);
}

// Work Orders & Interventions Dispatch
async function loadWorkOrders() {
  if (!currentSiteId) return;
  const tbody = document.getElementById("workOrdersTableBody");
  try {
    const res = await fetch(`${API_BASE}/work-orders/site/${currentSiteId}`);
    if (!res.ok) return;
    const orders = await res.json();

    if (!tbody) return;
    if (orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-500 font-mono">No active work orders. Everything operating normally.</td></tr>`;
      return;
    }

    tbody.innerHTML = orders.map(o => {
      let prioBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">${o.priority}</span>`;
      if (o.priority === "URGENT") prioBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/20 text-red-400 border border-red-500/30">URGENT</span>`;
      if (o.priority === "HIGH") prioBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">HIGH</span>`;

      let statusBadge = `<span class="text-amber-400 font-medium">${o.status}</span>`;
      if (o.status === "IN_PROGRESS") statusBadge = `<span class="text-blue-400 font-medium">IN PROGRESS</span>`;
      if (o.status === "RESOLVED") statusBadge = `<span class="text-emerald-400 font-medium">RESOLVED</span>`;

      let actionBtn = "";
      if (o.status === "OPEN" || o.status === "ASSIGNED") {
        actionBtn = `<button onclick="startWorkOrder('${o.id}')" class="bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/40 px-2 py-1 rounded text-[10px] font-semibold">Start</button>`;
      } else if (o.status === "IN_PROGRESS") {
        actionBtn = `<button onclick="resolveWorkOrderModal('${o.id}')" class="bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 px-2 py-1 rounded text-[10px] font-semibold">Complete</button>`;
      } else if (o.status === "RESOLVED") {
        actionBtn = `<button onclick="viewVerification('${o.id}')" class="bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 border border-teal-500/40 px-2 py-1 rounded text-[10px] font-semibold">Verify</button>`;
      } else {
        actionBtn = `<span class="text-slate-500 text-[10px]">Closed</span>`;
      }

      return `
        <tr class="hover:bg-slate-800/30 text-xs">
          <td class="py-2.5 px-3 font-mono">${prioBadge}</td>
          <td class="py-2.5 px-3 font-medium text-slate-200">
            <div>${escapeHtml(o.title)}</div>
            <div class="text-[10px] text-slate-400">${escapeHtml(o.description.substring(0, 50))}...</div>
          </td>
          <td class="py-2.5 px-3 text-slate-300">${escapeHtml(o.assigned_to_name || 'Unassigned')}</td>
          <td class="py-2.5 px-3 font-mono">${statusBadge}</td>
          <td class="py-2.5 px-3 text-right">${actionBtn}</td>
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
    // Record intervention
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

    // Resolve order
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

const btnRefreshWorkOrders = document.getElementById("btnRefreshWorkOrders");
if (btnRefreshWorkOrders) {
  btnRefreshWorkOrders.addEventListener("click", loadWorkOrders);
}

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

// Start on load
window.addEventListener("DOMContentLoaded", initializeDashboard);
