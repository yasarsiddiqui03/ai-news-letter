import re
import secrets
import hashlib
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import phonenumbers
from backend.config import Config
from backend.models.database import get_db

OTP_SALT = "ai-news-letter-otp-salt-secure"

def validate_identifier(id_type: str, identifier: str) -> tuple[bool, str]:
    """Validate phone or email format. Returns (is_valid, normalized_identifier)."""
    identifier = identifier.strip()
    if id_type == "phone":
        try:
            parsed = phonenumbers.parse(identifier, None)
            if not phonenumbers.is_valid_number(parsed):
                return False, ""
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return True, formatted
        except Exception:
            # Fallback regex for standard E.164
            if re.match(r"^\+[1-9]\d{6,14}$", identifier):
                return True, identifier
            return False, ""
    elif id_type == "email":
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if re.match(pattern, identifier):
            return True, identifier.lower()
        return False, ""
    return False, ""

def hash_otp(otp: str) -> str:
    """Hash OTP using SHA-256 with server-side salt."""
    return hashlib.sha256(f"{OTP_SALT}:{otp}".encode("utf-8")).hexdigest()

def send_twilio_sms(to_phone: str, otp: str) -> bool:
    """Send SMS via Twilio API."""
    if not (Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN and Config.TWILIO_PHONE_NUMBER):
        return False
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{Config.TWILIO_ACCOUNT_SID}/Messages.json"
        response = requests.post(
            url,
            auth=(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN),
            data={
                "From": Config.TWILIO_PHONE_NUMBER,
                "To": to_phone,
                "Body": f"Your AI NEWS LETTER verification code is: {otp}. Valid for 5 minutes."
            },
            timeout=10
        )
        return response.status_code in (200, 201)
    except Exception as e:
        print(f"[Twilio Error] Failed to send SMS: {e}")
