// CLEAIR 2.0 Centralized API Service
const API_BASE = "http://127.0.0.1:8000/v1";

export const api = {
  async ensureSession(force = false) {
    let token = !force ? sessionStorage.getItem("cleair_session_token") : null;
    if (token) return token;
    const res = await fetch(`${API_BASE}/session`, { method: "POST" });
    if (!res.ok) throw new Error(`Session error (${res.status})`);
    const data = await res.json();
    sessionStorage.setItem("cleair_session_token", data.session_token);
    return data.session_token;
  },

  async request(path, options = {}) {
    let token = await this.ensureSession(false);
    const headers = { "Content-Type": "application/json", "x-session-token": token, ...(options.headers || {}) };
    let res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.status === 401) {
      token = await this.ensureSession(true);
      headers["x-session-token"] = token;
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
  },

  async getAirCurrent(lat = 19.0760, lon = 72.8777) {
    const res = await fetch(`${API_BASE}/air/current?lat=${lat}&lon=${lon}`);
    if (!res.ok) throw new Error("Air quality service unavailable");
    return res.json();
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
