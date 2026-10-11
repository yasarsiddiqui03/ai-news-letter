import time
from functools import wraps
import jwt
from flask import Blueprint, request, jsonify, make_response
from backend.config import Config
from backend.services.admin_service import (
    verify_admin_credentials,
    verify_admin_totp,
    get_totp_setup_info,
    get_registered_users_list,
    get_activity_logs
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif request.cookies.get("admin_token"):
            token = request.cookies.get("admin_token")

        if not token:
            return jsonify({"success": False, "message": "This section is restricted to administrators."}), 403

        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            if not payload.get("is_admin"):
                return jsonify({"success": False, "message": "This section is restricted to administrators."}), 403
        except Exception:
            return jsonify({"success": False, "message": "Session expired or invalid. Please re-authenticate."}), 403

        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route("/login", methods=["POST"])
def admin_login():
    """Step 1 of admin authentication: Validate ID and password."""
    data = request.get_json(silent=True) or {}
    admin_id = data.get("admin_id", "").strip()
    password = data.get("password", "")

    if not admin_id or not password:
        return jsonify({"success": False, "message": "Admin ID and Password are required."}), 400

    if not verify_admin_credentials(admin_id, password):
        return jsonify({"success": False, "message": "Invalid credentials."}), 401

    # Issue temporary token for 2FA step (expires in 5 minutes)
    temp_payload = {
        "admin_step": "totp",
        "admin_id": admin_id,
        "exp": int(time.time() + 300)
    }
    temp_token = jwt.encode(temp_payload, Config.JWT_SECRET, algorithm="HS256")

    return jsonify({
        "success": True,
        "require_2fa": True,
        "temp_token": temp_token,
        "message": "Password verified. Please enter the 6-digit code from your Authenticator app."
    })

@admin_bp.route("/verify-2fa", methods=["POST"])
def admin_verify_2fa():
    """Step 2 of admin authentication: Validate TOTP code."""
    data = request.get_json(silent=True) or {}
    temp_token = data.get("temp_token", "").strip()
    totp_code = str(data.get("totp_code", "")).strip()

    if not temp_token or not totp_code:
        return jsonify({"success": False, "message": "Temporary token and 2FA code are required."}), 400

    try:
        payload = jwt.decode(temp_token, Config.JWT_SECRET, algorithms=["HS256"])
        if payload.get("admin_step") != "totp":
            return jsonify({"success": False, "message": "Invalid authentication step."}), 400
    except Exception:
        return jsonify({"success": False, "message": "2FA session expired. Please start over."}), 401

    if not verify_admin_totp(totp_code):
        return jsonify({"success": False, "message": "Invalid 2FA code. Please check your Authenticator app."}), 401

    # Issue persistent Admin JWT (valid 24 hours)
    admin_payload = {
        "is_admin": True,
        "admin_id": Config.ADMIN_ID,
        "exp": int(time.time() + 86400)
    }
    admin_token = jwt.encode(admin_payload, Config.JWT_SECRET, algorithm="HS256")

    resp = make_response(jsonify({
        "success": True,
        "message": "Admin authentication successful.",
        "admin_token": admin_token
    }))

    resp.set_cookie(
        "admin_token",
        admin_token,
        max_age=86400,
        httponly=True,
        samesite="Lax",
        secure=False
    )
    return resp

@admin_bp.route("/setup-2fa", methods=["GET"])
def setup_2fa():
    """Public helper endpoint showing TOTP QR code & manual key for Google Authenticator."""
    info = get_totp_setup_info()
    return jsonify({
        "success": True,
        "secret": info["secret"],
        "provisioning_uri": info["provisioning_uri"],
        "qr_code_url": info["qr_code_url"],
        "instructions": "Scan this QR code in Google Authenticator or enter the secret key manually."
    })

@admin_bp.route("/check", methods=["GET"])
def admin_check():
    """Verify if user has active admin session."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif request.cookies.get("admin_token"):
        token = request.cookies.get("admin_token")

    if not token:
        return jsonify({"is_admin": False}), 200

    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        if payload.get("is_admin"):
            return jsonify({"is_admin": True, "admin_id": payload.get("admin_id")}), 200
    except Exception:
        pass
    return jsonify({"is_admin": False}), 200

@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    """Admin Dashboard: List all registered users."""
    users = get_registered_users_list()
    return jsonify({
        "success": True,
        "count": len(users),
        "users": users
    })

@admin_bp.route("/activity", methods=["GET"])
@admin_required
def get_activity():
    """Admin Dashboard: View tracked user activity with live search."""
    q = request.args.get("q", "").strip()
    logs = get_activity_logs(search_query=q, limit=200)
    return jsonify({
        "success": True,
        "count": len(logs),
        "activity": logs
    })

@admin_bp.route("/logout", methods=["POST"])
def admin_logout():
    """Log out admin."""
    resp = make_response(jsonify({"success": True, "message": "Admin session terminated."}))
    resp.delete_cookie("admin_token")
    return resp
