/* ==========================================================================
   AI NEWS LETTER - API Client & Utility Library
   Vanilla JS, secure session handling, persistent JWT, and toast alerts
   ========================================================================== */

const API = {
  // Session handling for No-Repeat logic
  getSessionId() {
    let sid = localStorage.getItem("ainews_session_id");
    if (!sid) {
      sid = "session_" + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
      localStorage.setItem("ainews_session_id", sid);
    }
    return sid;
  },

  // JWT Token management
  getToken() {
    return localStorage.getItem("ainews_auth_token") || "";
  },

  setToken(token) {
    if (token) {
      localStorage.setItem("ainews_auth_token", token);
    } else {
      localStorage.removeItem("ainews_auth_token");
    }
  },

  getAdminToken() {
    return localStorage.getItem("ainews_admin_token") || "";
  },

  setAdminToken(token) {
    if (token) {
      localStorage.setItem("ainews_admin_token", token);
    } else {
      localStorage.removeItem("ainews_admin_token");
    }
  },

  // Detect environment base URL (handles file:/// direct opening)
  getBaseUrl() {
    if (typeof window !== "undefined" && (window.location.protocol === "file:" || !window.location.origin || window.location.origin === "null")) {
      return "http://localhost:5000";
    }
    return "";
  },

  // HTTP Request Helper
  async request(endpoint, options = {}) {
    const headers = options.headers || {};
    headers["X-Session-ID"] = this.getSessionId();

    const token = this.getToken();
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const adminToken = this.getAdminToken();
    if (endpoint.startsWith("/api/admin") && adminToken) {
      headers["Authorization"] = `Bearer ${adminToken}`;
    }

    if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.body);
    }

    options.headers = headers;
    options.credentials = "include"; // Include cookies

    const baseUrl = this.getBaseUrl();
    const targetUrl = endpoint.startsWith("http") ? endpoint : `${baseUrl}${endpoint}`;

    try {
      const response = await fetch(targetUrl, options);
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.message || `Request failed with status ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  // Toast Notification
  showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "error") icon = "⚠️";

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },

  // Theme Management (Light / Dark)
  initTheme() {
    const saved = localStorage.getItem("ainews_theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    const themeBtn = document.getElementById("theme-toggle-btn");
    if (themeBtn) {
      themeBtn.innerHTML = saved === "dark" ? "☀️" : "🌙";
      themeBtn.onclick = () => {
        const current = document.documentElement.getAttribute("data-theme");
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("ainews_theme", next);
        themeBtn.innerHTML = next === "dark" ? "☀️" : "🌙";
      };
    }
  }
};
