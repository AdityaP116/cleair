import { api } from "/static/api.js";

const CITY_COORDS = {
  "Mumbai": [19.0760, 72.8777],
  "Thane": [19.2183, 72.9781],
  "Delhi-NCR": [28.6139, 77.2090],
  "Pune": [18.5204, 73.8567],
  "Kolkata": [22.5726, 88.3639],
  "Bengaluru": [12.9716, 77.5946],
};

function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function badgeClass(aqi) {
  if (aqi <= 100) return "badge-good";
  if (aqi <= 200) return "badge-moderate";
  if (aqi <= 300) return "badge-poor";
  return "badge-severe";
}

// Theme
const savedTheme = localStorage.getItem("cleair_theme") || "light";
document.documentElement.setAttribute("data-theme", savedTheme);
document.getElementById("btnTheme")?.addEventListener("click", () => {
  const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("cleair_theme", next);
});

// Mobile Drawer
document.getElementById("btnMobileNav")?.addEventListener("click", () => {
  document.getElementById("appSidebar")?.classList.toggle("open");
});

// Router
function route() {
  const hash = (window.location.hash || "#/").replace(/^#/, "");
  const pLanding = document.getElementById("pageLanding");
  const pOnboard = document.getElementById("pageOnboarding");
  const shell = document.getElementById("appShell");

  [pLanding, pOnboard, shell].forEach((el) => el?.classList.add("hidden"));

  if (hash === "/" || hash === "") {
    pLanding?.classList.remove("hidden");
    loadLandingPreview();
  } else if (hash.startsWith("/onboarding")) {
    pOnboard?.classList.remove("hidden");
  } else {
    shell?.classList.remove("hidden");
    document.querySelectorAll(".dash-view").forEach((v) => v.classList.add("hidden"));
    document.querySelectorAll(".nav-link").forEach((a) => {
      a.classList.toggle("active", a.getAttribute("data-route") === hash);
    });
    const map = {
      "/dashboard": "view-dashboard",
      "/dashboard/air": "view-air",
      "/dashboard/assistant": "view-assistant",
      "/dashboard/planner": "view-planner",
      "/dashboard/indoor": "view-indoor",
      "/dashboard/sustainability": "view-sustainability",
      "/dashboard/community": "view-community",
      "/dashboard/settings": "view-settings",
    };
    const target = document.getElementById(map[hash] || "view-dashboard");
    target?.classList.remove("hidden");
    document.getElementById("appSidebar")?.classList.remove("open");
    if (hash === "/dashboard" || hash === "/dashboard/air") loadDashboard();
  }
}

window.addEventListener("hashchange", route);

async function loadLandingPreview() {
  try {
    const air = await api.getAirCurrent(19.0760, 72.8777);
    document.getElementById("lpCity").textContent = air.location?.city || "Mumbai";
    const b = document.getElementById("lpAqi");
    b.className = `badge ${badgeClass(air.aqi)} num-tabular`;
    b.textContent = `AQI ${air.aqi} · ${air.category}`;
    document.getElementById("lpSource").textContent = `PM2.5: ${air.pm25} µg/m³ · Source: ${air.source}`;
    document.getElementById("lpAction").textContent =
      air.aqi > 200
        ? "Limit outdoor exertion; wear N95/FFP2 during commute."
        : "Moderate conditions; ventilate briefly during midday mixing (1–4 PM).";
  } catch (e) {
    document.getElementById("lpSource").textContent = "Live data unavailable.";
  }
}

async function loadDashboard() {
  let city = "Mumbai";
  try {
    const prof = await api.getProfile();
    city = prof.city || "Mumbai";
  } catch (_) {}
  const [lat, lon] = CITY_COORDS[city] || CITY_COORDS["Mumbai"];
  document.getElementById("topbarLocation").textContent = city;

  try {
    const air = await api.getAirCurrent(lat, lon);
    document.getElementById("dashAqiVal").textContent = air.aqi;
    const cat = document.getElementById("dashAqiCat");
    cat.className = `badge ${badgeClass(air.aqi)}`;
    cat.textContent = air.category;
    document.getElementById("dashAqiMeta").textContent = `PM2.5: ${air.pm25} µg/m³ · Source: ${air.source}`;
    document.getElementById("topbarFreshness").textContent = air.stale ? "Stale / Demo" : "Live";

    const pGrid = document.getElementById("airPollutantsGrid");
    if (pGrid && air.pollutants) {
      pGrid.innerHTML = Object.entries(air.pollutants)
        .map(([k, v]) => `<div class="card"><span style="font-size:0.75rem;color:var(--color-text-secondary);text-transform:uppercase;">${esc(k)}</span><div class="num-tabular" style="font-size:1.5rem;font-weight:700;margin-top:4px;">${esc(v)}</div></div>`)
        .join("");
    }

    const chat = await api.sendChat(`Give 3 prioritized actions for ${city} at AQI ${air.aqi}`);
    const items = [...(chat.daily_routines || []), ...(chat.indoor_hacks || []), ...(chat.sustainable_alternatives || [])].slice(0, 3);
    const gGrid = document.getElementById("dashGuidanceGrid");
    if (gGrid && items.length) {
      gGrid.innerHTML = items.map((i) => `<div class="card"><strong>${esc(i.title)}</strong><p style="font-size:0.875rem;color:var(--color-text-secondary);margin:6px 0 0;">${esc(i.detail)}</p></div>`).join("");
    }

    const fc = await api.getAirForecast(lat, lon);
    const fcEl = document.getElementById("airForecastList");
    if (fcEl && fc.points) {
      fcEl.innerHTML = fc.points.slice(0, 6).map((pt) => `<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--color-border);"><span>${esc(pt.valid_at)}</span><span class="num-tabular">AQI ${esc(pt.aqi)} (${esc(pt.aqi_category)})</span></div>`).join("");
    }
  } catch (e) {
    console.error(e);
  }
}

// Onboarding
let obStep = 1;
function updateOb() {
  document.getElementById("obStepLabel").textContent = `Step ${obStep} of 5`;
  document.querySelectorAll(".ob-step").forEach((el) => el.classList.toggle("hidden", Number(el.dataset.step) !== obStep));
  document.getElementById("obBack").classList.toggle("hidden", obStep === 1);
  document.getElementById("obNext").classList.toggle("hidden", obStep === 5);
  document.getElementById("obFinish").classList.toggle("hidden", obStep !== 5);
}
document.getElementById("obNext")?.addEventListener("click", () => { if (obStep < 5) { obStep++; updateOb(); } });
document.getElementById("obBack")?.addEventListener("click", () => { if (obStep > 1) { obStep--; updateOb(); } });
document.getElementById("onboardingForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  await api.updateProfile({
    city: document.getElementById("obCity").value,
    has_child: document.getElementById("obChild").checked,
    has_elderly: document.getElementById("obElderly").checked,
    has_respiratory_condition: document.getElementById("obResp").checked,
    commute_mode: document.getElementById("obCommute").value,
    has_purifier: document.getElementById("obPurifier").checked,
    cooking_fuel: document.getElementById("obFuel").value,
    budget_tier: document.getElementById("obBudget").value,
  });
  window.location.hash = "#/dashboard";
});

