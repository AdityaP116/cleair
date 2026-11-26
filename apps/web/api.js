// CLEAIR 2.0 Centralized API Service
const isLocalHost = ["127.0.0.1", "localhost"].includes(window.location.hostname);
const API_BASE = window.CLEAIR_API_BASE || (isLocalHost ? "http://127.0.0.1:8000/v1" : "/v1");

export const api = {
  async ensureSession(force = false) {
    let token = !force ? sessionStorage.getItem("cleair_session_token") : null;
    if (token) return token;
    try {
      const res = await fetch(`${API_BASE}/session`, { method: "POST" });
      const ct = res.headers.get("content-type") || "";
      if (!res.ok || !ct.includes("application/json")) throw new Error(`Session error (${res.status})`);
      const data = await res.json();
      sessionStorage.setItem("cleair_session_token", data.session_token);
      return data.session_token;
    } catch (_) {
      const fallback = "cleair-static-session";
      sessionStorage.setItem("cleair_session_token", fallback);
      return fallback;
    }
  },

  async request(path, options = {}) {
    let token = await this.ensureSession(false);
    if (token === "cleair-static-session") {
      return this._staticFallback(path, options);
    }
    const headers = { "Content-Type": "application/json", "x-session-token": token, ...(options.headers || {}) };
    try {
      let res = await fetch(`${API_BASE}${path}`, { ...options, headers });
      if (res.status === 401) {
        token = await this.ensureSession(true);
        if (token === "cleair-static-session") return this._staticFallback(path, options);
        headers["x-session-token"] = token;
        res = await fetch(`${API_BASE}${path}`, { ...options, headers });
      }
      const ct = res.headers.get("content-type") || "";
      if (!res.ok || !ct.includes("application/json")) {
        if (res.status === 404 || res.status === 405 || !ct.includes("application/json")) {
          return this._staticFallback(path, options);
        }
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Request failed (${res.status})`);
      }
      return res.json();
    } catch (e) {
      if (e.name === "TypeError") return this._staticFallback(path, options);
      throw e;
    }
  },

  _staticFallback(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    if (path.startsWith("/profile")) {
      const saved = JSON.parse(localStorage.getItem("cleair_local_profile") || '{"city":"Mumbai","sensitivity":"standard","commute":"public_transit"}');
      if (method === "PATCH") {
        const updates = JSON.parse(options.body || "{}");
        const next = { ...saved, ...updates };
        localStorage.setItem("cleair_local_profile", JSON.stringify(next));
        return next;
      }
      if (method === "DELETE") {
        localStorage.removeItem("cleair_local_profile");
        sessionStorage.removeItem("cleair_session_token");
        return { status: "deleted" };
      }
      return saved;
    }
    return { status: "ok", offline_mode: true };
  },

  async getAirCurrent(lat = 19.0760, lon = 72.8777) {
    try {
      const res = await fetch(`${API_BASE}/air/current?lat=${lat}&lon=${lon}`);
      if (res.ok) return res.json();
    } catch (_) {}
    // Direct Open-Meteo fallback when backend is not attached (e.g. static Netlify host)
    const om = await fetch(
      `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=pm2_5,pm10,nitrogen_dioxide,ozone,european_aqi`
    );
    if (!om.ok) throw new Error("Air quality service unavailable");
    const d = await om.json();
    const cur = d.current || {};
    const aqi = Math.round((cur.pm2_5 || 35) * 2.1);
    return {
      aqi,
      category: aqi <= 50 ? "Good" : aqi <= 100 ? "Satisfactory" : aqi <= 200 ? "Moderate" : "Poor",
      source: "Open-Meteo Live",
      pollutants: {
        pm2_5: cur.pm2_5 ?? 0,
        pm10: cur.pm10 ?? 0,
        no2: cur.nitrogen_dioxide ?? 0,
        o3: cur.ozone ?? 0,
      },
    };
  },

  async getAirForecast(lat = 19.0760, lon = 72.8777) {
    const res = await fetch(`${API_BASE}/air/forecast?lat=${lat}&lon=${lon}`);
    if (!res.ok) throw new Error("Forecast unavailable");
    return res.json();
  },

  getProfile() { return this.request("/profile"); },
  updateProfile(updates) { return this.request("/profile", { method: "PATCH", body: JSON.stringify(updates) }); },
  deleteProfile() { return this.request("/profile", { method: "DELETE" }); },
  sendChat(message) { return this.request("/chat", { method: "POST", body: JSON.stringify({ message }) }); },
};
