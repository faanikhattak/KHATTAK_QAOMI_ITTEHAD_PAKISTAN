import requests
import json

# ================================================================
#  firebase_otp.py  –  Firebase Phone OTP Service
#  ─────────────────────────────────────────────────────────────
#  یہ فائل Firebase سے phone OTP بھیجتی اور verify کرتی ہے
#
#  Setup:
#   1. console.firebase.google.com → project بنائیں
#   2. Authentication → Sign-in method → Phone → Enable
#   3. Project Settings → General → Web API Key copy کریں
#   4. نیچے FIREBASE_API_KEY میں لکھیں
#
#  Functions:
#   • send_otp()    → phone پر OTP بھیجنا
#   • verify_otp()  → OTP تصدیق کرنا
# ================================================================
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# NOTE: load_dotenv() with no path relies on searching upward from the
# current working directory, which is unreliable inside the packaged
# Android app. Point it explicitly at the project-root .env instead —
# this file lives at <root>/services/firebase/firebase_otp.py.
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

FIREBASE_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")



# ── Firebase REST API URLs ─────────────────────────────────────
SEND_OTP_URL   = f"https://identitytoolkit.googleapis.com/v1/accounts:sendVerificationCode?key={FIREBASE_API_KEY}"
VERIFY_OTP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPhoneNumber?key={FIREBASE_API_KEY}"


def normalize_phone(raw: str) -> str:
    """
    Pakistan فون نمبر کو +92 format میں بدلنا
    03001234567  →  +923001234567
    """
    raw = (raw or "").strip()
    if raw.startswith("0"):
        return "+92" + raw[1:]
    if raw.startswith("92") and not raw.startswith("+"):
        return "+" + raw
    return raw


def send_otp(phone: str) -> tuple[bool, str, str]:
    """
    Firebase سے phone پر OTP بھیجنا

    Parameters:
      phone → فون نمبر (03xxxxxxxxx یا +923xxxxxxxxx)

    Returns:
      (success, session_info, error_msg)
      کامیاب → (True, "session_token", "")
      ناکام  → (False, "", "error message")

    Note:
      session_info کو محفوظ رکھیں — verify_otp میں چاہیے
    """
    phone = normalize_phone(phone)

    try:
        response = requests.post(
            SEND_OTP_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "phoneNumber":          phone,
            }),
            timeout=15,
        )

        data = response.json()

        # ── کامیاب ──
        if "sessionInfo" in data:
            return True, data["sessionInfo"], ""

        # ── Firebase error ──
        error = data.get("error", {})
        return False, "", _parse_firebase_error(error)

    except requests.exceptions.Timeout:
        return False, "", "Timeout | انٹرنیٹ slow ہے — دوبارہ کوشش کریں"
    except requests.exceptions.ConnectionError:
        return False, "", "No internet | انٹرنیٹ کنکشن چیک کریں"
    except Exception as err:
        return False, "", f"Error: {str(err)[:60]}"


def verify_otp(session_info: str, otp_code: str) -> tuple[bool, str, str]:
    """
    Firebase OTP تصدیق کرنا

    Parameters:
      session_info → send_otp سے ملا token
      otp_code     → user کا 6 ہندسہ OTP

    Returns:
      (success, phone_number, error_msg)
      کامیاب → (True, "+923001234567", "")
      ناکام  → (False, "", "error message")
    """
    try:
        response = requests.post(
            VERIFY_OTP_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "sessionInfo": session_info,
                "code":        otp_code.strip(),
            }),
            timeout=15,
        )

        data = response.json()

        # ── کامیاب ──
        if "localId" in data or "idToken" in data:
            phone = data.get("phoneNumber", "")
            return True, phone, ""

        # ── Firebase error ──
        error = data.get("error", {})
        return False, "", _parse_firebase_error(error)

    except requests.exceptions.Timeout:
        return False, "", "Timeout | انٹرنیٹ slow ہے"
    except requests.exceptions.ConnectionError:
        return False, "", "No internet | انٹرنیٹ چیک کریں"
    except Exception as err:
        return False, "", f"Error: {str(err)[:60]}"


