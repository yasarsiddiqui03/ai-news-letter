import sqlite3
import threading
from contextlib import contextmanager
from backend.config import Config

_local = threading.local()

def get_connection():
    """Get a thread-local SQLite connection with row_factory enabled."""
    if not hasattr(_local, "connection") or _local.connection is None:
        Config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(Config.DATABASE_PATH),
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        _local.connection = conn
    return _local.connection

@contextmanager
def get_db():
    """Context manager for database transactions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def init_db():
    """Initialize SQLite tables and indexes."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('phone', 'email')),
                identifier TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # OTPs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,
                hashed_otp TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                purpose TEXT NOT NULL CHECK(purpose IN ('signup', 'login')),
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                ip_address TEXT
            );
        """)

        # Articles Cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                image TEXT,
                source TEXT,
                published_at TEXT,
                category TEXT NOT NULL,
                fetched_at REAL NOT NULL
            );
        """)

        # Seen Articles per session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                article_url TEXT NOT NULL,
                seen_at REAL NOT NULL,
                UNIQUE(session_id, article_url)
            );
        """)

        # Saved Articles for users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                article_url TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                image TEXT,
                source TEXT,
                published_at TEXT,
                category TEXT NOT NULL,
                saved_at REAL NOT NULL,
                UNIQUE(user_id, article_url),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # Summaries Cache (for fast reuse and quota savings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT NOT NULL UNIQUE,
                headline TEXT NOT NULL,
                bullets TEXT NOT NULL,
                paragraph TEXT NOT NULL,
                created_at REAL NOT NULL
            );
        """)

        # User Activity for Admin tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_identifier TEXT,
                article_title TEXT,
                article_url TEXT,
                category TEXT,
                ip_address TEXT,
                timestamp REAL NOT NULL
            );
        """)

        # Performance Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_identifier ON users(identifier);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_otps_identifier ON otps(identifier);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_seen_session ON seen_articles(session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles_cache(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles_cache(fetched_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_saved_user ON saved_articles(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_time ON user_activity(timestamp DESC);")