def send_fast2sms_otp(to_phone: str, otp: str) -> bool:
    """Send real SMS via Fast2SMS to Indian mobile numbers."""
    if not Config.FAST2SMS_API_KEY:
        return False
    try:
        clean_num = to_phone.replace("+91", "").replace(" ", "").replace("-", "").strip()
        if len(clean_num) != 10:
            return False
        url = "https://www.fast2sms.com/dev/bulkV2"
        params = {
            "authorization": Config.FAST2SMS_API_KEY,
            "route": "otp",
            "variables_values": otp,
            "flash": "0",
            "numbers": clean_num
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json() if resp.status_code == 200 else {}
        return data.get("return", False) is True or resp.status_code == 200
    except Exception as e:
        print(f"[Fast2SMS Error] Failed to send SMS: {e}")
        return False

def send_smtp_email(to_email: str, otp: str) -> bool:
    """Send OTP via SMTP."""
    if not (Config.SMTP_USER and Config.SMTP_PASS):
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your AI NEWS LETTER OTP: {otp}"
        msg["From"] = Config.SMTP_FROM or Config.SMTP_USER
        msg["To"] = to_email

        text = f"Your verification code for AI NEWS LETTER is: {otp}. It is valid for 5 minutes."
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; padding: 20px; border-radius: 8px; background: #0f172a; color: #f8fafc;">
            <h2 style="color: #38bdf8; margin-top: 0;">AI NEWS LETTER</h2>
            <p style="font-size: 15px; color: #cbd5e1;">Your single-use verification code is:</p>
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 6px; padding: 16px; background: #1e293b; color: #38bdf8; text-align: center; border-radius: 6px; margin: 20px 0;">
                {otp}
            </div>
            <p style="font-size: 13px; color: #94a3b8;">This code expires in 5 minutes. If you did not request this code, please ignore this email.</p>
        </div>
        """
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASS)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[SMTP Error] Failed to send email: {e}")
        return False

def request_otp(id_type: str, identifier: str, purpose: str, ip_address: str = "") -> dict:
    """
    Generate and dispatch OTP adhering to strict cooldown, rate-limit, and user existence rules.
    """
    is_valid, normalized_id = validate_identifier(id_type, identifier)
    if not is_valid:
        return {"success": False, "message": f"Invalid {id_type} format. Please provide a valid {id_type}."}

    now = time.time()

    with get_db() as conn:
        cursor = conn.cursor()

        # Check user existence against purpose
        cursor.execute("SELECT id FROM users WHERE identifier = ?", (normalized_id,))
        user_row = cursor.fetchone()

        if purpose == "login" and not user_row:
            return {"success": False, "message": "Account not found, please sign up."}
        if purpose == "signup" and user_row:
            return {"success": False, "message": "Account already exists, please log in."}

        # Check 30-second resend cooldown
        cursor.execute("""
            SELECT created_at FROM otps 
            WHERE identifier = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (normalized_id,))
        last_otp = cursor.fetchone()
        if last_otp and (now - last_otp["created_at"]) < 30:
            remaining = int(30 - (now - last_otp["created_at"]))
            return {
                "success": False,
                "message": f"Please wait {remaining} seconds before requesting a new OTP."
            }

        # Rate limit per identifier (max 5 requests per 10 minutes)
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM otps 
            WHERE identifier = ? AND created_at > ?
        """, (normalized_id, now - 600))
        if cursor.fetchone()["cnt"] >= 5:
            return {
                "success": False,
                "message": "Too many OTP requests. Please wait 10 minutes and try again."
            }

        # Generate 6-digit OTP
        otp = f"{secrets.randbelow(900000) + 100000}"
        hashed = hash_otp(otp)
        expires_at = now + 300  # 5 minutes

        # Invalidate old OTPs for this identifier
        cursor.execute("DELETE FROM otps WHERE identifier = ?", (normalized_id,))

        cursor.execute("""
            INSERT INTO otps (identifier, hashed_otp, attempts, purpose, created_at, expires_at, ip_address)
            VALUES (?, ?, 0, ?, ?, ?, ?)
        """, (normalized_id, hashed, purpose, now, expires_at, ip_address))

    # Send delivery
    delivery_ok = False
    delivery_channel = "Console"
    if id_type == "phone":
        if Config.FAST2SMS_API_KEY:
            delivery_ok = send_fast2sms_otp(normalized_id, otp)
            if delivery_ok:
                delivery_channel = "Fast2SMS (Mobile SMS)"
        if not delivery_ok and Config.TWILIO_ACCOUNT_SID:
            delivery_ok = send_twilio_sms(normalized_id, otp)
            if delivery_ok:
                delivery_channel = "Twilio (Mobile SMS)"
    else:
        delivery_ok = send_smtp_email(normalized_id, otp)
        if delivery_ok:
            delivery_channel = "SMTP (Email Inbox)"

    # Always log for local development & seamless testing
    print(f"\n==================================================")
    print(f" [OTP DISPATCHED] Purpose: {purpose.upper()}")
    print(f" Target: {normalized_id} ({id_type})")
    print(f" Verification Code: >>> {otp} <<< (Expires in 5 mins)")
    print(f" Delivery Channel: {delivery_channel} | Success: {delivery_ok}")
    print(f"==================================================\n")

    if delivery_ok:
        msg = f"Verification code sent directly to your {id_type} ({normalized_id}) via {delivery_channel}."
    else:
        msg = f"Verification code generated. (Configure FAST2SMS_API_KEY or SMTP credentials in .env to receive actual SMS/Email)."

    res = {
        "success": True,
        "message": msg,
        "identifier": normalized_id,
        "cooldown": 30,
        "delivery_ok": delivery_ok
    }
    # In dev mode or when real SMS/SMTP is not configured, provide dev_otp for automated testing & smooth UI
    if Config.DEV_MODE or not delivery_ok:
        res["dev_otp"] = otp

    return res

def verify_otp_code(identifier: str, entered_otp: str, purpose: str) -> dict:
    """
    Verify OTP with 5 attempts max, 5-minute expiry, and hashing.
    """
    now = time.time()
    entered_otp = str(entered_otp).strip()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, hashed_otp, attempts, purpose, expires_at 
            FROM otps 
            WHERE identifier = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (identifier,))
        otp_row = cursor.fetchone()

        if not otp_row:
            return {"success": False, "message": "No active verification code found. Please request a new one."}

        if otp_row["purpose"] != purpose:
            return {"success": False, "message": "Invalid purpose for this code."}

        if now > otp_row["expires_at"]:
            cursor.execute("DELETE FROM otps WHERE id = ?", (otp_row["id"],))
            return {"success": False, "message": "Verification code has expired. Please request a new code."}

        if otp_row["attempts"] >= 5:
            cursor.execute("DELETE FROM otps WHERE id = ?", (otp_row["id"],))
            return {"success": False, "message": "Maximum verification attempts exceeded. Please request a new code."}

        # Check hash
        if hash_otp(entered_otp) != otp_row["hashed_otp"]:
            new_attempts = otp_row["attempts"] + 1
            cursor.execute("UPDATE otps SET attempts = ? WHERE id = ?", (new_attempts, otp_row["id"]))
            remaining = 5 - new_attempts
            if remaining <= 0:
                cursor.execute("DELETE FROM otps WHERE id = ?", (otp_row["id"],))
                return {"success": False, "message": "Too many failed attempts. Code has been invalidated."}
            return {"success": False, "message": f"Incorrect code. {remaining} attempt(s) remaining."}

        # Code matched successfully! Delete OTP so it cannot be reused
        cursor.execute("DELETE FROM otps WHERE id = ?", (otp_row["id"],))
        return {"success": True, "message": "Code verified successfully."}