def _parse_firebase_error(error: dict) -> str:
    """
    Firebase error کو اردو/انگریزی میں بدلنا
    """
    code = error.get("message", "").upper()

    errors = {
        "INVALID_CODE":
            "⚠ Wrong OTP | OTP غلط ہے!",
        "SESSION_EXPIRED":
            "⚠ OTP expired | OTP کی میعاد ختم — دوبارہ بھیجیں",
        "TOO_MANY_ATTEMPTS_TRY_LATER":
            "⚠ Too many attempts | بہت زیادہ کوششیں — کچھ دیر بعد کوشش کریں",
        "INVALID_PHONE_NUMBER":
            "⚠ Invalid phone | فون نمبر غلط ہے! (+923xxxxxxxxx)",
        "QUOTA_EXCEEDED":
            "⚠ SMS limit reached | آج کی SMS limit ختم ہو گئی",
        "CAPTCHA_CHECK_FAILED":
            "⚠ reCAPTCHA failed | Firebase testing mode enable کریں",
        "MISSING_CLIENT_IDENTIFIER":
            "⚠ Firebase config error | API Key چیک کریں",
        "INVALID_SESSION_INFO":
            "⚠ Session expired | دوبارہ OTP بھیجیں",
        "CODE_EXPIRED":
            "⚠ OTP expired | OTP پرانا ہو گیا — دوبارہ بھیجیں",
        "API_KEY_INVALID":
            "⚠ Invalid API Key | Firebase API Key غلط ہے!",
    }

    for key, msg in errors.items():
        if key in code:
            return msg

    return f"⚠ Firebase Error: {code[:60]}"



























# import requests
# import json

# # ================================================================
# #  firebase_otp.py  –  Firebase Phone OTP Service
# #  ─────────────────────────────────────────────────────────────
# #  یہ فائل Firebase سے phone OTP بھیجتی اور verify کرتی ہے
# #
# #  Setup:
# #   1. console.firebase.google.com → project بنائیں
# #   2. Authentication → Sign-in method → Phone → Enable
# #   3. Project Settings → General → Web API Key copy کریں
# #   4. نیچے FIREBASE_API_KEY میں لکھیں
# #
# #  Functions:
# #   • send_otp()    → phone پر OTP بھیجنا
# #   • verify_otp()  → OTP تصدیق کرنا
# # ================================================================
# import os
# import requests
# from dotenv import load_dotenv




# # load_dotenv()

# # FIREBASE_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
# # PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")



# # ── Firebase REST API URLs ─────────────────────────────────────
# SEND_OTP_URL   = f"https://identitytoolkit.googleapis.com/v1/accounts:sendVerificationCode?key={FIREBASE_API_KEY}"
# VERIFY_OTP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPhoneNumber?key={FIREBASE_API_KEY}"


# def normalize_phone(raw: str) -> str:
#     """
#     Pakistan فون نمبر کو +92 format میں بدلنا
#     03001234567  →  +923001234567
#     """
#     raw = (raw or "").strip()
#     if raw.startswith("0"):
#         return "+92" + raw[1:]
#     if raw.startswith("92") and not raw.startswith("+"):
#         return "+" + raw
#     return raw


# def send_otp(phone: str) -> tuple[bool, str, str]:
#     """
#     Firebase سے phone پر OTP بھیجنا

#     Parameters:
#       phone → فون نمبر (03xxxxxxxxx یا +923xxxxxxxxx)

#     Returns:
#       (success, session_info, error_msg)
#       کامیاب → (True, "session_token", "")
#       ناکام  → (False, "", "error message")

#     Note:
#       session_info کو محفوظ رکھیں — verify_otp میں چاہیے
#     """
#     phone = normalize_phone(phone)

