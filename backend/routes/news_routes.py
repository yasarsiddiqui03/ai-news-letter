import time
import uuid
from flask import Blueprint, request, jsonify, make_response
from backend.models.database import get_db
from backend.services.news_service import (
    CATEGORIES,
    get_unseen_articles_for_session,
    search_articles,
    get_article_by_id
)
from backend.services.gemini_service import summarize_article
from backend.services.admin_service import log_user_activity
from backend.routes.auth_routes import get_current_user_from_request

news_bp = Blueprint("news", __name__, url_prefix="/api/news")

def get_or_create_session_id(req, resp=None) -> str:
    """Retrieve session ID from header, cookie, or generate a new UUID."""
    user = get_current_user_from_request(req)
    if user:
        return f"user_{user['id']}"

    session_id = req.headers.get("X-Session-ID") or req.cookies.get("session_id")
    if not session_id or len(session_id) < 8:
        session_id = f"anon_{uuid.uuid4().hex}"
    return session_id

@news_bp.route("/categories", methods=["GET"])
def get_categories():
    """Return available news categories."""
    return jsonify({"categories": CATEGORIES})

@news_bp.route("", methods=["GET"])
def get_news():
    """
    Fetch exactly 21 fresh, non-repeating articles for current session.
    Params:
      - category: default 'All'
      - refresh: 'true' or 'false'
    """
    category = request.args.get("category", "All").strip()
    is_refresh = request.args.get("refresh", "false").lower() in ("true", "1")

    session_id = get_or_create_session_id(request)

    # Validate category
    if category != "All" and category not in CATEGORIES:
        category = "All"

    articles = get_unseen_articles_for_session(
        session_id=session_id,
        category=category,
        count=21,
        force_refresh=is_refresh
    )

    # Attach is_saved status if user is logged in
    user = get_current_user_from_request(request)
    saved_urls = set()
    if user:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT article_url FROM saved_articles WHERE user_id = ?", (user["id"],))
            saved_urls = {r["article_url"] for r in cursor.fetchall()}

    # Ensure 100% unique photos across all 21 returned cards
    from backend.services.news_service import CATEGORY_UNIQUE_IMAGES
    all_imgs = []
    for p in CATEGORY_UNIQUE_IMAGES.values():
        for u in p:
            if u not in all_imgs:
                all_imgs.append(u)

    seed = int(uuid.uuid4().hex[:4], 16)
    for idx, art in enumerate(articles):
        art["is_saved"] = art["url"] in saved_urls
        art["image"] = all_imgs[(seed + idx) % len(all_imgs)]

    response = make_response(jsonify({
        "success": True,
        "category": category,
        "count": len(articles),
        "articles": articles
    }))

    if "session_id" not in request.cookies and not session_id.startswith("user_"):
        response.set_cookie("session_id", session_id, max_age=86400 * 30, samesite="Lax")

    return response

@news_bp.route("/search", methods=["GET"])
def search():
    """Search news articles by query string."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"success": True, "count": 0, "articles": []})

    articles = search_articles(q, limit=21)

    user = get_current_user_from_request(request)
    saved_urls = set()
    if user:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT article_url FROM saved_articles WHERE user_id = ?", (user["id"],))
            saved_urls = {r["article_url"] for r in cursor.fetchall()}

    for art in articles:
        art["is_saved"] = art["url"] in saved_urls

    return jsonify({
        "success": True,
        "query": q,
        "count": len(articles),
        "articles": articles
    })

@news_bp.route("/article/<int:article_id>", methods=["GET"])
def get_article_detail(article_id: int):
    """Retrieve full article details and generate or fetch AI summary."""
    article = get_article_by_id(article_id)
    if not article:
        return jsonify({"success": False, "message": "Article not found."}), 404

    # Generate or get cached AI summary
    text_to_summarize = f"{article['title']}. {article.get('description', '')}"
    summary = summarize_article(text_to_summarize, title_hint=article["title"])
    article["ai_summary"] = summary

    # Check if saved by current user
    user = get_current_user_from_request(request)
    article["is_saved"] = False
    if user:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM saved_articles WHERE user_id = ? AND article_url = ?", (user["id"], article["url"]))
            article["is_saved"] = cursor.fetchone() is not None

    return jsonify({"success": True, "article": article})

@news_bp.route("/log-visit", methods=["POST"])
def log_visit():
    """Log article view activity for admin tracking."""
    data = request.get_json(silent=True) or {}
    article_title = data.get("title", "").strip()
    article_url = data.get("url", "").strip()
    category = data.get("category", "").strip()
    ip = request.remote_addr or ""

    user = get_current_user_from_request(request)
    user_id = user["id"] if user else None
    user_identifier = user["identifier"] if user else "Anonymous Visitor"

    log_user_activity(
        user_id=user_id,
        user_identifier=user_identifier,
        article_title=article_title or "Direct Article Visit",
        article_url=article_url or "Unknown URL",
        category=category,
        ip_address=ip
    )
    return jsonify({"success": True})

@news_bp.route("/saved", methods=["GET"])
def get_saved():
    """Fetch saved news for logged-in user."""
    user = get_current_user_from_request(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized. Please log in."}), 401

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, article_url AS url, title, description, image, source, published_at, category, saved_at
            FROM saved_articles
            WHERE user_id = ?
            ORDER BY saved_at DESC
        """, (user["id"],))
        rows = [dict(r) for r in cursor.fetchall()]

    for r in rows:
        r["is_saved"] = True

    return jsonify({"success": True, "count": len(rows), "articles": rows})

@news_bp.route("/save", methods=["POST"])
def toggle_save():
    """Save or unsave an article for logged-in user."""
    user = get_current_user_from_request(request)
    if not user:
        return jsonify({"success": False, "message": "Please log in to save articles."}), 401

    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    action = data.get("action", "toggle").lower()  # 'save', 'unsave', 'toggle'

    if not url:
        return jsonify({"success": False, "message": "Article URL is required."}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM saved_articles WHERE user_id = ? AND article_url = ?", (user["id"], url))
        existing = cursor.fetchone()

        if action == "unsave" or (action == "toggle" and existing):
            cursor.execute("DELETE FROM saved_articles WHERE user_id = ? AND article_url = ?", (user["id"], url))
            return jsonify({"success": True, "saved": False, "message": "Article removed from saved."})
        else:
            # Need to save: fetch info or use supplied payload
            title = data.get("title", "Saved Article").strip()
            description = data.get("description", "").strip()
            image = data.get("image", "").strip()
            source = data.get("source", "News").strip()
            published_at = data.get("published_at", "").strip()
            category = data.get("category", "General").strip()
            now = time.time()

            cursor.execute("""
                INSERT OR REPLACE INTO saved_articles 
                (user_id, article_url, title, description, image, source, published_at, category, saved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user["id"], url, title, description, image, source, published_at, category, now))

            return jsonify({"success": True, "saved": True, "message": "Article saved successfully."})