// AI Assistant
document.getElementById("assistantForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const inp = document.getElementById("assistantInput");
  const msg = inp.value.trim();
  if (!msg) return;
  const log = document.getElementById("assistantLog");
  log.innerHTML += `<div style="align-self:flex-end;background:var(--color-forest);color:#fff;padding:8px 12px;border-radius:var(--radius-sm);max-width:80%;font-size:0.875rem;">${esc(msg)}</div>`;
  inp.value = "";
  try {
    const res = await api.sendChat(msg);
    const renderSec = (title, items) =>
      items && items.length
        ? `<div style="margin-top:8px;"><strong>${esc(title)}</strong><ul style="margin:4px 0 0;padding-left:18px;">${items.map((i) => `<li><strong>${esc(i.title)}:</strong> ${esc(i.detail)}</li>`).join("")}</ul></div>`
        : "";
    log.innerHTML += `<div class="card-muted" style="max-width:85%;font-size:0.875rem;"><strong>${esc(res.headline)}</strong><p style="margin:4px 0;">${esc(res.summary)}</p>${renderSec("Daily Routines", res.daily_routines)}${renderSec("Indoor Air Hacks", res.indoor_hacks)}${renderSec("Sustainable Alternatives", res.sustainable_alternatives)}<small style="display:block;margin-top:8px;color:var(--color-text-secondary);">${esc(res.disclaimer || "")}</small></div>`;
    log.scrollTop = log.scrollHeight;
  } catch (err) {
    log.innerHTML += `<div style="color:var(--color-danger);font-size:0.875rem;">${esc(err.message)}</div>`;
  }
});

