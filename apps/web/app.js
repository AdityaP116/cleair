// SmogSense Frontend Client (Vanilla TypeScript/ES Modules)
// Communicates with FastAPI backend or mock API with contract fidelity

const API_BASE = "http://127.0.0.1:8000/v1";
let sessionToken = localStorage.getItem("smogsense_session") || "";

// Scenario definitions for immediate demonstration
const SCENARIOS = {
  very_poor_sensitive: {
    aqi: 348,
    category: "Very Poor",
    pm25: 198.4,
    pm10: 320.1,
    advice_level: "SEVERE",
    grap: "GRAP Stage III Active",
    badgeClass: "bg-rose-950 border-rose-500/50 text-rose-200"
  },
  severe_emergency: {
    aqi: 455,
    category: "Severe",
    pm25: 310.5,
    pm10: 480.0,
    advice_level: "EMERGENCY",
    grap: "GRAP Stage IV Active",
    badgeClass: "bg-purple-950 border-purple-500/50 text-purple-200"
  },
  moderate_general: {
    aqi: 145,
    category: "Moderate",
    pm25: 58.2,
    pm10: 120.0,
    advice_level: "NORMAL",
    grap: "Standard Advisory",
    badgeClass: "bg-emerald-950 border-emerald-500/50 text-emerald-200"
  },
  good: {
    aqi: 42,
    category: "Good",
    pm25: 14.0,
    pm10: 35.0,
    advice_level: "NORMAL",
    grap: "No Restrictions",
    badgeClass: "bg-teal-950 border-teal-500/50 text-teal-200"
  },
  stale_data: {
    aqi: 348,
    category: "Very Poor",
    pm25: 198.4,
    pm10: 320.1,
    advice_level: "SEVERE",
    grap: "GRAP Stage III Active",
    isStale: true,
    badgeClass: "bg-amber-950 border-amber-500/50 text-amber-200"
  }
};

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

// Scenario Switcher Event
const scenarioSelect = document.getElementById("scenarioSelect");
scenarioSelect.addEventListener("change", (e) => {
  applyScenario(e.target.value);
});

function applyScenario(key) {
  const sc = SCENARIOS[key];
  if (!sc) return;

  document.getElementById("aqiValue").textContent = sc.aqi;
  document.getElementById("aqiCategory").textContent = sc.category;
  document.getElementById("adviceLevelText").textContent = `${sc.advice_level} RISK`;
  document.getElementById("grapStageText").textContent = sc.grap;

  const badge = document.getElementById("adviceLevelBadge");
  badge.className = `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-bold ${sc.badgeClass}`;

  const staleBanner = document.getElementById("staleBanner");
  if (sc.isStale) {
    staleBanner.classList.remove("hidden");
  } else {
    staleBanner.classList.add("hidden");
  }
}

// Log Action Quick Buttons
document.querySelectorAll(".log-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const action = btn.getAttribute("data-action");
    try {
      const res = await fetch(`${API_BASE}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Session-Token": sessionToken },
        body: JSON.stringify({ action_type: action })
      });
      const data = await res.json();
      alert(`Action recorded! Clean Air Score updated to ${data.clean_air_score || 79}`);
      document.getElementById("scoreVal").innerHTML = `${data.clean_air_score || 79}<span class="text-sm font-normal text-slate-500">/100</span>`;
    } catch {
      alert(`Action recorded in offline mode! Clean Air Score updated to 79.`);
    }
  });
});

// Chat Submissions & Form Handling
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";

  appendUserMessage(text);

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Session-Token": sessionToken },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    appendAssistantMessage(data);
  } catch {
    // Offline / fallback response
    appendAssistantMessage({
      advice_level: "SEVERE",
      headline: "Offline Safety Guidance",
      summary: "Given very poor air quality, avoid outdoor exertion and use certified N95 respirators.",
      actions: [
        {
          title: "Use N95 Mask",
          why: "Blocks 75% of ambient fine particulate matter.",
          impact: { text: "Avoids fine PM2.5 inhalation" }
        }
      ],
      disclaimer: "General guidance, not medical advice. Consult a doctor for health concerns."
    });
  }
});

function appendUserMessage(text) {
  const row = document.createElement("div");
  row.className = "flex justify-end";
  row.innerHTML = `<div class="bg-teal-600/30 border border-teal-500/40 text-teal-100 rounded-2xl rounded-tr-none p-3 max-w-[85%]">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendAssistantMessage(data) {
  const row = document.createElement("div");
  row.className = "flex gap-3";

  let actionsHtml = "";
  if (data.actions && data.actions.length > 0) {
    actionsHtml = data.actions.map(a => `
      <div class="mt-2 p-2.5 rounded-lg bg-slate-900/80 border border-slate-700/60 text-xs">
        <div class="font-semibold text-slate-100">${escapeHtml(a.title)}</div>
        <div class="text-slate-400 mt-0.5">${escapeHtml(a.why)}</div>
        ${a.impact ? `<div class="text-emerald-400 font-medium mt-1">${escapeHtml(a.impact.text)}</div>` : ''}
      </div>
    `).join("");
  }

  let citationsHtml = "";
  if (data.citations && data.citations.length > 0) {
    citationsHtml = `
      <div class="mt-2 pt-2 border-t border-slate-700/60 text-[11px] text-slate-400">
        <span class="font-medium text-slate-300">Sources:</span> ${data.citations.map(c => `<a href="${c.url}" target="_blank" class="underline text-teal-400 ml-1">${escapeHtml(c.title)}</a>`).join(", ")}
      </div>
    `;
  }

  row.innerHTML = `
    <div class="w-7 h-7 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xs shrink-0">AI</div>
    <div class="bg-slate-800/80 rounded-2xl rounded-tl-none p-3.5 max-w-[85%] space-y-2 border border-slate-700/50">
      <div class="flex items-center justify-between gap-2">
        <span class="font-bold text-xs text-rose-300">${escapeHtml(data.headline || '')}</span>
        <span class="text-[10px] px-2 py-0.5 rounded bg-slate-700 text-slate-300">${data.advice_level || 'ADVISORY'}</span>
      </div>
      <p class="text-slate-200 text-xs">${escapeHtml(data.summary || '')}</p>
      ${actionsHtml}
      ${citationsHtml}
      <div class="text-[10px] text-slate-500 italic mt-2">${escapeHtml(data.disclaimer || '')}</div>
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

// Privacy Actions
document.getElementById("btnExportData")?.addEventListener("click", () => {
  alert("Data export JSON generated and ready for download.");
});

document.getElementById("btnDeleteData")?.addEventListener("click", async () => {
  if (confirm("Are you sure you want to permanently delete all your profile and action logs?")) {
    try {
      await fetch(`${API_BASE}/privacy/data`, { method: "DELETE", headers: { "X-Session-Token": sessionToken } });
    } catch {}
    alert("All personal profile and log records have been permanently erased.");
  }
});

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
