/* ==========================================================================
   AI NEWS LETTER - Article Details & AI Summary Controller
   Visitor activity tracking, DB-cached AI synthesis, and bookmark support
   ========================================================================== */

const ArticlePage = {
  article: null,

  async init() {
    API.initTheme();

    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    const rawUrl = params.get("url");

    if (!id && !rawUrl) {
      window.location.href = "/home.html";
      return;
    }

    await this.loadArticle(id, rawUrl);
    this.bindEvents();
  },

  async loadArticle(id, rawUrl) {
    const loadingEl = document.getElementById("article-loading");
    const contentEl = document.getElementById("article-content");

    try {
      let data;
      if (id) {
        data = await API.request(`/api/news/article/${id}`);
      } else {
        // Query search by raw URL or search route
        data = await API.request(`/api/news/search?q=${encodeURIComponent(rawUrl)}`);
        if (data.articles && data.articles.length > 0) {
          data = { success: true, article: data.articles[0] };
        } else {
          throw new Error("Article could not be loaded.");
        }
      }

      if (!data.success || !data.article) {
        throw new Error("Article details unavailable.");
      }

      this.article = data.article;
      this.renderArticle(this.article);

      // Log this visit for the admin panel
      this.logVisit(this.article);

      if (loadingEl) loadingEl.style.display = "none";
      if (contentEl) contentEl.style.display = "block";
    } catch (err) {
      console.error("Article load failure:", err);
      if (loadingEl) {
        loadingEl.innerHTML = `
          <div style="text-align: center; padding: 60px 20px;">
            <h2 style="color: var(--accent-rose); margin-bottom: 12px;">Failed to Load Article</h2>
            <p style="color: var(--text-muted); margin-bottom: 24px;">${this.escapeHtml(err.message)}</p>
            <a href="/home.html" class="btn-pill btn-primary">&larr; Back to News Feed</a>
          </div>
        `;
      }
    }
  },

  renderArticle(art) {
    document.title = `${art.title} — AI NEWS LETTER`;

    // Category badge
    const catBadge = document.getElementById("article-category-badge");
    if (catBadge) catBadge.textContent = art.category || "AI";

    // Title
    const titleEl = document.getElementById("article-title");
    if (titleEl) titleEl.textContent = art.title;

    // Metadata
    const sourceEl = document.getElementById("article-source");
    if (sourceEl) sourceEl.textContent = art.source || "News Source";

    const dateEl = document.getElementById("article-date");
    if (dateEl) {
      const dt = art.published_at ? new Date(art.published_at) : new Date();
      dateEl.textContent = dt.toLocaleDateString(undefined, {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric"
      });
    }

    // Media
    const imgWrapper = document.getElementById("article-media-container");
    if (imgWrapper) {
      const grad = this.getCategoryGradient(art.category);
      if (art.image) {
        imgWrapper.innerHTML = `
          <img src="${this.escapeHtml(art.image)}" alt="${this.escapeHtml(art.title)}" class="article-hero-image" onerror="this.outerHTML='<div class=\\'article-hero-placeholder\\' style=\\'background:${grad}\\'>${this.escapeHtml(art.category)}</div>'">
        `;
      } else {
        imgWrapper.innerHTML = `<div class="article-hero-placeholder" style="background:${grad}">${this.escapeHtml(art.category)}</div>`;
      }
    }

    // Read More Link
    const readMoreBtn = document.getElementById("read-more-link");
    if (readMoreBtn) {
      readMoreBtn.href = art.url;
      readMoreBtn.target = "_blank";
      readMoreBtn.rel = "noopener noreferrer";
    }

    // AI Summary Block
    const summary = art.ai_summary;
    if (summary) {
      const headlineEl = document.getElementById("ai-headline");
      if (headlineEl) headlineEl.textContent = summary.headline || art.title;

      const bulletsContainer = document.getElementById("ai-bullets");
      if (bulletsContainer) {
        bulletsContainer.innerHTML = "";
        (summary.bullets || []).forEach((b) => {
          const li = document.createElement("li");
          li.textContent = b;
          bulletsContainer.appendChild(li);
        });
      }

      const paraEl = document.getElementById("ai-paragraph");
      if (paraEl) paraEl.textContent = summary.paragraph || "";
    }

    // Bookmark state
    this.updateBookmarkUI(art.is_saved);
  },

  async logVisit(art) {
    try {
      await API.request("/api/news/log-visit", {
        method: "POST",
        body: {
          title: art.title,
          url: art.url,
          category: art.category
        }
      });
    } catch (e) {
      // Background activity log non-blocking
    }
  },

  updateBookmarkUI(isSaved) {
    const saveBtn = document.getElementById("article-save-btn");
    if (!saveBtn) return;
    if (isSaved) {
      saveBtn.classList.add("saved");
      saveBtn.innerHTML = `★ Saved`;
    } else {
      saveBtn.classList.remove("saved");
      saveBtn.innerHTML = `☆ Save Article`;
    }
  },

  bindEvents() {
    const saveBtn = document.getElementById("article-save-btn");
    if (saveBtn) {
      saveBtn.addEventListener("click", async () => {
        if (!Auth.currentUser) {
          API.showToast("Please log in to bookmark articles.", "info");
          Auth.openModal("login");
          return;
        }
        if (!this.article) return;

        try {
          const res = await API.request("/api/news/save", {
            method: "POST",
            body: {
              url: this.article.url,
              title: this.article.title,
              description: this.article.description,
              image: this.article.image,
              source: this.article.source,
              published_at: this.article.published_at,
              category: this.article.category,
              action: "toggle"
            }
          });
          this.article.is_saved = res.saved;
          this.updateBookmarkUI(res.saved);
          API.showToast(res.message, res.saved ? "success" : "info");
        } catch (err) {
          API.showToast(err.message, "error");
        }
      });
    }

    const copyBtn = document.getElementById("copy-article-summary-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        if (!this.article || !this.article.ai_summary) return;
        const s = this.article.ai_summary;
        const bullets = (s.bullets || []).map((b) => "• " + b).join("\n");
        const full = `${s.headline}\n\nKey Takeaways:\n${bullets}\n\nExecutive Synthesis:\n${s.paragraph}\n\nOriginal Source: ${this.article.url}\n— Powered by AI NEWS LETTER`;
        navigator.clipboard
          .writeText(full)
          .then(() => API.showToast("Article AI summary copied!", "success"))
          .catch(() => API.showToast("Failed to copy.", "error"));
      });
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

document.addEventListener("DOMContentLoaded", () => ArticlePage.init());
