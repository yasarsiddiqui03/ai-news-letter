/* ==========================================================================
   AI NEWS LETTER - Admin Controller
   2FA TOTP Authenticator, QR Code Setup, and Protected Admin Dashboard
   ========================================================================== */

const Admin = {
  isAdminLoggedIn: false,
  tempToken: "",
  activeDashboardTab: "users",

  init() {
    this.bindEvents();
    this.checkAdminStatus();
  },

  async checkAdminStatus() {
    try {
      const res = await API.request("/api/admin/check");
      this.isAdminLoggedIn = Boolean(res.is_admin);
    } catch {
      this.isAdminLoggedIn = false;
    }
  },

  bindEvents() {
    const adminNavBtn = document.getElementById("admin-nav-btn");
    if (adminNavBtn) {
      adminNavBtn.addEventListener("click", () => this.handleAdminNavClick());
    }

    const modalClose = document.getElementById("admin-modal-close");
    if (modalClose) {
      modalClose.addEventListener("click", () => this.closeModal());
    }

    // Switch from notice to login form
    const proceedLoginBtn = document.getElementById("admin-proceed-login-btn");
    if (proceedLoginBtn) {
      proceedLoginBtn.addEventListener("click", () => this.showView("login"));
    }

    // Admin Credentials Submit
    const loginBtn = document.getElementById("admin-submit-login-btn");
    if (loginBtn) {
      loginBtn.addEventListener("click", () => this.handleAdminLogin());
    }

    // Admin 2FA Submit
    const verify2faBtn = document.getElementById("admin-submit-2fa-btn");
    if (verify2faBtn) {
      verify2faBtn.addEventListener("click", () => this.handleAdmin2faVerify());
    }

    // Show QR Setup
    const setupQrLink = document.getElementById("admin-show-qr-link");
    if (setupQrLink) {
      setupQrLink.addEventListener("click", () => this.loadQrSetup());
    }

    // Back to Login from QR Setup
    const backFromQrBtn = document.getElementById("admin-back-from-qr");
    if (backFromQrBtn) {
      backFromQrBtn.addEventListener("click", () => this.showView("login"));
    }

    // Dashboard Tabs
    document.querySelectorAll(".admin-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        this.switchDashboardTab(tab);
      });
    });

    // Activity live search
    const activitySearch = document.getElementById("admin-activity-search");
    if (activitySearch) {
      let timeout;
      activitySearch.addEventListener("input", (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => this.loadActivityLogs(e.target.value.trim()), 300);
      });
    }

    // Admin Logout
    const logoutBtn = document.getElementById("admin-logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", () => this.handleAdminLogout());
    }
  },

  async handleAdminNavClick() {
    await this.checkAdminStatus();
    const modal = document.getElementById("admin-modal");
    if (!modal) return;
    modal.classList.add("active");

    if (this.isAdminLoggedIn) {
      this.showView("dashboard");
      this.loadDashboardData();
    } else {
      this.showView("notice");
    }
  },

  closeModal() {
    const modal = document.getElementById("admin-modal");
    if (modal) modal.classList.remove("active");
  },

  showView(viewName) {
    const views = ["notice", "login", "2fa", "qr", "dashboard"];
    views.forEach((v) => {
      const el = document.getElementById(`admin-view-${v}`);
      if (el) el.style.display = v === viewName ? "block" : "none";
    });

    const titleEl = document.getElementById("admin-modal-title");
    if (titleEl) {
      const titles = {
        notice: "Restricted Access",
        login: "Administrator Portal",
        "2fa": "Two-Factor Verification",
        qr: "Authenticator App Setup",
        dashboard: "Admin Management Console"
      };
      titleEl.textContent = titles[viewName] || "Admin Portal";
    }
  },

  async handleAdminLogin() {
    const idInput = document.getElementById("admin-id-input");
    const passInput = document.getElementById("admin-pass-input");
    const alertEl = document.getElementById("admin-login-alert");

    const adminId = idInput ? idInput.value.trim() : "";
    const password = passInput ? passInput.value : "";

    if (!adminId || !password) {
      this.showAlert(alertEl, "Please enter both Admin ID and Password.");
      return;
    }

    try {
      const res = await API.request("/api/admin/login", {
        method: "POST",
        body: { admin_id: adminId, password }
      });

      if (res.require_2fa) {
        this.tempToken = res.temp_token;
        this.showView("2fa");
        const totpInput = document.getElementById("admin-totp-input");
        if (totpInput) {
          totpInput.value = res.dev_totp_code || "";
          totpInput.focus();
        }
        if (res.dev_totp_code) {
          API.showToast(`Authenticator Code: ${res.dev_totp_code}`, "info");
        }
      }
    } catch (err) {
      this.showAlert(alertEl, err.message || "Invalid administrator credentials.");
    }
  },

  async handleAdmin2faVerify() {
    const totpInput = document.getElementById("admin-totp-input");
    const alertEl = document.getElementById("admin-2fa-alert");
    const code = totpInput ? totpInput.value.trim() : "";

    if (!code || code.length !== 6) {
      this.showAlert(alertEl, "Please enter the 6-digit Authenticator code.");
      return;
    }

    try {
      const res = await API.request("/api/admin/verify-2fa", {
        method: "POST",
        body: {
          temp_token: this.tempToken,
          totp_code: code
        }
      });

      API.setAdminToken(res.admin_token);
      this.isAdminLoggedIn = true;
      API.showToast("Admin authenticated successfully!", "success");
      this.showView("dashboard");
      this.loadDashboardData();
    } catch (err) {
      this.showAlert(alertEl, err.message || "Invalid 2FA code. Please check your Authenticator.");
    }
  },

  async loadQrSetup() {
    this.showView("qr");
    const qrImg = document.getElementById("admin-qr-image");
    const secretCode = document.getElementById("admin-secret-code");

    try {
      const data = await API.request("/api/admin/setup-2fa");
      if (qrImg) qrImg.src = data.qr_code_url;
      if (secretCode) secretCode.textContent = data.secret;
    } catch (err) {
      API.showToast("Could not generate 2FA setup QR: " + err.message, "error");
    }
  },

  switchDashboardTab(tab) {
    this.activeDashboardTab = tab;
    document.querySelectorAll(".admin-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tab);
    });

    const usersPane = document.getElementById("admin-tab-users-pane");
    const activityPane = document.getElementById("admin-tab-activity-pane");

    if (tab === "users") {
      usersPane.style.display = "block";
      activityPane.style.display = "none";
      this.loadUsersList();
    } else {
      usersPane.style.display = "none";
      activityPane.style.display = "block";
      this.loadActivityLogs();
    }
  },

  loadDashboardData() {
    this.switchDashboardTab(this.activeDashboardTab || "users");
  },

  async loadUsersList() {
    const tbody = document.getElementById("admin-users-tbody");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px;">Loading registered users...</td></tr>`;

    try {
      const data = await API.request("/api/admin/users");
      const users = data.users || [];

      if (users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--text-muted);">No users registered yet.</td></tr>`;
        return;
      }

      tbody.innerHTML = "";
      users.forEach((u) => {
        const tr = document.createElement("tr");
        const typeBadge = `<span class="table-badge ${u.type}">${u.type.toUpperCase()}</span>`;
        tr.innerHTML = `
          <td><strong>#${u.id}</strong></td>
          <td>${typeBadge}</td>
          <td>${this.escapeHtml(u.identifier)}</td>
          <td>${this.escapeHtml(u.created_at || "—")}</td>
          <td>${this.escapeHtml(u.last_login_at || "—")}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--accent-rose); padding: 20px;">Failed to load users: ${this.escapeHtml(err.message)}</td></tr>`;
    }
  },

  async loadActivityLogs(query = "") {
    const tbody = document.getElementById("admin-activity-tbody");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px;">Loading user activity...</td></tr>`;

    try {
      const url = `/api/admin/activity${query ? "?q=" + encodeURIComponent(query) : ""}`;
      const data = await API.request(url);
      const logs = data.activity || [];

      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--text-muted);">No activity recorded matching this query.</td></tr>`;
        return;
      }

      tbody.innerHTML = "";
      logs.forEach((log) => {
        const tr = document.createElement("tr");
        const dt = new Date(log.timestamp * 1000).toLocaleString();
        tr.innerHTML = `
          <td><strong>${this.escapeHtml(log.user_identifier || "Anonymous")}</strong></td>
          <td>${this.escapeHtml(log.article_title)}</td>
          <td><a href="${this.escapeHtml(log.article_url)}" target="_blank" rel="noopener noreferrer" class="table-link">${this.escapeHtml(log.article_url)}</a></td>
          <td><span class="table-badge email">${this.escapeHtml(log.category || "General")}</span></td>
          <td style="color: var(--text-muted); font-size: 0.8rem;">${dt}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--accent-rose); padding: 20px;">Failed to load activity logs: ${this.escapeHtml(err.message)}</td></tr>`;
    }
  },

  async handleAdminLogout() {
    try {
      await API.request("/api/admin/logout", { method: "POST" });
    } catch (e) {
      // Ignore
    }
    API.setAdminToken("");
    this.isAdminLoggedIn = false;
    this.closeModal();
    API.showToast("Admin session ended.", "info");
  },

  showAlert(el, msg) {
    if (el) {
      el.textContent = msg;
      el.className = "form-alert error";
      el.style.display = "block";
    }
  },

  escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, (m) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[m]);
  }
};

document.addEventListener("DOMContentLoaded", () => Admin.init());
