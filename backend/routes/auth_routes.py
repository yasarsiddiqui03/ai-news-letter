import time
from datetime import datetime, timezone
import jwt
from flask import Blueprint, request, jsonify, make_response
from backend.config import Config
from backend.models.database import get_db
from backend.services.otp_service import request_otp, verify_otp_code, validate_identifier

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

def get_current_user_from_request(req) -> dict | None:
    """Extract authenticated user from cookie or Authorization header."""
    token = req.cookies.get("auth_token")
    auth_header = req.headers.get("Authorization")
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if not token:
        return None

    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            return None

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, type, identifier, created_at, last_login_at FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception:
        return None

@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    """Request OTP for signup or login."""
    data = request.get_json(silent=True) or {}
    id_type = data.get("type", "").strip().lower()
    identifier = data.get("identifier", "").strip()
    purpose = data.get("purpose", "").strip().lower()

    if id_type not in ("phone", "email"):
        return jsonify({"success": False, "message": "Type must be 'phone' or 'email'."}), 400

    if purpose not in ("signup", "login"):
        return jsonify({"success": False, "message": "Purpose must be 'signup' or 'login'."}), 400

    ip = request.remote_addr or ""
    result = request_otp(id_type, identifier, purpose, ip_address=ip)
    status_code = 200 if result["success"] else 400
    if not result["success"] and "Account not found" in result.get("message", ""):
        status_code = 404
    return jsonify(result), status_code

@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP and authenticate user."""
    data = request.get_json(silent=True) or {}
    id_type = data.get("type", "").strip().lower()
    raw_identifier = data.get("identifier", "").strip()
    otp = str(data.get("otp", "")).strip()
    purpose = data.get("purpose", "").strip().lower()

    if id_type not in ("phone", "email") or not raw_identifier or not otp:
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    is_valid, identifier = validate_identifier(id_type, raw_identifier)
    if not is_valid:
        return jsonify({"success": False, "message": f"Invalid {id_type} format."}), 400

    verify_res = verify_otp_code(identifier, otp, purpose)
    if not verify_res["success"]:
        return jsonify(verify_res), 400

    now_ts = time.time()
    now_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    user_data = None
    with get_db() as conn:
        cursor = conn.cursor()
        if purpose == "signup":
            cursor.execute("""
                INSERT INTO users (type, identifier, created_at, last_login_at)
                VALUES (?, ?, ?, ?)
            """, (id_type, identifier, now_dt, now_dt))
            user_id = cursor.lastrowid
        else:
            cursor.execute("SELECT id FROM users WHERE identifier = ?", (identifier,))
            existing = cursor.fetchone()
            if not existing:
                return jsonify({"success": False, "message": "Account not found, please sign up."}), 404
            user_id = existing["id"]
            cursor.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_dt, user_id))

        cursor.execute("SELECT id, type, identifier, created_at, last_login_at FROM users WHERE id = ?", (user_id,))
        user_data = dict(cursor.fetchone())

    # Issue persistent JWT token (7 days expiry)
    exp_time = int(now_ts + (Config.JWT_EXPIRY_DAYS * 86400))
    token_payload = {
        "user_id": user_data["id"],
        "identifier": user_data["identifier"],
        "type": user_data["type"],
        "exp": exp_time
    }
    jwt_token = jwt.encode(token_payload, Config.JWT_SECRET, algorithm="HS256")

    response = make_response(jsonify({
        "success": True,
        "message": "Authentication successful.",
        "token": jwt_token,
        "user": user_data
    }))

    # Set secure persistent httpOnly cookie
    response.set_cookie(
        "auth_token",
        jwt_token,
        max_age=Config.JWT_EXPIRY_DAYS * 86400,
        httponly=True,
        samesite="Lax",
        secure=False  # Set True in strict HTTPS production
    )
    return response

@auth_bp.route("/me", methods=["GET"])
def me():
    """Retrieve current logged in user."""
    user = get_current_user_from_request(request)
    if not user:
        return jsonify({"authenticated": False, "user": None}), 200
    return jsonify({"authenticated": True, "user": user}), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Log out user and clear cookie."""
    resp = make_response(jsonify({"success": True, "message": "Logged out successfully."}))
    resp.delete_cookie("auth_token")
    return resp
