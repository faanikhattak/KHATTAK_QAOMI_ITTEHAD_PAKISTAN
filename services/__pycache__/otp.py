##### new claud



from services.database.db import supabase
import threading

# ================================================================
#  otp.py  –  OTP Management
#  ─────────────────────────────────────────────────────────────
#  یہ فائل Email OTP کا انتظام کرتی ہے۔
#  Supabase built-in email OTP استعمال کرتی ہے — کوئی extra
#  service درکار نہیں۔
#
#  Functions:
#   • send_signup_otp()    → Registration OTP بھیجنا
#   • send_recovery_otp()  → Password reset OTP بھیجنا
#   • verify_signup_otp()  → Registration OTP تصدیق
#   • verify_recovery_otp()→ Password reset OTP تصدیق
#   • resend_otp()         → OTP دوبارہ بھیجنا
#   • set_new_password()   → نیا پاس ورڈ سیٹ کرنا
# ================================================================


# ── Registration OTP بھیجنا ───────────────────────────────────
def send_signup_otp(email: str, password: str) -> tuple[bool, str, str]:
    """
    نئے user کو Email OTP بھیجتا ہے۔
    Supabase خود OTP generate کرتا اور email بھیجتا ہے۔

    Parameters:
      email    → user کی ای میل
      password → user کا پاس ورڈ

    Returns:
      (success: bool, user_id: str, error_msg: str)
      کامیاب ہو تو → (True, "uuid", "")
      ناکام ہو تو  → (False, "", "error message")
    """
    try:
        res = supabase.auth.sign_up({
            "email":    email.strip(),
            "password": password,
        })

        if res and res.user:
            return True, res.user.id, ""
        else:
            return False, "", "Account not created | اکاؤنٹ نہیں بن سکا"

    except Exception as err:
        return False, "", _parse_error(err)


# ── Registration OTP تصدیق ────────────────────────────────────
def verify_signup_otp(email: str, otp_code: str) -> tuple[bool, str]:
    """
    Registration OTP تصدیق کرتا ہے۔

    Parameters:
      email    → وہی ای میل جہاں OTP گیا
      otp_code → 6 ہندسے OTP

    Returns:
      (success: bool, error_msg: str)
    """
    try:
        res = supabase.auth.verify_otp({
            "email": email.strip(),
            "token": otp_code.strip(),
            "type":  "signup",
        })

        if res and res.user:
            # profiles میں email_verified = True کریں
            _update_verified(email)
            return True, ""
        else:
            return False, "Wrong OTP | OTP غلط ہے"

    except Exception as err:
        return False, _parse_error(err)


# ── Password Reset OTP بھیجنا ─────────────────────────────────
def send_recovery_otp(email: str) -> tuple[bool, str]:
    """
    پاس ورڈ reset کے لیے OTP بھیجتا ہے۔

    Returns:
      (success: bool, error_msg: str)
    """
    try:
        supabase.auth.reset_password_email(email.strip())
        return True, ""
    except Exception as err:
        return False, _parse_error(err)


# ── Password Reset OTP تصدیق ──────────────────────────────────
def verify_recovery_otp(email: str, otp_code: str) -> tuple[bool, str]:
    """
    Password reset OTP تصدیق کرتا ہے۔

    Returns:
      (success: bool, error_msg: str)
    """
    try:
        res = supabase.auth.verify_otp({
            "email": email.strip(),
            "token": otp_code.strip(),
            "type":  "recovery",
        })

        if res and res.session:
            return True, ""
        else:
            return False, "Wrong OTP | OTP غلط ہے"

    except Exception as err:
        return False, _parse_error(err)


# ── نیا پاس ورڈ سیٹ کرنا ─────────────────────────────────────
def set_new_password(new_password: str) -> tuple[bool, str]:
    """
    OTP تصدیق کے بعد نیا پاس ورڈ سیٹ کرتا ہے۔
    (verify_recovery_otp کے بعد call کریں)

    Returns:
      (success: bool, error_msg: str)
    """
    try:
        res = supabase.auth.update_user({"password": new_password})
        if res and res.user:
            return True, ""
        else:
            return False, "Password not updated | پاس ورڈ نہیں بدلا"
    except Exception as err:
        return False, _parse_error(err)


# ── OTP دوبارہ بھیجنا ─────────────────────────────────────────
def resend_otp(email: str) -> tuple[bool, str]:
    """
    OTP دوبارہ بھیجتا ہے (اگر expire ہو گیا ہو)۔

    Returns:
      (success: bool, error_msg: str)
    """
    try:
        supabase.auth.resend({
            "type":  "signup",
            "email": email.strip(),
        })
        return True, ""
    except Exception as err:
        return False, _parse_error(err)


# ── profiles میں email_verified = True ───────────────────────
def _update_verified(email: str) -> None:
    """
    OTP تصدیق کے بعد profiles table میں
    email_verified کو True کرتا ہے۔
    Background thread میں چلتا ہے۔
    """
    def _work():
        try:
            supabase.table("profiles").update(
                {"email_verified": True}
            ).eq("email", email.strip()).execute()
        except Exception as err:
            print(f"[OTP VERIFY UPDATE ERROR] {err}")

    threading.Thread(target=_work, daemon=True).start()


# ── Error message parsing ─────────────────────────────────────
def _parse_error(err: Exception) -> str:
    """
    Supabase error کو صارف دوست پیغام میں بدلتا ہے۔
    اردو اور انگریزی دونوں میں۔
    """
    msg = str(err).lower()

    if "already registered" in msg or "already exists" in msg or "duplicate" in msg:
        return "Email already registered | یہ ای میل پہلے سے رجسٹرڈ ہے!"

    if "invalid" in msg and ("otp" in msg or "token" in msg):
        return "Wrong OTP | OTP غلط ہے!"

    if "expired" in msg or "otp" in msg:
        return "OTP expired | OTP کی میعاد ختم ہو گئی — دوبارہ بھیجیں"

    if "password" in msg and "weak" in msg:
        return "Weak password | پاس ورڈ بہت آسان ہے!"

    if "user not found" in msg or "no user" in msg:
        return "User not found | صارف موجود نہیں!"

    if "rate" in msg or "limit" in msg:
        return "Too many attempts | بہت زیادہ کوششیں — کچھ دیر بعد آزمائیں"

    if "network" in msg or "connect" in msg:
        return "Check internet | انٹرنیٹ کنکشن چیک کریں"

    if "email" in msg and "invalid" in msg:
        return "Invalid email | ای میل غلط ہے!"

    # Default — مکمل error اردو میں
    return f"Error | خرابی: {str(err)[:80]}"
