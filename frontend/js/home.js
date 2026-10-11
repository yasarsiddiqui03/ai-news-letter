/* ==========================================================================
   AI NEWS LETTER - Main Feed, 21 Cards No-Repeat Grid, Saved Drawer & Summarizer
   ========================================================================== */

const Home = {
  activeCategory: "All",
  currentQuery: "",
  isLoading: false,

  init() {
    API.initTheme();
    this.bindEvents();
    this.loadNews(false);
  },

  bindEvents() {
    // Category tabs
    document.querySelectorAll(".cat-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const cat = btn.dataset.category;
        if (this.activeCategory === cat && !this.currentQuery) return;
        this.activeCategory = cat;
        this.currentQuery = "";
        const searchInput = document.getElementById("search-input");
        if (searchInput) searchInput.value = "";

        document.querySelectorAll(".cat-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.loadNews(false);
      });
    });

    // Refresh Button (No page reload! AJAX only)
    const refreshBtn = document.getElementById("refresh-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        if (this.isLoading) return;
        this.loadNews(true);
      });
    }

    // Search bar
    const searchInput = document.getElementById("search-input");
    const searchClear = document.getElementById("search-clear");
    if (searchInput) {
      let debounceTimeout;
      searchInput.addEventListener("input", (e) => {
        const query = e.target.value.trim();
        searchClear.style.display = query ? "block" : "none";
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
          this.currentQuery = query;
          if (query) {
            this.executeSearch(query);
          } else {
            this.loadNews(false);
          }
        }, 400);
      });

      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          clearTimeout(debounceTimeout);
          this.currentQuery = searchInput.value.trim();
          if (this.currentQuery) {
            this.executeSearch(this.currentQuery);
          } else {
            this.loadNews(false);
          }
        }
      });
    }

    if (searchClear) {
      searchClear.addEventListener("click", () => {
        searchInput.value = "";
        searchClear.style.display = "none";
        this.currentQuery = "";
        this.loadNews(false);
      });
    }

    // Saved Drawer toggle
    const savedBtn = document.getElementById("saved-nav-btn");
    if (savedBtn) {
      savedBtn.addEventListener("click", () => this.openSavedDrawer());
    }

    const drawerClose = document.getElementById("saved-drawer-close");
    const drawerOverlay = document.getElementById("saved-drawer-overlay");
    if (drawerClose) drawerClose.addEventListener("click", () => this.closeSavedDrawer());
    if (drawerOverlay) drawerOverlay.addEventListener("click", () => this.closeSavedDrawer());

    // Summarizer
    const summarizeBtn = document.getElementById("summarize-btn");
    const summarizeTextarea = document.getElementById("summarize-input");
    const charCounter = document.getElementById("char-counter");

    if (summarizeTextarea && charCounter) {
      summarizeTextarea.addEventListener("input", () => {
        charCounter.textContent = `${summarizeTextarea.value.length} characters`;
      });
    }

    if (summarizeBtn) {
      summarizeBtn.addEventListener("click", () => this.handleSummarize());
    }

    const copyBtn = document.getElementById("copy-summary-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => this.copySummaryToClipboard());
    }
  },

  showSkeletons() {
    const grid = document.getElementById("news-grid");
    if (!grid) return;
    grid.innerHTML = "";
    for (let i = 0; i < 21; i++) {
      const skel = document.createElement("div");
      skel.className = "skeleton-card";
      grid.appendChild(skel);
    }
  },

  async loadNews(isRefresh = false) {
    if (this.isLoading) return;
    this.isLoading = true;

    const refreshBtn = document.getElementById("refresh-btn");
    if (refreshBtn) refreshBtn.classList.add("spinning");
    this.showSkeletons();

    try {
      const url = `/api/news?category=${encodeURIComponent(this.activeCategory)}&refresh=${isRefresh ? "true" : "false"}`;
      const data = await API.request(url);
      
      const articles = data.articles || [];
      this.renderNewsGrid(articles);

      const countEl = document.getElementById("feed-count-badge");
      if (countEl) countEl.textContent = `${articles.length} latest briefings`;
    } catch (err) {
      console.error("Load news error:", err);
      const grid = document.getElementById("news-grid");
      if (grid) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
            <p style="color: var(--accent-rose); font-size: 1.1rem; margin-bottom: 12px;">Failed to fetch the latest briefings.</p>
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px;">${this.escapeHtml(err.message)}</p>
            <button class="btn-pill btn-primary" onclick="Home.loadNews(true)">Retry Fetch</button>
          </div>
        `;
      }
    } finally {
      this.isLoading = false;
      if (refreshBtn) refreshBtn.classList.remove("spinning");
    }
  },

  async executeSearch(query) {
    this.showSkeletons();
    this.isLoading = true;
    try {
      const data = await API.request(`/api/news/search?q=${encodeURIComponent(query)}`);
      const articles = data.articles || [];
      this.renderNewsGrid(articles);
      const countEl = document.getElementById("feed-count-badge");
      if (countEl) countEl.textContent = `${articles.length} results for "${this.escapeHtml(query)}"`;
    } catch (err) {
      API.showToast("Search failed: " + err.message, "error");
    } finally {
      this.isLoading = false;
    }
  },

  renderNewsGrid(articles) {
    const grid = document.getElementById("news-grid");
    if (!grid) return;
    grid.innerHTML = "";

    if (!articles || articles.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
          <p style="font-size: 1.2rem; color: var(--text-secondary); margin-bottom: 8px;">No news briefings found for this filter.</p>
          <button class="btn-pill btn-primary" onclick="Home.loadNews(true)">Refresh Feed</button>
        </div>
      `;
      return;
    }

    articles.forEach((art, index) => {
      const card = document.createElement("article");
      card.className = "news-card";
      card.style.animationDelay = `${index * 35}ms`;

      // Relative published time
      const timeFormatted = this.formatRelativeTime(art.published_at);
      const isSaved = Boolean(art.is_saved);

      const placeholderGrad = this.getCategoryGradient(art.category);

      card.innerHTML = `
        <div class="card-media-wrapper">
          ${
            art.image
              ? `<img src="${this.escapeHtml(art.image)}" alt="${this.escapeHtml(art.title)}" class="card-image" loading="lazy" onerror="this.outerHTML='<div class=\\'card-placeholder\\' style=\\'background:${placeholderGrad}\\'>${this.escapeHtml(art.category)}</div>'">`
              : `<div class="card-placeholder" style="background:${placeholderGrad}">${this.escapeHtml(art.category)}</div>`
          }
          <span class="card-tag">${this.escapeHtml(art.category || "AI")}</span>
          <button class="card-save-btn ${isSaved ? "saved" : ""}" title="${isSaved ? "Remove bookmark" : "Save article"}" data-url="${this.escapeHtml(art.url)}">
            ${isSaved ? "★" : "☆"}
          </button>
        </div>
        <div class="card-body">
          <div class="card-source-bar">
            <span class="card-source-name">${this.escapeHtml(art.source || "News")}</span>
            <span class="card-time">${timeFormatted}</span>
          </div>
          <h3 class="card-title">${this.escapeHtml(art.title)}</h3>
          <p class="card-desc">${this.escapeHtml(art.description || "")}</p>
          <div class="card-footer">
            <span>Read AI Summary &rarr;</span>
          </div>
        </div>
      `;

      // Card click opens Article Page (unless save button was clicked)
      card.addEventListener("click", (e) => {
        if (e.target.closest(".card-save-btn")) return;
        if (art.id) {
          window.location.href = `article.html?id=${art.id}`;
        } else {
          // If search result without DB id, encode URL
          window.location.href = `article.html?url=${encodeURIComponent(art.url)}`;
        }
      });

      // Save button click
      const saveBtn = card.querySelector(".card-save-btn");
      saveBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.toggleSaveArticle(art, saveBtn);
      });

      grid.appendChild(card);
    });
  },

  async toggleSaveArticle(art, btnEl) {
    if (!Auth.currentUser) {
      API.showToast("Please log in to save articles.", "info");
      Auth.openModal("login");
      return;
    }

    try {
      const res = await API.request("/api/news/save", {
        method: "POST",
        body: {
          url: art.url,
          title: art.title,
          description: art.description,
          image: art.image,
          source: art.source,
          published_at: art.published_at,
          category: art.category,
          action: "toggle"
        }
      });

      if (res.saved) {
        btnEl.classList.add("saved");
        btnEl.innerHTML = "★";
        btnEl.title = "Remove bookmark";
        API.showToast("Article saved to your reading list.", "success");
      } else {
        btnEl.classList.remove("saved");
        btnEl.innerHTML = "☆";
        btnEl.title = "Save article";
        API.showToast("Article removed from saved.", "info");
      }
    } catch (err) {
      API.showToast(err.message || "Failed to update saved state.", "error");
    }
  },

  async openSavedDrawer() {
    if (!Auth.currentUser) {
      API.showToast("Please log in to view your saved articles.", "info");
      Auth.openModal("login");
      return;
    }

    const overlay = document.getElementById("saved-drawer-overlay");
    const panel = document.getElementById("saved-drawer-panel");
    const body = document.getElementById("saved-drawer-body");

    overlay.classList.add("active");
    panel.classList.add("active");
    body.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">Loading your saved articles...</div>`;

    try {
      const data = await API.request("/api/news/saved");
      const list = data.articles || [];

      if (list.length === 0) {
        body.innerHTML = `
          <div style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
            <div style="font-size: 32px; margin-bottom: 12px;">📑</div>
            <p>You haven't saved any articles yet.</p>
            <p style="font-size: 0.85rem; margin-top: 6px;">Click the star icon on any news card to bookmark it.</p>
          </div>
        `;
        return;
      }

      body.innerHTML = "";
      list.forEach((item) => {
        const itemEl = document.createElement("div");
        itemEl.className = "saved-item-card";
        const placeholderGrad = this.getCategoryGradient(item.category);

        itemEl.innerHTML = `
          ${
            item.image
              ? `<img src="${this.escapeHtml(item.image)}" alt="" class="saved-item-thumb" onerror="this.outerHTML='<div class=\\'saved-item-thumb\\' style=\\'background:${placeholderGrad}\\'></div>'">`
              : `<div class="saved-item-thumb" style="background:${placeholderGrad}"></div>`
          }
          <div class="saved-item-info">
            <h4 class="saved-item-title">${this.escapeHtml(item.title)}</h4>
            <div class="saved-item-meta">${this.escapeHtml(item.source)} &bull; ${this.escapeHtml(item.category)}</div>
            <button class="unsave-btn" data-url="${this.escapeHtml(item.url)}">Remove</button>
          </div>
        `;

        itemEl.addEventListener("click", (e) => {
          if (e.target.classList.contains("unsave-btn")) return;
          window.location.href = `article.html?url=${encodeURIComponent(item.url)}`;
        });

        const unsaveBtn = itemEl.querySelector(".unsave-btn");
        unsaveBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          await this.unsaveArticle(item.url, itemEl);
        });

        body.appendChild(itemEl);
      });
    } catch (err) {
      body.innerHTML = `<div style="color: var(--accent-rose); padding: 20px;">Failed to load saved items: ${this.escapeHtml(err.message)}</div>`;
    }
  },

  async unsaveArticle(url, cardElement) {
    try {
      await API.request("/api/news/save", {
        method: "POST",
        body: { url, action: "unsave" }
      });
      cardElement.remove();
      API.showToast("Article removed from saved.", "info");
      // Also update any visible card on the home feed
      const btn = document.querySelector(`.card-save-btn[data-url="${url}"]`);
      if (btn) {
        btn.classList.remove("saved");
        btn.innerHTML = "☆";
      }
    } catch (err) {
      API.showToast(err.message || "Failed to remove article.", "error");
    }
  },

  closeSavedDrawer() {
    const overlay = document.getElementById("saved-drawer-overlay");
    const panel = document.getElementById("saved-drawer-panel");
    if (overlay) overlay.classList.remove("active");
    if (panel) panel.classList.remove("active");
  },

  async handleSummarize() {
    const input = document.getElementById("summarize-input");
    const resultBox = document.getElementById("summarize-result-box");
    const btn = document.getElementById("summarize-btn");
    const text = input ? input.value.trim() : "";

    if (!text || text.length < 50) {
      API.showToast("Please paste at least 50 characters of news text to summarize.", "error");
      return;
    }

    btn.disabled = true;
    btn.innerHTML = `<span class="btn-refresh spinning" style="display:inline-block; margin-right:6px;">⚙️</span> Analyzing & Summarizing...`;

    try {
      const res = await API.request("/api/summarize", {
        method: "POST",
        body: { text }
      });

      const s = res.summary;
      document.getElementById("summary-headline").textContent = s.headline;

      const bulletsContainer = document.getElementById("summary-bullets");
      bulletsContainer.innerHTML = "";
      (s.bullets || []).forEach((b) => {
        const li = document.createElement("li");
        li.textContent = b;
        bulletsContainer.appendChild(li);
      });

      document.getElementById("summary-paragraph").textContent = s.paragraph;
      resultBox.style.display = "block";
      resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
      API.showToast("Summary synthesized successfully!", "success");
    } catch (err) {
      API.showToast(err.message || "Summarization failed.", "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "Summarize with AI";
    }
  },

  copySummaryToClipboard() {
    const headline = document.getElementById("summary-headline").textContent;
    const bullets = Array.from(document.querySelectorAll("#summary-bullets li"))
      .map((li) => "• " + li.textContent)
      .join("\n");
    const paragraph = document.getElementById("summary-paragraph").textContent;

    const fullSummary = `${headline}\n\nKey Takeaways:\n${bullets}\n\nSynthesis:\n${paragraph}\n\n— Generated by AI NEWS LETTER`;

    navigator.clipboard
      .writeText(fullSummary)
      .then(() => API.showToast("Summary copied to clipboard!", "success"))
      .catch(() => API.showToast("Could not access clipboard.", "error"));
  },

  formatRelativeTime(isoDateStr) {
    if (!isoDateStr) return "Recently";
    try {
      const date = new Date(isoDateStr);
      const now = new Date();
      const diffSecs = Math.floor((now - date) / 1000);

      if (diffSecs < 60) return "Just now";
      if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
      if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;
      if (diffSecs < 604800) return `${Math.floor(diffSecs / 86400)}d ago`;
      return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch {
      return "Recently";
    }
  },

  getCategoryGradient(category) {
    const grads = {
      Technology: "linear-gradient(135deg, #1e3a8a, #0284c7)",
      AI: "linear-gradient(135deg, #4c1d95, #8b5cf6)",
      Science: "linear-gradient(135deg, #064e3b, #10b981)",
      Startups: "linear-gradient(135deg, #7c2d12, #f59e0b)",
      Business: "linear-gradient(135deg, #1e293b, #475569)",
      "Cyber Security": "linear-gradient(135deg, #881337, #f43f5e)",
      "World News": "linear-gradient(135deg, #134e4a, #06b6d4)"
    };
    return grads[category] || "linear-gradient(135deg, #1e293b, #38bdf8)";
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

window.Home = Home;
document.addEventListener("DOMContentLoaded", () => Home.init());
