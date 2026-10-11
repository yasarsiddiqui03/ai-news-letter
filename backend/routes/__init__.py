from .auth_routes import auth_bp
from .news_routes import news_bp
from .summarizer_routes import summarizer_bp
from .admin_routes import admin_bp

__all__ = ["auth_bp", "news_bp", "summarizer_bp", "admin_bp"]