// Sustainability Calculator
document.getElementById("calcForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  const km = Number(document.getElementById("calcKm").value || 0);
  const base = Number(document.getElementById("calcBase").value || 0);
  const alt = Number(document.getElementById("calcAlt").value || 0);
  const saved = Math.max(0, (base - alt) * km).toFixed(2);
  const out = document.getElementById("calcResult");
  out.classList.remove("hidden");
  out.innerHTML = `<strong>Estimated CO2 Avoided:</strong> ${saved} kg/day (${(saved * 22).toFixed(1)} kg/month assuming 22 commute days).`;
});

// Delete Profile
document.getElementById("btnDeleteProfile")?.addEventListener("click", async () => {
  await api.deleteProfile();
  sessionStorage.removeItem("cleair_session_token");
  document.getElementById("settingsMsg").textContent = "Profile and session deleted.";
});

// ================= TOASTS, ANALYTICS, COOKIE CONSENT & SEO =================
export function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

export function trackEvent(eventName, detail = {}) {
  try {
    const prefs = JSON.parse(localStorage.getItem("cleair_cookie_prefs") || "{}");
    if (prefs.analytics === false) return;
    const events = JSON.parse(localStorage.getItem("cleair_events") || "[]");
    events.push({ event: eventName, detail, ts: new Date().toISOString() });
    localStorage.setItem("cleair_events", JSON.stringify(events.slice(-50)));
  } catch (_) {}
}

function initCookieConsent() {
  const banner = document.getElementById("cookieBanner");
  const modal = document.getElementById("cookieModal");
  if (!banner || !modal) return;
  if (!localStorage.getItem("cleair_cookie_prefs")) {
    banner.classList.remove("hidden");
  }
  const savePrefs = (analytics, personalization) => {
    localStorage.setItem("cleair_cookie_prefs", JSON.stringify({ essential: true, analytics, personalization }));
    banner.classList.add("hidden");
    modal.classList.add("hidden");
    showToast("Privacy preferences saved.");
  };
  document.getElementById("btnCookieAccept")?.addEventListener("click", () => savePrefs(true, true));
  document.getElementById("btnCookieEssential")?.addEventListener("click", () => savePrefs(false, false));
  document.getElementById("btnCookiePrefs")?.addEventListener("click", () => modal.classList.remove("hidden"));
  document.getElementById("btnCookieSave")?.addEventListener("click", () => {
    const a = document.getElementById("prefAnalytics")?.checked ?? true;
    const p = document.getElementById("prefPersonalization")?.checked ?? true;
    savePrefs(a, p);
  });
}

const ROUTE_META = {
  "#/": ["CLEAIR — Clearer Air. Smarter Living.", "CLEAIR turns environmental data into personalized decisions for your home, routine, and community."],
  "#/onboarding": ["Onboarding — CLEAIR", "Personalize your household air-quality profile in 5 quick steps."],
  "#/dashboard": ["Dashboard — CLEAIR", "Live local AQI, pollutant breakdown, and personalized daily guidance."],
  "#/dashboard/intelligence": ["Air Quality Intelligence — CLEAIR", "Hourly air-quality forecasts and pollutant trends."],
  "#/dashboard/assistant": ["AI Environmental Assistant — CLEAIR", "Ask CLEAIR AI for tailored air-quality and health guidance."],
  "#/dashboard/routines": ["Daily Routines — CLEAIR", "Low-emission daily routines and commute planning."],
  "#/dashboard/indoor": ["Indoor Air — CLEAIR", "Practical indoor air quality recommendations."],
  "#/dashboard/planner": ["Daily Planner — CLEAIR", "Plan your day around cleaner air windows."],
  "#/dashboard/impact": ["Sustainability Calculator — CLEAIR", "Measure completed actions and estimated impact."],
  "#/dashboard/community": ["Community Insights — CLEAIR", "Local community air-quality observations."],
  "#/dashboard/settings": ["Settings & Privacy — CLEAIR", "Manage your CLEAIR profile, data, and privacy."],
};

function updateRouteSEO() {
  const hash = window.location.hash || "#/";
  const [title, desc] = ROUTE_META[hash] || ROUTE_META["#/"];
  document.title = title;
  document.querySelector('meta[name="description"]')?.setAttribute("content", desc);
  document.getElementById("ogTitle")?.setAttribute("content", title);
  document.getElementById("ogDescription")?.setAttribute("content", desc);
  const url = `${window.location.origin}/${hash === "#/" ? "" : hash}`;
  document.getElementById("canonicalLink")?.setAttribute("href", url);
  document.getElementById("ogUrl")?.setAttribute("content", url);
}

window.addEventListener("hashchange", updateRouteSEO);
window.addEventListener("DOMContentLoaded", () => {
  route();
  initCookieConsent();
  updateRouteSEO();
});
