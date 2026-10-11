import io
import base64
import time
import bcrypt
import pyotp
import qrcode
from backend.config import Config
from backend.models.database import get_db

def verify_admin_credentials(admin_id: str, password: str) -> bool:
    """Validate Admin ID and bcrypt-hashed password."""
    if admin_id.strip() != Config.ADMIN_ID:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), Config.ADMIN_PASSWORD_HASH.encode("utf-8"))
    except Exception as e:
        print(f"[Admin Auth Error] {e}")
        return False

def verify_admin_totp(code: str) -> bool:
    """Verify 6-digit TOTP code against ADMIN_TOTP_SECRET with 1-step window."""
    code_clean = str(code).strip()
    if not code_clean or len(code_clean) != 6:
        return False
    totp = pyotp.TOTP(Config.ADMIN_TOTP_SECRET)
    return totp.verify(code_clean, valid_window=1)

def get_totp_setup_info() -> dict:
    """Generate TOTP provisioning URI and QR Code data URL."""
    totp = pyotp.TOTP(Config.ADMIN_TOTP_SECRET)
    provisioning_uri = totp.provisioning_uri(
        name=Config.ADMIN_ID,
        issuer_name="AI News Letter"
    )

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_data_url = f"data:image/png;base64,{qr_b64}"

    return {
        "secret": Config.ADMIN_TOTP_SECRET,
        "provisioning_uri": provisioning_uri,
        "qr_code_url": qr_data_url
    }

def log_user_activity(user_id: int | None, user_identifier: str, article_title: str, article_url: str, category: str = "", ip_address: str = ""):
    """Record an article view activity in DB."""
    now = time.time()
    identifier = user_identifier or "Anonymous Visitor"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_activity 
            (user_id, user_identifier, article_title, article_url, category, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, identifier, article_title, article_url, category, ip_address, now))

def get_registered_users_list() -> list[dict]:
    """Retrieve all registered users with phone/email, signup date, last login."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, type, identifier, created_at, last_login_at
            FROM users
            ORDER BY created_at DESC
        """)
        return [dict(r) for r in cursor.fetchall()]

def get_activity_logs(search_query: str = "", limit: int = 200) -> list[dict]:
    """Retrieve user activity logs with optional search filter."""
    with get_db() as conn:
        cursor = conn.cursor()
        if search_query.strip():
            pattern = f"%{search_query.strip()}%"
            cursor.execute("""
                SELECT id, user_id, user_identifier, article_title, article_url, category, ip_address, timestamp
                FROM user_activity
                WHERE user_identifier LIKE ? OR article_title LIKE ? OR article_url LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (pattern, pattern, pattern, limit))
        else:
            cursor.execute("""
                SELECT id, user_id, user_identifier, article_title, article_url, category, ip_address, timestamp
                FROM user_activity
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