#     try:
#         response = requests.post(
#             SEND_OTP_URL,
#             headers={"Content-Type": "application/json"},
#             data=json.dumps({
#                 "phoneNumber":          phone,
#             }),
#             timeout=15,
#         )

#         data = response.json()

#         # ── کامیاب ──
#         if "sessionInfo" in data:
#             return True, data["sessionInfo"], ""

#         # ── Firebase error ──
#         error = data.get("error", {})
#         return False, "", _parse_firebase_error(error)

#     except requests.exceptions.Timeout:
#         return False, "", "Timeout | انٹرنیٹ slow ہے — دوبارہ کوشش کریں"
#     except requests.exceptions.ConnectionError:
#         return False, "", "No internet | انٹرنیٹ کنکشن چیک کریں"
#     except Exception as err:
#         return False, "", f"Error: {str(err)[:60]}"


# def verify_otp(session_info: str, otp_code: str) -> tuple[bool, str, str]:
#     """
#     Firebase OTP تصدیق کرنا

#     Parameters:
#       session_info → send_otp سے ملا token
#       otp_code     → user کا 6 ہندسہ OTP

#     Returns:
#       (success, phone_number, error_msg)
#       کامیاب → (True, "+923001234567", "")
#       ناکام  → (False, "", "error message")
#     """
#     try:
#         response = requests.post(
#             VERIFY_OTP_URL,
#             headers={"Content-Type": "application/json"},
#             data=json.dumps({
#                 "sessionInfo": session_info,
#                 "code":        otp_code.strip(),
#             }),
#             timeout=15,
#         )

#         data = response.json()

#         # ── کامیاب ──
#         if "localId" in data or "idToken" in data:
#             phone = data.get("phoneNumber", "")
#             return True, phone, ""

#         # ── Firebase error ──
#         error = data.get("error", {})
#         return False, "", _parse_firebase_error(error)

#     except requests.exceptions.Timeout:
#         return False, "", "Timeout | انٹرنیٹ slow ہے"
#     except requests.exceptions.ConnectionError:
#         return False, "", "No internet | انٹرنیٹ چیک کریں"
#     except Exception as err:
#         return False, "", f"Error: {str(err)[:60]}"


# def _parse_firebase_error(error: dict) -> str:
#     """
#     Firebase error کو اردو/انگریزی میں بدلنا
#     """
#     code = error.get("message", "").upper()

#     errors = {
#         "INVALID_CODE":
#             "⚠ Wrong OTP | OTP غلط ہے!",
#         "SESSION_EXPIRED":
#             "⚠ OTP expired | OTP کی میعاد ختم — دوبارہ بھیجیں",
#         "TOO_MANY_ATTEMPTS_TRY_LATER":
#             "⚠ Too many attempts | بہت زیادہ کوششیں — کچھ دیر بعد کوشش کریں",
#         "INVALID_PHONE_NUMBER":
#             "⚠ Invalid phone | فون نمبر غلط ہے! (+923xxxxxxxxx)",
#         "QUOTA_EXCEEDED":
#             "⚠ SMS limit reached | آج کی SMS limit ختم ہو گئی",
#         "CAPTCHA_CHECK_FAILED":
#             "⚠ reCAPTCHA failed | Firebase testing mode enable کریں",
#         "MISSING_CLIENT_IDENTIFIER":
#             "⚠ Firebase config error | API Key چیک کریں",
#         "INVALID_SESSION_INFO":
#             "⚠ Session expired | دوبارہ OTP بھیجیں",
#         "CODE_EXPIRED":
#             "⚠ OTP expired | OTP پرانا ہو گیا — دوبارہ بھیجیں",
#         "API_KEY_INVALID":
#             "⚠ Invalid API Key | Firebase API Key غلط ہے!",
#     }

#     for key, msg in errors.items():
#         if key in code:
#             return msg

#     return f"⚠ Firebase Error: {code[:60]}"