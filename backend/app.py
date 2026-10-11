import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.models.database import init_db
from backend.routes import auth_bp, news_bp, summarizer_bp, admin_bp

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

def create_app():
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/")
    app.config.from_object(Config)

    # Enable CORS for local development and API access
    CORS(app, supports_credentials=True)

    # Initialize Database
    init_db()

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(summarizer_bp)
    app.register_blueprint(admin_bp)

    # Serve Frontend Pages & Static Files
    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/home")
    @app.route("/home.html")
    def home_page():
        return send_from_directory(FRONTEND_DIR, "home.html")

    @app.route("/article")
    @app.route("/article.html")
    def article_page():
        return send_from_directory(FRONTEND_DIR, "article.html")

    @app.route("/css/<path:path>")
    def send_css(path):
        return send_from_directory(FRONTEND_DIR / "css", path)

    @app.route("/js/<path:path>")
    def send_js(path):
        return send_from_directory(FRONTEND_DIR / "js", path)

    @app.route("/assets/<path:path>")
    def send_assets(path):
        return send_from_directory(FRONTEND_DIR / "assets", path)

    # Security & Performance Headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # Global Error Handlers
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"error": "Resource not found", "status": 404}), 404

    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({"error": "Internal server error", "status": 500}), 500

    return app

if __name__ == "__main__":
    app = create_app()
    print(f"\n=======================================================")
    print(f" AI NEWS LETTER SERVER RUNNING")
    print(f" URL: http://localhost:{Config.PORT}")
    print(f" Start Page: http://localhost:{Config.PORT}/")
    print(f" Main Page:  http://localhost:{Config.PORT}/home.html")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
