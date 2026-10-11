/* ==========================================================================
   AI NEWS LETTER - Authentication Logic
   Phone & Email OTP Authentication, Signup vs Login segregation, Persistent JWT
   ========================================================================== */

const Auth = {
  currentType: "email",    // 'phone' or 'email'
  currentMode: "signup",   // 'signup' or 'login'
  currentIdentifier: "",
  cooldownTimer: null,
  cooldownSeconds: 0,
  currentUser: null,

  init() {
    this.bindEvents();
    this.checkSession();
  },

  async checkSession() {
    try {
      const data = await API.request("/api/auth/me");
      if (data.authenticated && data.user) {
        this.currentUser = data.user;
        this.updateAuthUI(true);
      } else {
        this.updateAuthUI(false);
      }
    } catch {
      this.updateAuthUI(false);
    }
  },

  updateAuthUI(isLoggedIn) {
    const authBtn = document.getElementById("auth-nav-btn");
    if (!authBtn) return;

    if (isLoggedIn && this.currentUser) {
      const label = this.currentUser.identifier.includes("@")
        ? this.currentUser.identifier.split("@")[0]
        : this.currentUser.identifier;

      authBtn.innerHTML = `
        <span class="user-avatar">👤</span>
        <span class="user-label">${this.escapeHtml(label)}</span>
        <button id="logout-btn" class="logout-btn-inline" title="Sign out" style="margin-left:8px; opacity:0.8; color: var(--accent-rose);">✕</button>
      `;
      authBtn.classList.add("logged-in");
      authBtn.onclick = (e) => {
        if (e.target.id === "logout-btn") {
          e.stopPropagation();
          this.logout();
        }
      };
    } else {
      authBtn.innerHTML = `<span>Login / Sign Up</span>`;
      authBtn.classList.remove("logged-in");
      authBtn.onclick = () => this.openModal("login");
    }
  },

  async logout() {
    try {
      await API.request("/api/auth/logout", { method: "POST" });
    } catch (e) {
      console.warn("Logout request err", e);
    }
    API.setToken("");
    this.currentUser = null;
    this.updateAuthUI(false);
    API.showToast("You have been signed out.", "info");
    // Refresh page news cards to sync saved bookmarks state
    if (window.Home && typeof window.Home.loadNews === "function") {
      window.Home.loadNews();
    }
  },

  openModal(initialMode = "signup") {
    this.currentMode = initialMode;
    const modal = document.getElementById("auth-modal");
    if (!modal) return;

    this.resetForm();
    this.updateModalModeUI();
    modal.classList.add("active");
  },

  closeModal() {
    const modal = document.getElementById("auth-modal");
    if (modal) modal.classList.remove("active");
    this.clearIntervalCooldown();
  },

  resetForm() {
    document.getElementById("auth-phone").value = "";
    document.getElementById("auth-email").value = "";
    this.clearOtpInputs();
    this.hideAlert();
    this.showStep("identifier");
  },

  updateModalModeUI() {
    const titleEl = document.getElementById("auth-modal-title");
    const switchPrompt = document.getElementById("auth-switch-prompt");
    const switchLink = document.getElementById("auth-switch-link");
    const sendBtn = document.getElementById("auth-send-btn");

    if (this.currentMode === "signup") {
      if (titleEl) titleEl.textContent = "Create an Account";
      if (switchPrompt) switchPrompt.textContent = "Already have an account?";
      if (switchLink) switchLink.textContent = "Sign In";
      if (sendBtn) sendBtn.textContent = "Sign Up with OTP";
    } else {
      if (titleEl) titleEl.textContent = "Welcome Back";
      if (switchPrompt) switchPrompt.textContent = "Don't have an account?";
      if (switchLink) switchLink.textContent = "Sign Up";
      if (sendBtn) sendBtn.textContent = "Sign In with OTP";
    }
  },

  switchMode() {
    this.currentMode = this.currentMode === "signup" ? "login" : "signup";
    this.updateModalModeUI();
    this.hideAlert();
  },

  switchType(type) {
    this.currentType = type;
    document.querySelectorAll(".auth-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.type === type);
    });

    const phoneGroup = document.getElementById("phone-group");
    const emailGroup = document.getElementById("email-group");
    if (type === "phone") {
      phoneGroup.style.display = "block";
      emailGroup.style.display = "none";
    } else {
      phoneGroup.style.display = "none";
      emailGroup.style.display = "block";
    }
    this.hideAlert();
  },

  showStep(step) {
    const stepIdent = document.getElementById("auth-step-identifier");
    const stepOtp = document.getElementById("auth-step-otp");
    if (step === "otp") {
      stepIdent.style.display = "none";
      stepOtp.style.display = "block";
      // Focus first OTP input
      const firstOtp = document.querySelector(".otp-digit-box");
      if (firstOtp) setTimeout(() => firstOtp.focus(), 100);
    } else {
      stepIdent.style.display = "block";
      stepOtp.style.display = "none";
    }
  },

  getIdentifierValue() {
    if (this.currentType === "phone") {
      const code = document.getElementById("country-code-select").value.trim();
      const num = document.getElementById("auth-phone").value.trim().replace(/^0+/, "");
      if (!num) return "";
      return code + num;
    } else {
      return document.getElementById("auth-email").value.trim();
    }
  },

  async handleSendOtp() {
    const rawId = this.getIdentifierValue();
    this.hideAlert();

    if (!rawId) {
      this.showAlert(`Please enter your ${this.currentType}.`, "error");
      return;
    }

    if (this.currentType === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(rawId)) {
      this.showAlert("Please enter a valid email address.", "error");
      return;
    }

    const sendBtn = document.getElementById("auth-send-btn");
    sendBtn.disabled = true;
    sendBtn.textContent = "Sending Code...";

    try {
      const res = await API.request("/api/auth/send-otp", {
        method: "POST",
        body: {
          type: this.currentType,
          identifier: rawId,
          purpose: this.currentMode
        }
      });

      this.currentIdentifier = res.identifier || rawId;
      document.getElementById("otp-target-display").textContent = this.currentIdentifier;

      this.showStep("otp");
      this.startCooldown(res.cooldown || 30);

      // Keep digit boxes clean and empty so user enters OTP manually
      this.clearOtpInputs();
      API.showToast(res.message || "Verification code sent!", "success");
    } catch (err) {
      this.showAlert(err.message || "Failed to send verification code.", "error");
    } finally {
      sendBtn.disabled = false;
      this.updateModalModeUI();
    }
  },

  async handleVerifyOtp() {
    this.hideAlert();
    const otp = this.getEnteredOtp();

    if (otp.length !== 6) {
      this.showAlert("Please enter all 6 digits of the verification code.", "error");
      return;
    }

    const verifyBtn = document.getElementById("auth-verify-btn");
    verifyBtn.disabled = true;
    verifyBtn.textContent = "Verifying...";

    try {
      const res = await API.request("/api/auth/verify-otp", {
        method: "POST",
        body: {
          type: this.currentType,
          identifier: this.currentIdentifier,
          otp: otp,
          purpose: this.currentMode
        }
      });

      API.setToken(res.token);
      this.currentUser = res.user;
      this.updateAuthUI(true);
      API.showToast(this.currentMode === "signup" ? "Account created successfully!" : "Signed in successfully!", "success");
      this.closeModal();

      // Refresh home feed to sync saved items
      if (window.Home && typeof window.Home.loadNews === "function") {
        window.Home.loadNews();
      }
    } catch (err) {
      this.showAlert(err.message || "Verification failed.", "error");
      this.clearOtpInputs();
    } finally {
      verifyBtn.disabled = false;
      verifyBtn.textContent = "Verify & Proceed";
    }
  },

  startCooldown(seconds) {
    this.clearIntervalCooldown();
    this.cooldownSeconds = seconds;
    const resendBtn = document.getElementById("otp-resend-btn");
    const timerText = document.getElementById("otp-cooldown-timer");

    resendBtn.disabled = true;
    timerText.textContent = `(${this.cooldownSeconds}s)`;

    this.cooldownTimer = setInterval(() => {
      this.cooldownSeconds--;
      if (this.cooldownSeconds <= 0) {
        this.clearIntervalCooldown();
        resendBtn.disabled = false;
        timerText.textContent = "";
      } else {
        timerText.textContent = `(${this.cooldownSeconds}s)`;
      }
    }, 1000);
  },

  clearIntervalCooldown() {
    if (this.cooldownTimer) {
      clearInterval(this.cooldownTimer);
      this.cooldownTimer = null;
    }
  },

  getEnteredOtp() {
    const inputs = document.querySelectorAll(".otp-digit-box");
    let code = "";
    inputs.forEach((input) => (code += input.value.trim()));
    return code;
  },

  fillOtpInputs(code) {
    const inputs = document.querySelectorAll(".otp-digit-box");
    for (let i = 0; i < inputs.length && i < code.length; i++) {
      inputs[i].value = code[i];
    }
  },

  clearOtpInputs() {
    const inputs = document.querySelectorAll(".otp-digit-box");
    inputs.forEach((input) => (input.value = ""));
    if (inputs[0]) inputs[0].focus();
  },

  showAlert(message, type = "error") {
    const alertEl = document.getElementById("auth-alert");
    if (alertEl) {
      alertEl.textContent = message;
      alertEl.className = `form-alert ${type}`;
    }
  },

  hideAlert() {
    const alertEl = document.getElementById("auth-alert");
    if (alertEl) {
      alertEl.textContent = "";
      alertEl.className = "form-alert";
    }
  },

  escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (m) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[m]);
  },

  bindEvents() {
    // Tab switching
    document.querySelectorAll(".auth-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.switchType(btn.dataset.type));
    });

    // Mode switch
    const switchLink = document.getElementById("auth-switch-link");
    if (switchLink) {
      switchLink.addEventListener("click", () => this.switchMode());
    }

    // Modal close
    const closeBtn = document.getElementById("auth-modal-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.closeModal());
    }

    // Send OTP
    const sendBtn = document.getElementById("auth-send-btn");
    if (sendBtn) {
      sendBtn.addEventListener("click", () => this.handleSendOtp());
    }

    // Resend OTP
    const resendBtn = document.getElementById("otp-resend-btn");
    if (resendBtn) {
      resendBtn.addEventListener("click", () => this.handleSendOtp());
    }

    // Back from OTP step to identifier step
    const backBtn = document.getElementById("otp-back-btn");
    if (backBtn) {
      backBtn.addEventListener("click", () => this.showStep("identifier"));
    }

    // Verify OTP
    const verifyBtn = document.getElementById("auth-verify-btn");
    if (verifyBtn) {
      verifyBtn.addEventListener("click", () => this.handleVerifyOtp());
    }

    // OTP Box Navigation
    const otpInputs = document.querySelectorAll(".otp-digit-box");
    otpInputs.forEach((input, idx) => {
      input.addEventListener("input", (e) => {
        const val = e.target.value.replace(/[^0-9]/g, "");
        e.target.value = val ? val[val.length - 1] : "";
        if (e.target.value && idx < otpInputs.length - 1) {
          otpInputs[idx + 1].focus();
        }
      });

      input.addEventListener("keydown", (e) => {
        if (e.key === "Backspace" && !input.value && idx > 0) {
          otpInputs[idx - 1].focus();
        } else if (e.key === "Enter") {
          this.handleVerifyOtp();
        }
      });

      input.addEventListener("paste", (e) => {
        e.preventDefault();
        const pasted = (e.clipboardData || window.clipboardData).getData("text").replace(/[^0-9]/g, "");
        if (pasted.length === 6) {
          this.fillOtpInputs(pasted);
          this.handleVerifyOtp();
        }
      });
    });
  }
};

document.addEventListener("DOMContentLoaded", () => Auth.init());
