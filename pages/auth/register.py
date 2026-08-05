







# =========================== with location=====================================
#  register.py  —  User Registration System
#  KHATTAK QOMI ETEHAD PAKISTAN  |  Flet v0.84
# ================================================================
from core.theme import Theme 
from httpx import HTTPStatusError
import asyncio
import bcrypt
import re
import json
import threading
import base64
import os
import hashlib
import secrets
import logging
import time
import datetime
from datetime import datetime as dt_module
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import flet as ft
from services.database.db import supabase
from home_module.home_config import get_session, set_session, clear_session, get_logo_control
from core.config import BLOOD_GROUPS, PROVINCES, COUNTRIES, get_districts, get_tehsils, COUNTRY_PHONE_CODES, DEFAULT_COUNTRY_CODE
from services.utils_services.location import add_geolocator, get_location


# ════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ════════════════════════════════════════════════════════════════

class Config:
    MIN_PASSWORD_LENGTH: int = 8
    MAX_PASSWORD_LENGTH: int = 128
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_SPECIAL_CHARS: str = r"!@#$%^&*()_+-=[]{}|;:,.<>?"

    MIN_USERNAME_LENGTH: int = 3
    MAX_USERNAME_LENGTH: int = 20
    USERNAME_PATTERN: str = r"^[a-zA-Z0-9_]+$"

    EMAIL_MAX_LENGTH: int = 254
    EMAIL_PATTERN: str = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    PHONE_E164_PATTERN: str = r"^\+[1-9]\d{1,14}$"

    MAX_ATTEMPTS_PER_HOUR: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 3600

    CSRF_TOKEN_LENGTH: int = 32
    CSRF_TOKEN_EXPIRY_SECONDS: int = 3600

    BCRYPT_ROUNDS: int = 12
    SALT_LENGTH: int = 32

    MAX_DIALOG_WIDTH: int = 400
    DIALOG_AUTO_CLOSE_MS: int = 8000

    LOG_FILE: str = "logs/registration_errors.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5


# ════════════════════════════════════════════════════════════════
#  LOGGING
# ════════════════════════════════════════════════════════════════

os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("RegistrationManager")


# ════════════════════════════════════════════════════════════════
#  DATA CLASSES & ENUMS
# ════════════════════════════════════════════════════════════════

class ValidationErrorType(Enum):
    EMPTY_FIELD = "empty_field"
    INVALID_FORMAT = "invalid_format"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    PASSWORD_MISMATCH = "password_mismatch"
    WEAK_PASSWORD = "weak_password"
    ALREADY_EXISTS = "already_exists"
    DATABASE_ERROR = "database_error"
    RATE_LIMITED = "rate_limited"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class ValidationError:
    field_name: str
    message_en: str
    message_ur: str
    error_type: ValidationErrorType
    suggestion: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "field": self.field_name,
            "message": f"{self.message_ur} | {self.message_en}",
            "type": self.error_type.value,
            "suggestion": self.suggestion,
        }


@dataclass
class RegistrationData:
    username: str = ""
    email: str = ""
    password: str = ""
    confirm_password: str = ""
    full_name: str = ""
    phone: str = ""
    date_of_birth: Optional[str] = None
    avatar_data: Optional[bytes] = None
    avatar_name: Optional[str] = None
    csrf_token: str = ""
    ip_address: str = "127.0.0.1"

    def to_profile_dict(self, user_id: str) -> Dict[str, Any]:
        return {
            "id": user_id,
            "username": self.username.strip().lower(),
            "email": self.email.strip().lower(),
            "full_name": self.full_name.strip() or None,
            "phone": self.phone.strip() or None,
            "date_of_birth": self.date_of_birth or None,
            "role": "member",
            "is_active": True,
            "email_verified": False,
            "phone_verified": False,
            "created_at": dt_module.utcnow().isoformat(),
            "updated_at": dt_module.utcnow().isoformat(),
        }


@dataclass
class RegistrationResult:
    status: str
    message: str = ""
    field_name: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    errors: List[ValidationError] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "field": self.field_name,
            "user_id": self.user_id,
            "email": self.email,
            "errors": [e.to_dict() for e in self.errors] if self.errors else [],
        }


# ════════════════════════════════════════════════════════════════
#  RATE LIMITER
# ════════════════════════════════════════════════════════════════

class RateLimiter:
    def __init__(self, max_attempts: int = Config.MAX_ATTEMPTS_PER_HOUR,
                 window_seconds: int = Config.RATE_LIMIT_WINDOW_SECONDS):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, ip: str) -> Tuple[bool, int]:
        with self._lock:
            now = time.time()
            if ip not in self._attempts:
                self._attempts[ip] = []
            self._attempts[ip] = [
                t for t in self._attempts[ip]
                if now - t < self.window_seconds
            ]
            attempts = len(self._attempts[ip])
            remaining = max(0, self.max_attempts - attempts)
            if attempts >= self.max_attempts:
                logger.warning(f"Rate limit exceeded for IP: {ip}")
                return False, remaining
            return True, remaining

    def record_attempt(self, ip: str) -> None:
        with self._lock:
            if ip not in self._attempts:
                self._attempts[ip] = []
            self._attempts[ip].append(time.time())
            logger.info(f"Registration attempt recorded for IP: {ip}")


# ════════════════════════════════════════════════════════════════
#  CSRF PROTECTION
# ════════════════════════════════════════════════════════════════

class CSRFManager:
    def __init__(self):
        self._tokens: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.Lock()

    def generate_token(self, session_id: str) -> str:
        token = secrets.token_urlsafe(Config.CSRF_TOKEN_LENGTH)
        with self._lock:
            self._tokens[session_id] = (token, time.time())
        return token

    def validate_token(self, session_id: str, token: str) -> bool:
        with self._lock:
            if session_id not in self._tokens:
                return False
            stored_token, created_at = self._tokens[session_id]
            if time.time() - created_at > Config.CSRF_TOKEN_EXPIRY_SECONDS:
                del self._tokens[session_id]
                return False
            is_valid = secrets.compare_digest(stored_token, token)
            if is_valid:
                del self._tokens[session_id]
            return is_valid


# ════════════════════════════════════════════════════════════════
#  PASSWORD HASHING
# ════════════════════════════════════════════════════════════════

class PasswordHasher:
    @staticmethod
    def generate_salt() -> str:
        return secrets.token_hex(Config.SALT_LENGTH)

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return base64.b64encode(key).decode("utf-8")

    @staticmethod
    def verify_password(password: str, salt: str, hash_value: str) -> bool:
        computed = PasswordHasher.hash_password(password, salt)
        return secrets.compare_digest(computed, hash_value)


# ════════════════════════════════════════════════════════════════
#  INPUT SANITIZATION
# ════════════════════════════════════════════════════════════════

class InputSanitizer:
    @staticmethod
    def sanitize_string(value: str, max_length: int = 500) -> str:
        if not value:
            return ""
        value = value.strip()
        value = value[:max_length]
        value = re.sub(r'[<>&"\'\\]', '', value)
        return value

    @staticmethod
    def sanitize_email(email: str) -> str:
        if not email:
            return ""
        email = email.strip().lower()
        email = re.sub(r'\s', '', email)
        return email[:Config.EMAIL_MAX_LENGTH]

    @staticmethod
    def sanitize_username(username: str) -> str:
        if not username:
            return ""
        username = username.strip().lower()
        username = re.sub(r'[^a-z0-9_]', '', username)
        return username[:Config.MAX_USERNAME_LENGTH]


# ════════════════════════════════════════════════════════════════
#  REGISTRATION MANAGER
# ════════════════════════════════════════════════════════════════

class RegistrationManager:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.csrf_manager = CSRFManager()
        self.password_hasher = PasswordHasher()
        self.sanitizer = InputSanitizer()
        self.email_regex = re.compile(Config.EMAIL_PATTERN)
        self.username_regex = re.compile(Config.USERNAME_PATTERN)
        self.phone_regex = re.compile(Config.PHONE_E164_PATTERN)

    def validate_inputs(self, data: RegistrationData) -> List[ValidationError]:
        errors: List[ValidationError] = []

        username = self.sanitizer.sanitize_username(data.username)
        if not username:
            errors.append(ValidationError(
                field_name="username",
                message_en="Username is required",
                message_ur="صارف نام لازمی ہے",
                error_type=ValidationErrorType.EMPTY_FIELD,
                suggestion="Enter a username between 3-20 characters using letters, numbers, and underscores only.",
            ))
        elif len(username) < Config.MIN_USERNAME_LENGTH:
            errors.append(ValidationError(
                field_name="username",
                message_en=f"Username must be at least {Config.MIN_USERNAME_LENGTH} characters",
                message_ur=f"صارف نام کم از کم {Config.MIN_USERNAME_LENGTH} حروف ہونا چاہیے",
                error_type=ValidationErrorType.TOO_SHORT,
                suggestion=f"Enter at least {Config.MIN_USERNAME_LENGTH} characters. Example: john_doe",
            ))
        elif len(username) > Config.MAX_USERNAME_LENGTH:
            errors.append(ValidationError(
                field_name="username",
                message_en=f"Username must be at most {Config.MAX_USERNAME_LENGTH} characters",
                message_ur=f"صارف نام زیادہ سے زیادہ {Config.MAX_USERNAME_LENGTH} حروف ہونا چاہیے",
                error_type=ValidationErrorType.TOO_LONG,
                suggestion=f"Use a shorter username (max {Config.MAX_USERNAME_LENGTH} chars).",
            ))
        elif not self.username_regex.match(username):
            errors.append(ValidationError(
                field_name="username",
                message_en="Username can only contain letters, numbers, and underscores",
                message_ur="صارف نام میں صرف حروف، نمبر اور انڈر سکور ہو سکتے ہیں",
                error_type=ValidationErrorType.INVALID_FORMAT,
                suggestion="Use only a-z, 0-9, and _. Example: user_123",
            ))

        email = self.sanitizer.sanitize_email(data.email)
        if not email:
            errors.append(ValidationError(
                field_name="email",
                message_en="Email is required",
                message_ur="ای میل لازمی ہے",
                error_type=ValidationErrorType.EMPTY_FIELD,
                suggestion="Enter a valid email address. Example: name@example.com",
            ))
        elif not self.email_regex.match(email):
            errors.append(ValidationError(
                field_name="email",
                message_en="Invalid email format",
                message_ur="غلط ای میل فارمیٹ",
                error_type=ValidationErrorType.INVALID_FORMAT,
                suggestion="Check for typos. Format: name@domain.com",
            ))

        password = data.password
        if not password:
            errors.append(ValidationError(
                field_name="password",
                message_en="Password is required",
                message_ur="پاس ورڈ لازمی ہے",
                error_type=ValidationErrorType.EMPTY_FIELD,
                suggestion="Create a strong password with at least 8 characters.",
            ))
        else:
            errors.extend(self._validate_password_strength(password))

        confirm = data.confirm_password
        if not confirm:
            errors.append(ValidationError(
                field_name="confirm_password",
                message_en="Please confirm your password",
                message_ur="پاس ورڈ کی تصدیق کریں",
                error_type=ValidationErrorType.EMPTY_FIELD,
                suggestion="Re-enter your password to confirm.",
            ))
        elif password and confirm and password != confirm:
            errors.append(ValidationError(
                field_name="confirm_password",
                message_en="Passwords do not match",
                message_ur="پاس ورڈ مطابقت نہیں رکھتے",
                error_type=ValidationErrorType.PASSWORD_MISMATCH,
                suggestion="Both password fields must be identical. Check for typos.",
            ))

        if data.phone.strip():
            phone = data.phone.strip()
            if not self.phone_regex.match(phone):
                errors.append(ValidationError(
                    field_name="phone",
                    message_en="Invalid phone number format. Use E.164 format (+1234567890)",
                    message_ur="غلط فون نمبر فارمیٹ۔ E.164 فارمیٹ استعمال کریں",
                    error_type=ValidationErrorType.INVALID_FORMAT,
                    suggestion="Format: +92XXXXXXXXXX (with country code, no spaces)",
                ))

        return errors

    def _validate_password_strength(self, password: str) -> List[ValidationError]:
        errors: List[ValidationError] = []

        if len(password) < Config.MIN_PASSWORD_LENGTH:
            errors.append(ValidationError(
                field_name="password",
                message_en=f"Password must be at least {Config.MIN_PASSWORD_LENGTH} characters",
                message_ur=f"پاس ورڈ کم از کم {Config.MIN_PASSWORD_LENGTH} حروف ہونا چاہیے",
                error_type=ValidationErrorType.TOO_SHORT,
                suggestion=f"Use {Config.MIN_PASSWORD_LENGTH}+ characters. Example: MyP@ssw0rd!",
            ))

        if len(password) > Config.MAX_PASSWORD_LENGTH:
            errors.append(ValidationError(
                field_name="password",
                message_en=f"Password must be at most {Config.MAX_PASSWORD_LENGTH} characters",
                message_ur=f"پاس ورڈ زیادہ سے زیادہ {Config.MAX_PASSWORD_LENGTH} حروف ہونا چاہیے",
                error_type=ValidationErrorType.TOO_LONG,
                suggestion="Use a shorter password.",
            ))

        if Config.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append(ValidationError(
                field_name="password",
                message_en="Password must contain at least one uppercase letter (A-Z)",
                message_ur="پاس ورڈ میں کم از کم ایک بڑا حرف (A-Z) ہونا چاہیے",
                error_type=ValidationErrorType.WEAK_PASSWORD,
                suggestion="Add uppercase letters. Example: Password123",
            ))

        if Config.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append(ValidationError(
                field_name="password",
                message_en="Password must contain at least one lowercase letter (a-z)",
                message_ur="پاس ورڈ میں کم از کم ایک چھوٹا حرف (a-z) ہونا چاہیے",
                error_type=ValidationErrorType.WEAK_PASSWORD,
                suggestion="Add lowercase letters. Example: PASSWORD123",
            ))

        if Config.PASSWORD_REQUIRE_DIGIT and not re.search(r"[0-9]", password):
            errors.append(ValidationError(
                field_name="password",
                message_en="Password must contain at least one digit (0-9)",
                message_ur="پاس ورڈ میں کم از کم ایک نمبر (0-9) ہونا چاہیے",
                error_type=ValidationErrorType.WEAK_PASSWORD,
                suggestion="Add numbers. Example: Password123",
            ))

        if Config.PASSWORD_REQUIRE_SPECIAL and not re.search(
            f"[{re.escape(Config.PASSWORD_SPECIAL_CHARS)}]", password
        ):
            errors.append(ValidationError(
                field_name="password",
                message_en=f"Password must contain at least one special character ({Config.PASSWORD_SPECIAL_CHARS})",
                message_ur=f"پاس ورڈ میں کم از کم ایک خاص حرف ہونا چاہیے ({Config.PASSWORD_SPECIAL_CHARS})",
                error_type=ValidationErrorType.WEAK_PASSWORD,
                suggestion="Add special characters. Example: MyP@ssw0rd!",
            ))

        return errors

    # Same dropped-connection hints used elsewhere in this app (home.py) —
    # a ConnectionTerminated / RemoteProtocolError mid-request means
    # "retry later", not "genuine database failure".
    _NETWORK_ERR_HINTS = (
        "connectionterminated", "remoteprotocolerror", "timeout", "httpcore",
        "connectionerror", "connectionreset", "network is unreachable",
        "temporarily unavailable", "name or service not known", "nodename",
    )

    @staticmethod
    def _is_network_glitch(err: BaseException) -> bool:
        if isinstance(err, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
            return True
        return any(h in str(err).lower() for h in RegistrationManager._NETWORK_ERR_HINTS)

    async def check_uniqueness(self, username: str, email: str) -> List[ValidationError]:
        errors: List[ValidationError] = []
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                username_result = (
                    supabase.table("profiles")
                    .select("username")
                    .eq("username", username.lower())
                    .limit(1)
                    .execute()
                )
                email_result = (
                    supabase.table("profiles")
                    .select("email")
                    .eq("email", email.lower())
                    .limit(1)
                    .execute()
                )
                if (username_result.data and len(username_result.data) > 0) or \
                   (email_result.data and len(email_result.data) > 0):
                    errors.append(ValidationError(
                        field_name="credentials",
                        message_en="Account credentials already in use. Please try different username or email.",
                        message_ur="اکاؤنٹ کی تفصیلات پہلے سے استعمال میں ہیں۔ دوسرا صارف نام یا ای میل آزمائیں۔",
                        error_type=ValidationErrorType.ALREADY_EXISTS,
                        suggestion="Try a different username or email address.",
                    ))
                break  # success (with or without matches) — stop retrying
            except Exception as ex:
                if self._is_network_glitch(ex) and attempt < max_retries:
                    logger.warning(
                        f"Uniqueness check network glitch (attempt {attempt}/{max_retries}): {ex}"
                    )
                    await asyncio.sleep(1.5 * attempt)
                    continue
                logger.error(f"Database uniqueness check failed: {ex}", exc_info=True)
                errors.append(ValidationError(
                    field_name="database",
                    message_en="Unable to verify account availability. Please try again.",
                    message_ur="اکاؤنٹ کی دستیابی تصدیق نہیں ہو سکی۔ دوبارہ کوشش کریں۔",
                    error_type=ValidationErrorType.DATABASE_ERROR,
                    suggestion="Check your internet connection and try again.",
                ))
                break
        return errors

    def hash_password(self, password: str) -> Tuple[str, str]:
        salt = self.password_hasher.generate_salt()
        hash_value = self.password_hasher.hash_password(password, salt)
        return salt, hash_value

    async def save_to_db(self, data: RegistrationData,
                         extra_fields: Optional[Dict[str, Any]] = None) -> RegistrationResult:
        result = RegistrationResult(status="error")

        try:
            salt, password_hash = self.hash_password(data.password)

            auth_res = supabase.auth.sign_up({
                "email": data.email,
                "password": data.password,
            })

            if not auth_res or not auth_res.user:
                logger.error("Supabase auth signup failed: no user returned")
                result.message = "Account creation failed — try again!"
                result.errors.append(ValidationError(
                    field_name="auth",
                    message_en="Account creation failed. Please try again.",
                    message_ur="اکاؤنٹ بنانے میں ناکامی۔ دوبارہ کوشش کریں۔",
                    error_type=ValidationErrorType.DATABASE_ERROR,
                    suggestion="Check your internet connection and try again.",
                ))
                return result

            user_id = auth_res.user.id
            uid = user_id

            def format_sql_date(date_str):
                if date_str and "/" in date_str:
                    parts = date_str.strip().split("/")
                    if len(parts) == 3:
                        return f"{parts[2]}-{parts[1]}-{parts[0]}"
                return None

            avatar_url = None
            if data.avatar_data and data.avatar_name:
                avatar_url = await self._upload_avatar(user_id, data.avatar_data, data.avatar_name)

            ef = extra_fields or {}

            def _dial(key_dial: str, key_num: str) -> Optional[str]:
                dial = ef.get(key_dial, "+92")
                num = (ef.get(key_num) or "").strip().lstrip("0")
                return f"{dial}{num}" if num else None
            salt, password_hash = self.hash_password(data.password)
            dob_sql = format_sql_date(data.date_of_birth)

            profiles_data: Dict[str, Any] = {
                "id": uid,
                "full_name": data.full_name,
                "password_hash": password_hash,
                "password_salt": salt,
                "father_name": ef.get("father_name") or None,
                "username": data.email.split("@")[0].strip(),
                "email": data.email,
                "phone": _dial("phone_dial", "phone_num") or data.phone,
                "whatsapp": _dial("wp_dial", "wp_num"),
                "emergency_contact": _dial("em_dial", "em_num"),
                "cnic": ef.get("cnic") or None,
                "gender": ef.get("gender") or None,
                "date_of_birth": dob_sql,
                "marital_status": ef.get("marital_status") or None,
                "blood_group": ef.get("blood_group") or None,
                "religion": ef.get("religion") or None,
                "profession": ef.get("profession") or None,
                "cast_name": ef.get("cast_name") or None,
                "sub_cast": ef.get("sub_cast") or None,
                "country": ef.get("country") or None,
                "province": ef.get("province") or None,
                "state": ef.get("state") or None,
                "city": ef.get("city") or None,
                "tehsil_village": ef.get("tehsil_village") or None,
                "address": ef.get("address") or None,
                "is_available": ef.get("is_available", False),
                "is_active": True,
                "is_approved": False,
                "role": "member",
                "email_verified": False,
                "phone_verified": False,
                "latitude": ef.get("latitude"),
                "longitude": ef.get("longitude"),
            }

            if avatar_url:
                profiles_data["avatar_url"] = avatar_url

            logger.info(f"[SAVE_DB] Inserting profile for user: {user_id}")
            logger.info(f"[SAVE_DB] DOB raw='{data.date_of_birth}' → sql='{dob_sql}'")

            try:
                supabase.table("profiles").insert(profiles_data).execute()
                logger.info(f"Profile created successfully for user: {user_id}")
            except Exception as ex:
                logger.error(f"Profile insert failed, rolling back auth user: {ex}", exc_info=True)
                try:
                    if hasattr(supabase, "auth") and hasattr(supabase.auth, "admin"):
                        supabase.auth.admin.delete_user(user_id)
                except Exception as rollback_ex:
                    logger.warning(f"Rollback skip (might lack admin permissions): {rollback_ex}")

                result.message = "Profile not saved — contact admin!"
                result.errors.append(ValidationError(
                    field_name="database",
                    message_en="Failed to save profile. Please contact support.",
                    message_ur="پروفائل محفوظ نہیں ہو سکی۔ ایڈمن سے رابطہ کریں۔",
                    error_type=ValidationErrorType.DATABASE_ERROR,
                    suggestion="Contact support with error details.",
                ))
                return result

            try:
                supabase.auth.sign_out()
                logger.info("[REGISTER] Signed out after profile insert — auto-login prevented")
            except Exception as so_ex:
                logger.warning(f"[REGISTER] sign_out failed (non-fatal): {so_ex}")

            result.status = "success"
            result.user_id = user_id
            result.email = data.email
            result.message = "Registration successful! Please verify your email."
            logger.info(f"Registration successful for user: {user_id}")

        except HTTPStatusError as http_ex:
            logger.error(f"Supabase HTTP Error: {http_ex}", exc_info=True)
            if http_ex.response.status_code == 422:
                result.message = "User already registered | یہ ای میل پہلے سے رجسٹرڈ ہے!"
                result.errors.append(ValidationError(
                    field_name="email",
                    message_en="This email address is already registered. Please login.",
                    message_ur="یہ ای میل ایڈریس پہلے سے رجسٹرڈ ہے۔ براہ کرم لاگ ان کریں۔",
                    error_type=ValidationErrorType.ALREADY_EXISTS,
                    suggestion="Try logging in or use a different email address.",
                ))
            else:
                result.message = f"Server Error: {http_ex.response.status_code}"
                result.errors.append(ValidationError(
                    field_name="auth",
                    message_en="Authentication server error. Please try again later.",
                    message_ur="تصدیقی سرور کی خرابی۔ براہ کرم بعد میں دوبارہ کوشش کریں۔",
                    error_type=ValidationErrorType.DATABASE_ERROR,
                ))

        except Exception as ex:
            error_msg = str(ex).lower()
            logger.error(f"Registration failed: {ex}", exc_info=True)

            if any(k in error_msg for k in ("already registered", "user already", "email already")):
                result.message = "User already registered | یہ ای میل پہلے سے رجسٹرڈ ہے!"
                result.errors.append(ValidationError(
                    field_name="email",
                    message_en="This email address is already registered. Please login.",
                    message_ur="یہ ای میل ایڈریس پہلے سے رجسٹرڈ ہے۔ براہ کرم لاگ ان کریں۔",
                    error_type=ValidationErrorType.ALREADY_EXISTS,
                    suggestion="Try logging in or use a different email address.",
                ))
            elif any(k in error_msg for k in ("weak", "password")):
                result.message = "Weak password — add A-Z and 0-9!"
                result.errors.append(ValidationError(
                    field_name="password",
                    message_en="Password is too weak. Add uppercase, numbers, and special characters.",
                    message_ur="پاس ورڈ بہت آسان ہے۔ بڑے حروف، نمبر اور خاص حروف شامل کریں۔",
                    error_type=ValidationErrorType.WEAK_PASSWORD,
                    suggestion="Use a stronger password with mixed case, numbers, and symbols.",
                ))
            elif any(k in error_msg for k in ("network", "connect", "timeout")):
                result.message = "Check your internet connection!"
                result.errors.append(ValidationError(
                    field_name="network",
                    message_en="Network error. Please check your connection.",
                    message_ur="نیٹ ورک خرابی۔ اپنی کنکشن چیک کریں۔",
                    error_type=ValidationErrorType.NETWORK_ERROR,
                    suggestion="Check your internet connection and try again.",
                ))
            else:
                result.message = f"Error: {str(ex)[:90]}"
                result.errors.append(ValidationError(
                    field_name="unknown",
                    message_en="An unexpected error occurred. Please try again.",
                    message_ur="ایک غیر متوقع خرابی پیش آئی۔ دوبارہ کوشش کریں۔",
                    error_type=ValidationErrorType.UNKNOWN,
                    suggestion="If the problem persists, contact support.",
                ))

        return result

    async def _upload_avatar(self, user_id: str, data: bytes, filename: str) -> Optional[str]:
        try:
            ext = os.path.splitext(filename)[1].lstrip(".") or "jpg"
            dest = f"avatars/{user_id}.{ext}"
            supabase.storage.from_("avatars").upload(
                dest, data,
                file_options={"content-type": f"image/{ext}", "upsert": "true"},
            )
            return supabase.storage.from_("avatars").get_public_url(dest)
        except Exception as ex:
            logger.error(f"Avatar upload error: {ex}", exc_info=True)
            return None

    async def register(self, data: RegistrationData,
                        extra_fields: Optional[Dict[str, Any]] = None) -> RegistrationResult:
        is_allowed, remaining = self.rate_limiter.is_allowed(data.ip_address)
        if not is_allowed:
            logger.warning(f"Rate limit hit for IP: {data.ip_address}")
            return RegistrationResult(
                status="error",
                message="Too many attempts — wait 1 hour!",
                errors=[ValidationError(
                    field_name="rate_limit",
                    message_en="Too many registration attempts. Please wait 1 hour.",
                    message_ur="بہت زیادہ رجسٹریشن کی کوششیں۔ 1 گھنٹہ انتظار کریں۔",
                    error_type=ValidationErrorType.RATE_LIMITED,
                    suggestion="Wait 1 hour before trying again.",
                )],
            )

        self.rate_limiter.record_attempt(data.ip_address)

        validation_errors = self.validate_inputs(data)
        if validation_errors:
            logger.info(f"Validation failed: {len(validation_errors)} errors")
            return RegistrationResult(
                status="error",
                message="Please fix the errors below.",
                errors=validation_errors,
            )

        uniqueness_errors = await self.check_uniqueness(
            self.sanitizer.sanitize_username(data.username),
            self.sanitizer.sanitize_email(data.email),
        )
        if uniqueness_errors:
            return RegistrationResult(
                status="error",
                message="Account credentials already in use.",
                errors=uniqueness_errors,
            )

        return await self.save_to_db(data, extra_fields=extra_fields)


# ════════════════════════════════════════════════════════════════
#  DIALOG MANAGER
# ════════════════════════════════════════════════════════════════

class DialogManager:
    RED = "#C62828"
    RED_DK = "#B71C1C"
    RED_LT = "#FFEBEE"
    RED_MID = "#FFCDD2"
    GREEN = "#2E7D32"
    GREEN_LT = "#E8F5E9"
    GREEN_DK = "#1B5E20"
    ORANGE = "#E65100"
    ORANGE_LT = "#FFF3E0"
    BLUE = "#1565C0"
    BLUE_LT = "#E3F2FD"
    GREY = "#757575"
    GREY_BDR = "#E0E0E0"
    WHITE = "#FFFFFF"
    BG = "#FDF8F8"
    SHADOW = "#33C62828"

    def __init__(self, page: ft.Page):
        self.page = page
        self._popup_timer = None
        self._active_dialogs: List[ft.AlertDialog] = []

    def show_error_dialog(self, error: ValidationError, on_dismiss: Optional[callable] = None) -> None:
        dlg = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=self.RED, size=28),
                ft.Column([
                    ft.Text("Validation Error | تصدیق کی خرابی",
                           color=self.RED_DK, weight=ft.FontWeight.BOLD, size=14),
                ], spacing=0, tight=True),
            ], spacing=10),
            content=ft.Column([
                ft.Container(
                    bgcolor=self.RED_LT, border_radius=10,
                    padding=ft.padding.all(12),
                    content=ft.Row([
                        ft.Icon(ft.Icons.TEXT_FIELDS_ROUNDED, color=self.RED, size=16),
                        ft.Text(f"Field: {error.field_name}",
                               color=self.RED_DK, weight=ft.FontWeight.W_600, size=12),
                    ], spacing=8),
                ),
                ft.Divider(color=self.GREY_BDR),
                ft.Container(
                    content=ft.Column([
                        ft.Text(error.message_ur, size=13, color="#212121",
                               weight=ft.FontWeight.W_500),
                        ft.Text(error.message_en, size=12, color=self.GREY),
                    ], spacing=4),
                ),
                ft.Divider(color=self.GREY_BDR),
                ft.Container(
                    bgcolor=self.BLUE_LT, border_radius=10,
                    padding=ft.padding.all(10),
                    content=ft.Row([
                        ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=self.BLUE, size=16),
                        ft.Text(error.suggestion, size=11, color=self.BLUE,
                               weight=ft.FontWeight.W_500),
                    ], spacing=8),
                ),
            ], spacing=10, tight=True, width=320),
            actions=[
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_ROUNDED, color=self.WHITE, size=16),
                        ft.Text("OK | ٹھیک ہے", color=self.WHITE, weight=ft.FontWeight.BOLD, size=13),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=self.RED,
                        shape=ft.RoundedRectangleBorder(radius=12),
                        elevation=4,
                    ),
                    on_click=lambda e: self._close_dialog(dlg, on_dismiss),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.show_dialog(dlg)

    def show_multiple_errors_dialog(self, errors: List[ValidationError],
                                    on_dismiss: Optional[callable] = None) -> None:
        error_items = []
        for i, err in enumerate(errors[:5], 1):
            error_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            width=24, height=24, border_radius=12,
                            bgcolor=self.RED_LT,
                            content=ft.Text(str(i), color=self.RED,
                                          size=11, weight=ft.FontWeight.BOLD),
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column([
                            ft.Text(
                                value=f"{err.field_name.replace('_', ' ').title()}: {err.message_ur}",
                                size=12, color="#212121", weight=ft.FontWeight.W_500,
                            ),
                            ft.Text(err.message_en, size=11, color=self.GREY),
                        ], spacing=0, tight=True, expand=True),
                    ], spacing=10),
                    padding=ft.padding.symmetric(vertical=8),
                )
            )
            if i < len(errors[:5]):
                error_items.append(ft.Divider(height=1, color=self.GREY_BDR))

        dlg = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=self.RED, size=28),
                ft.Column([
                    ft.Text("Multiple Errors | متعدد خرابیاں",
                           color=self.RED_DK, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(f"{len(errors)} issues found | {len(errors)} مسائل ملے",
                           size=11, color=self.GREY),
                ], spacing=0, tight=True),
            ], spacing=10),
            content=ft.Column(error_items, spacing=0, tight=True, width=320),
            actions=[
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_ROUNDED, color=self.WHITE, size=16),
                        ft.Text("OK | ٹھیک ہے", color=self.WHITE, weight=ft.FontWeight.BOLD, size=13),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=self.RED,
                        shape=ft.RoundedRectangleBorder(radius=12),
                        elevation=4,
                    ),
                    on_click=lambda e: self._close_dialog(dlg, on_dismiss),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.show_dialog(dlg)

    def show_success_dialog(self, email: str, phone: str,
                            on_verify: Optional[callable] = None) -> None:
        dlg = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=22),
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=self.GREEN, size=28),
                ft.Column([
                    ft.Text("Registration Successful! | رجسٹریشن کامیاب!",
                            color=self.GREEN, weight=ft.FontWeight.BOLD, size=14),
                ], spacing=0, tight=True),
            ], spacing=10),
            content=ft.Column([
                ft.Container(
                    bgcolor=self.GREEN_LT, border_radius=10,
                    padding=ft.padding.all(12),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.EMAIL_OUTLINED, color=self.BLUE, size=15),
                            ft.Text(email, size=12, color="#212121"),
                        ], spacing=6),
                        ft.Row([
                            ft.Icon(ft.Icons.PHONE_ANDROID_ROUNDED, color=self.RED, size=15),
                            ft.Text(phone, size=12, color="#212121"),
                        ], spacing=6),
                    ], spacing=6),
                ),
                ft.Divider(color=self.GREY_BDR),
                ft.Container(
                    bgcolor=self.GREEN_LT, border_radius=10,
                    padding=ft.padding.all(10),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.VERIFIED_USER_ROUNDED, color=self.GREEN, size=18),
                            ft.Text("Verify Phone Now | ابھی فون تصدیق کریں",
                                    size=13, weight=ft.FontWeight.BOLD, color=self.GREEN_DK),
                        ], spacing=6),
                        ft.Text("A 4-digit OTP will be sent to verify your number.\n"
                                "آپ کے نمبر پر 4 ہندسہ کوڈ بھیجا جائے گا۔",
                                size=11, color=self.GREEN),
                    ], spacing=4),
                ),
            ], spacing=10, tight=True, width=310),
            actions=[
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.VERIFIED_ROUNDED, color=self.WHITE, size=16),
                        ft.Text("Verify Phone | فون تصدیق کریں",
                                color=self.WHITE, weight=ft.FontWeight.BOLD, size=13),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=self.GREEN,
                        shape=ft.RoundedRectangleBorder(radius=12),
                        elevation=4,
                    ),
                    on_click=lambda e: self._handle_success_action(dlg, on_verify),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

        # save phone to session for verification.py to pick up
        try:
            sess = get_session(self.page)
            sess["verify_phone"] = phone
            sess["email"] = email
        except Exception as ex:
            logger.warning(f"[SUCCESS_DLG] Could not save phone to session: {ex}")

        self.page.show_dialog(dlg)

    def show_database_error_dialog(self, message: str, suggestion: str,
                                    on_dismiss: Optional[callable] = None) -> None:
        dlg = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row([
                ft.Icon(ft.Icons.WIFI_OFF_ROUNDED, color=self.ORANGE, size=28),
                ft.Column([
                    ft.Text("Connection Error | کنکشن خرابی",
                           color=self.ORANGE, weight=ft.FontWeight.BOLD, size=14),
                ], spacing=0, tight=True),
            ], spacing=10),
            content=ft.Column([
                ft.Text(message, size=13, color="#212121"),
                ft.Divider(color=self.GREY_BDR),
                ft.Container(
                    bgcolor=self.BLUE_LT, border_radius=10,
                    padding=ft.padding.all(10),
                    content=ft.Row([
                        ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=self.BLUE, size=16),
                        ft.Text(suggestion, size=11, color=self.BLUE),
                    ], spacing=8),
                ),
            ], spacing=10, tight=True, width=320),
            actions=[
                ft.ElevatedButton(
                    content=ft.Text("Retry | دوبارہ کوشش", color=self.WHITE, size=13),
                    style=ft.ButtonStyle(
                        bgcolor=self.ORANGE,
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                    on_click=lambda e: self._close_dialog(dlg, on_dismiss),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.show_dialog(dlg)

    def _close_dialog(self, dlg: ft.AlertDialog, callback: Optional[callable] = None) -> None:
        try:
            self.page.pop_dialog()
        except Exception:
            try:
                dlg.open = False
                self.page.update()
            except Exception:
                pass

        if dlg in self._active_dialogs:
            self._active_dialogs.remove(dlg)

        if callback:
            callback()

    def _handle_success_action(self, dlg: ft.AlertDialog, callback: Optional[callable]) -> None:
        self._close_dialog(dlg, callback)

    def close_all(self) -> None:
        for dlg in self._active_dialogs[:]:
            self._close_dialog(dlg)


# ════════════════════════════════════════════════════════════════
#  TOAST MANAGER
# ════════════════════════════════════════════════════════════════

class ToastManager:
    RED = "#C62828"
    GREEN = "#2E7D32"
    ORANGE = "#E65100"
    BLUE = "#1565C0"
    WHITE = "#FFFFFF"
    SHADOW = "#33C62828"

    STYLES = {
        "error":   (RED,    ft.Icons.ERROR_OUTLINE_ROUNDED),
        "success": (GREEN,  ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED),
        "warn":    (ORANGE, ft.Icons.WARNING_AMBER_ROUNDED),
        "info":    (BLUE,   ft.Icons.INFO_OUTLINE_ROUNDED),
    }

    def __init__(self, page: ft.Page):
        self.page = page
        self._timer = None
        self._popup_box = self._create_popup_box()

    def _create_popup_box(self) -> ft.Container:
        self._popup_text = ft.Text(
            "", color=self.WHITE, size=13, weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER, expand=True,
        )
        self._popup_icon = ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=self.WHITE, size=20)
        self._popup_close = ft.IconButton(
            icon=ft.Icons.CLOSE_ROUNDED, icon_color=self.WHITE, icon_size=16,
            style=ft.ButtonStyle(padding=ft.padding.all(2)),
            on_click=self._close_popup,
        )
        return ft.Container(
            visible=False,
            content=ft.Row(
                [self._popup_icon, self._popup_text, self._popup_close],
                spacing=8, alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=self.RED, border_radius=16,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            width=410,
            shadow=ft.BoxShadow(blur_radius=20, color=self.SHADOW, offset=ft.Offset(0, 6)),
        )

    def show(self, msg: str, kind: str = "error", ms: int = 4500) -> None:
        color, icon_name = self.STYLES.get(kind, self.STYLES["error"])
        self._popup_box.bgcolor = color
        self._popup_icon.name = icon_name
        self._popup_text.value = msg
        self._popup_box.visible = True

        try:
            self.page.update()
        except Exception:
            pass

        if self._timer:
            self._timer.cancel()

        def _hide():
            self._popup_box.visible = False
            try:
                self.page.update()
            except Exception:
                pass

        t = threading.Timer(ms / 1000, _hide)
        t.daemon = True
        t.start()
        self._timer = t

    def _close_popup(self, e) -> None:
        if self._timer:
            self._timer.cancel()
        self._popup_box.visible = False
        try:
            self.page.update()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════
#  REGISTRATION VIEW  —  /register
# ════════════════════════════════════════════════════════════════

def view(page: ft.Page) -> ft.View:
    reg_manager = RegistrationManager()
    dialog_manager = DialogManager(page)
    toast_manager = ToastManager(page)
    geo = add_geolocator(page)

    RED = "#C62828"
    RED_DK = "#B71C1C"
    RED_LT = "#FFEBEE"
    RED_MID = "#FFCDD2"
    GREEN = "#2E7D32"
    GREEN_LT = "#E8F5E9"
    ORANGE = "#E65100"
    BLUE = "#1565C0"
    GREY = "#757575"
    GREY_BDR = "#E0E0E0"
    WHITE = "#FFFFFF"
    BG = "#FDF8F8"
    SHADOW = "#33C62828"

    W = 390
    HW = 185

    FS = dict(
        border_radius=13,
        focused_border_color=RED,
        border_color=GREY_BDR,
        text_size=14,
        label_style=ft.TextStyle(color=GREY, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=13),
        border_width=1.5,
        focused_border_width=2,
        bgcolor=WHITE,
    )
    DDS = dict(
        border_radius=13,
        focused_border_color=RED,
        border_color=GREY_BDR,
        text_size=14,
        label_style=ft.TextStyle(color=GREY, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_width=1.5,
        focused_border_width=2,
        bgcolor=WHITE,
    )

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    def ferr(f, msg: str):
        f.error_text = msg
        f.border_color = RED
        f.focused_border_color = RED

    def fok(f, msg: str = "✓"):
        f.error_text = None
        f.helper_text = msg
        f.helper_style = ft.TextStyle(color=GREEN, size=11)
        f.border_color = GREEN
        f.focused_border_color = GREEN

    def freset(f):
        f.error_text = None
        f.helper_text = None
        f.border_color = GREY_BDR
        f.focused_border_color = RED

    def derr(d, msg: str):
        d.error_text = msg
        d.border_color = RED
        d.focused_border_color = RED

    def dok(d, msg: str = "✓"):
        d.error_text = None
        d.helper_text = msg
        d.helper_style = ft.TextStyle(color=GREEN, size=11)
        d.border_color = GREEN
        d.focused_border_color = GREEN

    # ── Loading Overlay ──────────────────────────────────────────
    loading_ring = ft.ProgressRing(width=44, height=44, stroke_width=4, color=WHITE)
    loading_label = ft.Text(
        "Registering... | رجسٹریشن ہو رہی ہے...",
        color=WHITE, size=14, weight=ft.FontWeight.W_500,
    )
    loading_overlay = ft.Container(
        visible=False, expand=True, bgcolor="#CC000000",
        alignment=ft.Alignment.CENTER,
        content=ft.Column([
            ft.Container(
                padding=ft.padding.symmetric(horizontal=32, vertical=28),
                border_radius=20, bgcolor="#CC212121",
                content=ft.Column(
                    [loading_ring, loading_label],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=14, tight=True,
                ),
            )
        ], alignment=ft.MainAxisAlignment.CENTER,
           horizontal_alignment=ft.CrossAxisAlignment.CENTER),
    )

    if loading_overlay not in page.overlay:
        page.overlay.append(loading_overlay)

    def show_loading(msg: str = "Registering... | رجسٹریشن ہو رہی ہے..."):
        loading_label.value = msg
        loading_overlay.visible = True
        safe_update()

    def hide_loading():
        loading_overlay.visible = False
        safe_update()

    # ── Progress Steps ───────────────────────────────────────────
    STEPS = ["Account", "Personal", "Location", "Contact", "Details"]

    step_circles = []
    step_labels = []
    for i, label in enumerate(STEPS):
        active = (i == 0)
        circle = ft.Container(
            width=30, height=30, border_radius=15,
            bgcolor=RED if active else GREY_BDR,
            content=ft.Text(str(i + 1),
                           color=WHITE if active else GREY,
                           size=12, weight=ft.FontWeight.BOLD,
                           text_align=ft.TextAlign.CENTER),
            alignment=ft.Alignment.CENTER,
        )
        lbl = ft.Text(label, size=9,
                     color=RED if active else GREY,
                     text_align=ft.TextAlign.CENTER,
                     weight=ft.FontWeight.W_600 if active else ft.FontWeight.NORMAL)
        step_circles.append(circle)
        step_labels.append(lbl)

    step_lines = [
        ft.Container(width=30, height=2, bgcolor=GREY_BDR, border_radius=1)
        for _ in range(4)
    ]

    def _step_col(i):
        return ft.Column([step_circles[i], step_labels[i]],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)

    progress_row = ft.Row(
        controls=[
            _step_col(0), step_lines[0],
            _step_col(1), step_lines[1],
            _step_col(2), step_lines[2],
            _step_col(3), step_lines[3],
            _step_col(4),
        ],
        alignment=ft.MainAxisAlignment.CENTER, spacing=2,
    )

    def mark_step_done(idx: int):
        step_circles[idx].bgcolor = GREEN
        step_circles[idx].content = ft.Icon(ft.Icons.CHECK_ROUNDED, color=WHITE, size=14)
        step_labels[idx].color = GREEN
        if idx < 4:
            step_lines[idx].bgcolor = RED
            step_circles[idx + 1].bgcolor = RED
            step_labels[idx + 1].color = RED
            step_circles[idx + 1].content = ft.Text(
                str(idx + 2), color=WHITE, size=12,
                weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

    _current_step = [0]

    def _activate_step(idx: int):
        for i in range(5):
            done = i < idx
            active = i == idx
            if done:
                step_circles[i].bgcolor = GREEN
                step_circles[i].content = ft.Icon(ft.Icons.CHECK_ROUNDED, color=WHITE, size=14)
                step_labels[i].color = GREEN
                if i < 4:
                    step_lines[i].bgcolor = GREEN
            elif active:
                step_circles[i].bgcolor = RED
                step_circles[i].content = ft.Text(
                    str(i + 1), color=WHITE, size=12,
                    weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
                step_labels[i].color = RED
                if i < 4:
                    step_lines[i].bgcolor = GREY_BDR
            else:
                step_circles[i].bgcolor = GREY_BDR
                step_circles[i].content = ft.Text(
                    str(i + 1), color=GREY, size=12,
                    weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
                step_labels[i].color = GREY
                if i < 4:
                    step_lines[i].bgcolor = GREY_BDR

    # ── Avatar Picker ────────────────────────────────────────────
    _avatar_data = [None]
    _avatar_name = [None]

    avatar_preview = ft.Container(
        width=90, height=90, border_radius=45,
        bgcolor=RED_LT, alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Icon(ft.Icons.PERSON_OUTLINE, color=RED, size=44),
        border=ft.border.all(2, RED_MID),
    )
    avatar_label = ft.Text(
        "Tap to select photo | تصویر منتخب کریں",
        size=10, color=GREY, italic=True, text_align=ft.TextAlign.CENTER,
    )

    async def _pick_avatar_async(e=None):
        try:
            files = await ft.FilePicker().pick_files(
                dialog_title="Select Profile Photo | تصویر منتخب کریں",
                allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"],
                allow_multiple=False,
                file_type=ft.FilePickerFileType.IMAGE,
            )
        except Exception as ex:
            logger.error(f"Avatar picker error: {ex}", exc_info=True)
            toast_manager.show(f"Photo picker error: {ex}", "warn")
            return

        if not files:
            return

        f = files[0]
        data = None
        if f.path:
            try:
                with open(f.path, "rb") as fh:
                    data = fh.read()
            except Exception as ex:
                logger.error(f"Avatar read error: {ex}", exc_info=True)
                toast_manager.show("Could not read image file", "warn")
                return
        elif hasattr(f, 'bytes') and f.bytes:
            data = bytes(f.bytes)

        if not data:
            toast_manager.show("Could not read image file", "warn")
            return

        _avatar_data[0] = data
        _avatar_name[0] = f.name
        avatar_label.value = f.name

        b64 = base64.b64encode(data).decode()
        ext = os.path.splitext(f.name)[1].lstrip(".")
        mime_type = "jpeg" if ext.lower() in ["jpg", "jpeg"] else ext.lower()

        avatar_preview.content = ft.Image(
            src=f"data:image/{mime_type};base64,{b64}",
            width=90, height=90, fit=ft.ImageFit.COVER,
        )
        safe_update()

    def _pick_avatar(e=None):
        page.run_task(_pick_avatar_async)

    avatar_area = ft.GestureDetector(
        on_tap=_pick_avatar,
        content=ft.Column([
            ft.Stack([
                avatar_preview,
                ft.Container(
                    width=90, height=90,
                    alignment=ft.Alignment.BOTTOM_RIGHT,
                    content=ft.Container(
                        width=26, height=26, border_radius=13,
                        bgcolor=RED,
                        content=ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED, color=WHITE, size=13),
                        alignment=ft.Alignment.CENTER,
                        border=ft.border.all(2, WHITE),
                    ),
                ),
            ]),
            avatar_label,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
        tooltip="Tap to change photo | تصویر تبدیل کریں",
    )

    # ── Step 1: Account Fields ───────────────────────────────────
    username_f = ft.TextField(
        label="Username | صارف نام *",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        hint_text="3-20 chars, letters, numbers, _",
        width=W, **FS,
    )

    email_f = ft.TextField(
        label="Email | ای میل *",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        hint_text="yourname@gmail.com",
        keyboard_type=ft.KeyboardType.EMAIL,
        width=W, **FS,
    )

    password_f = ft.TextField(
        label="Password | پاس ورڈ *",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True, can_reveal_password=True,
        hint_text="Min 8 | A-Z, a-z, 0-9, symbol",
        width=W, **FS,
    )

    confirm_f = ft.TextField(
        label="Confirm Password | تصدیق *",
        prefix_icon=ft.Icons.LOCK_RESET_OUTLINED,
        password=True, can_reveal_password=True,
        width=W, **FS,
    )

    strength_bar = ft.ProgressBar(
        value=0, width=W, bgcolor=GREY_BDR, color=RED,
        border_radius=4, visible=False,
    )
    strength_label = ft.Text("", size=11, color=GREY, visible=False)

    def _check_confirm():
        p = password_f.value or ""
        c = confirm_f.value or ""
        freset(confirm_f)
        if c and c != p:
            ferr(confirm_f, "Passwords do not match | مطابقت نہیں!")
        elif c and c == p:
            fok(confirm_f, "✓ Matched | مطابق")

    def on_pwd_change(e):
        p = password_f.value or ""
        freset(password_f)
        if p:
            score = sum([
                len(p) >= 8,
                bool(re.search(r"[A-Z]", p)),
                bool(re.search(r"[a-z]", p)),
                bool(re.search(r"[0-9]", p)),
                bool(re.search(r"[^A-Za-z0-9]", p)),
            ])
            levels = [
                (0.2, "Very Weak | بہت ضعیف", RED),
                (0.4, "Weak | ضعیف", ORANGE),
                (0.6, "Fair | ٹھیک", BLUE),
                (0.8, "Good | اچھا", "#1565C0"),
                (1.0, "Strong | مضبوط", GREEN),
            ]
            val, label, color = levels[min(score, 4)]
            strength_bar.value = val
            strength_bar.color = color
            strength_bar.visible = True
            strength_label.value = label
            strength_label.color = color
            strength_label.visible = True
            if score < 3:
                ferr(password_f, "Weak password | پاس ورڈ کمزور!")
            elif score == 5:
                fok(password_f, "✓ Strong | مضبوط")
        else:
            strength_bar.visible = False
            strength_label.visible = False
        _check_confirm()
        safe_update()

    def on_confirm_change(e):
        _check_confirm()
        safe_update()

    password_f.on_change = on_pwd_change
    password_f.on_blur = on_pwd_change
    confirm_f.on_change = on_confirm_change
    confirm_f.on_blur = on_confirm_change

    def on_username_change(e):
        v = (username_f.value or "").strip()
        freset(username_f)
        if not v:
            pass
        elif len(v) < 3:
            ferr(username_f, "Min 3 chars | کم از کم 3 حروف")
        elif len(v) > 20:
            ferr(username_f, "Max 20 chars | زیادہ سے زیادہ 20 حروف")
        elif not re.match(r"^[a-zA-Z0-9_]+$", v):
            ferr(username_f, "Letters, numbers, _ only | صرف a-z, 0-9, _")
        else:
            fok(username_f, "✓ Valid | درست")
        safe_update()

    username_f.on_change = on_username_change
    username_f.on_blur = on_username_change

    def on_email_change(e):
        v = (email_f.value or "").strip()
        freset(email_f)
        if not v:
            pass
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            ferr(email_f, "Invalid format | غلط فارمیٹ")
        else:
            fok(email_f, "✓ Valid email | درست ای میل")
        safe_update()

    email_f.on_change = on_email_change
    email_f.on_blur = on_email_change

    # ── Step 2: Personal Fields ──────────────────────────────────
    full_name_f = ft.TextField(
        label="Full Name | پورا نام *",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        width=W, **FS,
    )

    father_name_f = ft.TextField(
        label="Father's Name | والد کا نام *",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        width=W, **FS,
    )

    cnic_f = ft.TextField(
        label="CNIC | قومی شناختی کارڈ",
        prefix_icon=ft.Icons.BADGE_OUTLINED,
        hint_text="XXXXX-XXXXXXX-X",
        width=W, **FS,
    )

    def live_text(f, min_len: int = 2, ok_msg: str = "✓ OK"):
        def h(e):
            v = (f.value or "").strip()
            if not v:
                freset(f)
            elif len(v) < min_len:
                ferr(f, f"Min {min_len} chars | کم از کم {min_len} حروف!")
            else:
                fok(f, ok_msg)
            safe_update()
        f.on_change = h
        f.on_blur = h

    live_text(full_name_f, 3, "✓ Name OK | نام درج")
    live_text(father_name_f, 3, "✓ Father's name OK")

    gender_f = ft.Dropdown(
        label="Gender | جنس *",
        width=W,
        options=[
            ft.dropdown.Option("Male | مرد"),
            ft.dropdown.Option("Female | خاتون"),
            ft.dropdown.Option("Other | دیگر"),
        ],
        border_radius=13,
        focused_border_color=RED,
        border_color=GREY_BDR,
        text_size=14,
        label_style=ft.TextStyle(color=GREY, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_width=1.5,
        focused_border_width=2,
        bgcolor=WHITE,
    )

    gender_other_f = ft.TextField(
        label="Specify Gender | جنس بتائیں",
        visible=False,
        width=W, **FS,
    )

    def on_gender_change(e):
        gender_other_f.visible = (gender_f.value == "Other | دیگر")
        if not gender_other_f.visible:
            gender_other_f.value = ""
        safe_update()

    gender_f.on_change = on_gender_change

    marital_f = ft.Dropdown(
        label="Marital Status | ازدواجی حیثیت",
        width=W,
        options=[
            ft.dropdown.Option("Single | غیر شادی شدہ"),
            ft.dropdown.Option("Married | شادی شدہ"),
            ft.dropdown.Option("Divorced | طلاق یافتہ"),
            ft.dropdown.Option("Widowed | بیوہ"),
        ],
        **DDS,
    )

    blood_f = ft.Dropdown(
        label="Blood Group | بلڈ گروپ *",
        width=W,
        options=[
            ft.dropdown.Option("A+"), ft.dropdown.Option("A-"),
            ft.dropdown.Option("B+"), ft.dropdown.Option("B-"),
            ft.dropdown.Option("AB+"), ft.dropdown.Option("AB-"),
            ft.dropdown.Option("O+"), ft.dropdown.Option("O-"),
        ],
        **DDS,
    )

    dob_f = ft.TextField(
        label="Date of Birth | تاریخ پیدائش",
        prefix_icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
        hint_text="DD/MM/YYYY", width=HW, **FS,
        read_only=True,
    )

    date_picker = ft.DatePicker(
        first_date=dt_module(1900, 1, 1),
        last_date=dt_module(2026, 12, 31),
        current_date=dt_module.now(),
    )

    def on_date_change(e):
        if date_picker.value:
            dob_f.value = date_picker.value.strftime("%d/%m/%Y")
            dob_f.error_text = None
            dob_f.border_color = GREEN
            dob_f.update()

    date_picker.on_change = on_date_change

    def pick_date_click(e):
        page.show_dialog(date_picker)

    dob_btn = ft.IconButton(
        icon=ft.Icons.EDIT_CALENDAR_ROUNDED, icon_color=RED, icon_size=20,
        tooltip="Pick date | تاریخ منتخب کریں",
        on_click=pick_date_click,
    )

    # ── Step 3: Contact Fields ───────────────────────────────────
    _phone_code_options = [
        ft.dropdown.Option(key=c["code"], text=c["display"])
        for c in COUNTRY_PHONE_CODES
    ]

    def make_phone_row(label_en: str, label_ur: str, required: bool = False):
        dial_dd = ft.Dropdown(
            value=DEFAULT_COUNTRY_CODE,
            width=115,
            options=_phone_code_options,
            border_radius=13,
            border_color=GREY_BDR,
            focused_border_color=RED,
            border_width=1.5,
            focused_border_width=2,
            bgcolor=WHITE,
            text_size=13,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=10),
        )
        phone_input = ft.TextField(
            label=f"{label_en} | {label_ur}{' *' if required else ''}",
            hint_text="3001234567",
            keyboard_type=ft.KeyboardType.PHONE,
            expand=True, **FS,
        )

        def on_phone_change(e):
            v = (phone_input.value or "").strip()
            freset(phone_input)
            if not v:
                pass
            elif not re.match(r"^0?[0-9]{7,13}$", v):
                ferr(phone_input, "Invalid format | غلط فارمیٹ")
            else:
                fok(phone_input, "✓ Valid | درست")
            safe_update()

        phone_input.on_change = on_phone_change
        phone_input.on_blur = on_phone_change

        row = ft.Row(
            [dial_dd, phone_input],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            width=W,
        )
        return row, phone_input, dial_dd

    phone_row,     phone_f,     phone_dial_dd     = make_phone_row("Mobile",    "موبائل",    required=True)
    whatsapp_row,  whatsapp_f,  whatsapp_dial_dd  = make_phone_row("WhatsApp",  "واٹس ایپ")
    emergency_row, emergency_f, emergency_dial_dd = make_phone_row("Emergency", "ایمرجنسی")

    # ── Step 4: Location Fields ──────────────────────────────────
    def _loc_update():
        for _c in [
            country_f, country_other_f,
            province_dd, province_txt,
            city_f, city_txt,
            tehsil_f, tehsil_txt,
            address_f,
        ]:
            try:
                _c.update()
            except Exception:
                pass
        try:
            location_fields_container.update()
        except Exception:
            pass
        safe_update()

    def on_country_change(e):
        selected = (country_f.value or "").strip()
        country_name = selected.split(" | ")[0].strip() if " | " in selected else selected

        is_pakistan    = country_name == "Pakistan"
        is_other       = country_name == "Other"
        is_configured  = country_name in COUNTRIES and not is_pakistan and not is_other

        country_other_f.visible = is_other
        if not is_other:
            country_other_f.value = ""

        if is_pakistan:
            province_dd.visible  = True
            province_dd.value    = None
            province_dd.options  = [ft.dropdown.Option(p) for p in PROVINCES]
            province_txt.visible = False; province_txt.value = ""
            city_f.visible       = True;  city_f.value = None; city_f.options = []
            city_txt.visible     = False; city_txt.value = ""
            tehsil_f.visible     = True;  tehsil_f.value = None; tehsil_f.options = []
            tehsil_txt.visible   = False; tehsil_txt.value = ""

        elif is_configured:
            from core.config import get_provinces
            provinces = get_provinces(country_name) or []
            province_dd.visible  = True
            province_dd.value    = None
            province_dd.options  = [ft.dropdown.Option(p) for p in provinces]
            province_txt.visible = False; province_txt.value = ""
            city_f.visible       = False; city_f.value = None; city_f.options = []
            city_txt.visible     = False; city_txt.value = ""
            tehsil_f.visible     = False; tehsil_f.value = None; tehsil_f.options = []
            tehsil_txt.visible   = False; tehsil_txt.value = ""

        else:
            province_dd.visible  = False; province_dd.value = None
            province_txt.visible = True;  province_txt.value = ""
            city_f.visible       = False; city_f.value = None; city_f.options = []
            city_txt.visible     = True;  city_txt.value = ""
            tehsil_f.visible     = False; tehsil_f.value = None; tehsil_f.options = []
            tehsil_txt.visible   = True;  tehsil_txt.value = ""

        _loc_update()

    def on_province_change(e):
        selected_province = (province_dd.value or "").strip()
        selected_country  = (country_f.value or "").strip()
        country_name = selected_country.split(" | ")[0].strip() if " | " in selected_country else selected_country

        if selected_province:
            districts = get_districts(country_name, selected_province) or []
            if districts:
                city_f.options = [ft.dropdown.Option(d) for d in districts]
                city_f.visible = True
                city_txt.visible = False
            else:
                city_f.options = []; city_f.visible = False
                city_txt.visible = True
        else:
            city_f.options = []; city_f.visible = False
            city_txt.visible = False

        city_f.value   = None
        city_txt.value = ""
        tehsil_f.options = []; tehsil_f.value = None; tehsil_f.visible = False
        tehsil_txt.visible = False; tehsil_txt.value = ""
        _loc_update()

    def on_city_change(e):
        selected_province = (province_dd.value or "").strip()
        selected_city     = (city_f.value or "").strip()
        selected_country  = (country_f.value or "").strip()
        country_name = selected_country.split(" | ")[0].strip() if " | " in selected_country else selected_country

        if country_name == "Pakistan" and selected_city and selected_province:
            tehsils = get_tehsils(country_name, selected_province, selected_city) or []
            if tehsils:
                tehsil_f.options = [ft.dropdown.Option(t) for t in tehsils]
                tehsil_f.visible = True
                tehsil_txt.visible = False
            else:
                tehsil_f.options = []; tehsil_f.visible = False
                tehsil_txt.visible = True
        else:
            tehsil_f.options = []; tehsil_f.visible = False
            tehsil_txt.visible = False

        tehsil_f.value = None
        tehsil_txt.value = ""
        _loc_update()

    country_f = ft.Dropdown(
        label="Country | ملک *",
        width=W,
        options=[ft.dropdown.Option(f"{c} | {c}") for c in COUNTRIES] + [ft.dropdown.Option("Other | دیگر")],
        **DDS,
    )
    country_f.on_select = on_country_change

    country_other_f = ft.TextField(
        label="Specify Country | ملک بتائیں",
        visible=False, width=W, **FS,
    )

    province_dd = ft.Dropdown(
        label="Province | صوبہ *",
        width=W, visible=False,
        **DDS,
    )
    province_dd.on_select = on_province_change

    province_txt = ft.TextField(
        label="Province/State | صوبہ/ریاست *",
        visible=False, width=W, **FS,
    )

    city_f = ft.Dropdown(
        label="City/District | شہر/ضلع *",
        width=W, options=[], visible=False,
        **DDS,
    )
    city_f.on_select = on_city_change

    tehsil_f = ft.Dropdown(
        label="Tehsil | تحصیل",
        width=W, options=[], visible=False,
        **DDS,
    )

    city_txt = ft.TextField(
        label="City | شہر *",
        prefix_icon=ft.Icons.LOCATION_CITY_OUTLINED,
        visible=False, width=W, **FS,
    )

    tehsil_txt = ft.TextField(
        label="Tehsil/Area | تحصیل/علاقہ",
        prefix_icon=ft.Icons.LOCATION_ON_OUTLINED,
        visible=False, width=W, **FS,
    )

    address_f = ft.TextField(
        label="Full Address | مکمل پتہ",
        prefix_icon=ft.Icons.HOME_OUTLINED,
        multiline=True, min_lines=2, max_lines=3,
        width=W, **FS,
    )

    location_fields_container = ft.Column(
        controls=[
            country_f,
            country_other_f,
            province_dd,
            province_txt,
            city_f,
            city_txt,
            tehsil_f,
            tehsil_txt,
            address_f,
        ],
        spacing=10,
    )

    # ── Step 5: Additional Details ───────────────────────────────
    religion_f = ft.Dropdown(
        label="Religion | مذہب",
        width=W,
        options=[
            ft.dropdown.Option("Islam | اسلام"),
            ft.dropdown.Option("Christianity | عیسائیت"),
            ft.dropdown.Option("Hinduism | ہندو مت"),
            ft.dropdown.Option("Other | دیگر"),
        ],
        **DDS,
    )

    religion_other_f = ft.TextField(
        label="Specify Religion | مذہب بتائیں",
        visible=False,
        width=W, **FS,
    )

    def on_religion_change(e):
        religion_other_f.visible = (religion_f.value == "Other | دیگر")
        if not religion_other_f.visible:
            religion_other_f.value = ""
        safe_update()

    religion_f.on_change = on_religion_change

    profession_f = ft.TextField(
        label="Profession | پیشہ",
        prefix_icon=ft.Icons.WORK_OUTLINE,
        width=W, **FS,
    )

    cast_f = ft.TextField(
        label="Cast/Tribe | ذات/قبیلہ",
        prefix_icon=ft.Icons.GROUPS_OUTLINED,
        width=W, **FS,
    )

    sub_cast_f = ft.TextField(
        label="Sub-Cast | ذیلی ذات",
        prefix_icon=ft.Icons.GROUP_OUTLINED,
        width=W, **FS,
    )

    donor_status_f = ft.Dropdown(
        label="Blood Donor Status | خون دینے کی حیثیت *",
        width=W,
        options=[
            ft.dropdown.Option("Available | دستیاب ہے"),
            ft.dropdown.Option("Not Available | دستیاب نہیں"),
            ft.dropdown.Option("Emergency Only | صرف ایمرجنسی میں"),
        ],
        **DDS,
    )

    # ── Submit Button ────────────────────────────────────────────
    sub_btn = ft.ElevatedButton(
        content=ft.Text("Register & Continue | رجسٹر کریں",
                       weight=ft.FontWeight.BOLD, size=15),
        style=ft.ButtonStyle(
            color=WHITE, bgcolor=RED,
            shape=ft.RoundedRectangleBorder(radius=14),
            elevation=6, shadow_color=SHADOW,
        ),
        width=W, height=52,
    )

    def _set_btn_loading():
        sub_btn.disabled = True
        sub_btn.content = ft.Row([
            ft.ProgressRing(width=18, height=18, color=WHITE, stroke_width=2.5),
            ft.Text("Registering... | رجسٹریشن ہو رہی ہے...", color=WHITE, size=13),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        safe_update()

    def _set_btn_ready():
        sub_btn.disabled = False
        sub_btn.content = ft.Text("Register & Continue | رجسٹر کریں",
                                 weight=ft.FontWeight.BOLD, size=15)
        safe_update()

    # ── Per-Step Validation ──────────────────────────────────────
    def validate_step1() -> List[ValidationError]:
        errors: List[ValidationError] = []
        username = (username_f.value or "").strip()
        if not username:
            ferr(username_f, "Required! | لازمی!")
            errors.append(ValidationError("username", "Username is required", "صارف نام لازمی ہے", ValidationErrorType.EMPTY_FIELD, "Enter a username between 3-20 characters."))
        elif len(username) < 3:
            ferr(username_f, "Min 3 chars! | کم از کم 3 حروف!")
            errors.append(ValidationError("username", "Min 3 chars", "کم از کم 3 حروف", ValidationErrorType.TOO_SHORT))
        elif len(username) > 20:
            ferr(username_f, "Max 20 chars!")
            errors.append(ValidationError("username", "Max 20 chars", "زیادہ سے زیادہ 20 حروف", ValidationErrorType.TOO_LONG))
        elif not re.match(r"^[a-zA-Z0-9_]+$", username):
            ferr(username_f, "Letters/numbers/_ only!")
            errors.append(ValidationError("username", "Invalid format", "غلط فارمیٹ", ValidationErrorType.INVALID_FORMAT))
        email = (email_f.value or "").strip()
        if not email:
            ferr(email_f, "Required! | لازمی!")
            errors.append(ValidationError("email", "Email is required", "ای میل لازمی ہے", ValidationErrorType.EMPTY_FIELD, "Example: name@example.com"))
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            ferr(email_f, "Invalid format! | غلط فارمیٹ!")
            errors.append(ValidationError("email", "Invalid email format", "غلط ای میل فارمیٹ", ValidationErrorType.INVALID_FORMAT))
        pw = password_f.value or ""
        if len(pw) < 8:
            ferr(password_f, "Min 8 chars!")
            errors.append(ValidationError("password", "Min 8 chars", "کم از کم 8 حروف", ValidationErrorType.TOO_SHORT))
        elif not re.search(r"[A-Z]", pw):
            ferr(password_f, "Add A-Z!")
            errors.append(ValidationError("password", "Add uppercase", "بڑا حرف شامل کریں", ValidationErrorType.WEAK_PASSWORD))
        elif not re.search(r"[a-z]", pw):
            ferr(password_f, "Add a-z!")
            errors.append(ValidationError("password", "Add lowercase", "چھوٹا حرف شامل کریں", ValidationErrorType.WEAK_PASSWORD))
        elif not re.search(r"[0-9]", pw):
            ferr(password_f, "Add 0-9!")
            errors.append(ValidationError("password", "Add digit", "نمبر شامل کریں", ValidationErrorType.WEAK_PASSWORD))
        elif not re.search(r"[^A-Za-z0-9]", pw):
            ferr(password_f, "Add symbol!")
            errors.append(ValidationError("password", "Add special char", "خاص حرف شامل کریں", ValidationErrorType.WEAK_PASSWORD))
        if pw != (confirm_f.value or ""):
            ferr(confirm_f, "Do not match!")
            errors.append(ValidationError("confirm_password", "Passwords do not match", "پاس ورڈ مطابقت نہیں", ValidationErrorType.PASSWORD_MISMATCH))
        safe_update()
        return errors

    def validate_step2() -> List[ValidationError]:
        errors: List[ValidationError] = []
        if not (full_name_f.value or "").strip():
            ferr(full_name_f, "Required! | لازمی!")
            errors.append(ValidationError("full_name", "Full name is required", "پورا نام لازمی ہے", ValidationErrorType.EMPTY_FIELD))
        safe_update()
        return errors

    def validate_step3() -> List[ValidationError]:
        errors: List[ValidationError] = []
        ph = (phone_f.value or "").strip()
        if not ph:
            ferr(phone_f, "Required! | لازمی!")
            errors.append(ValidationError("phone", "Mobile number is required", "موبائل نمبر لازمی ہے", ValidationErrorType.EMPTY_FIELD))
        elif not re.match(r"^0?3[0-9]{9}$", ph):
            ferr(phone_f, "Invalid number!")
            errors.append(ValidationError("phone", "Invalid mobile format", "غلط موبائل فارمیٹ", ValidationErrorType.INVALID_FORMAT))
        safe_update()
        return errors

    def validate_step4() -> List[ValidationError]:
        errors: List[ValidationError] = []
        if not (country_f.value or "").strip():
            derr(country_f, "Required! | لازمی!")
            errors.append(ValidationError("country", "Country is required", "ملک لازمی ہے", ValidationErrorType.EMPTY_FIELD))
        safe_update()
        return errors

    def validate_all() -> List[ValidationError]:
        errors: List[ValidationError] = []

        username = (username_f.value or "").strip()
        if not username:
            ferr(username_f, "Required! | لازمی!")
            errors.append(ValidationError(field_name="username", message_en="Username is required", message_ur="صارف نام لازمی ہے", error_type=ValidationErrorType.EMPTY_FIELD, suggestion="Enter a username between 3-20 characters."))
        elif len(username) < 3:
            ferr(username_f, "Min 3 chars! | کم از کم 3 حروف!")
            errors.append(ValidationError(field_name="username", message_en="Username must be at least 3 characters", message_ur="صارف نام کم از کم 3 حروف ہونا چاہیے", error_type=ValidationErrorType.TOO_SHORT, suggestion="Enter at least 3 characters. Example: john_doe"))
        elif len(username) > 20:
            ferr(username_f, "Max 20 chars! | زیادہ سے زیادہ 20 حروف!")
            errors.append(ValidationError(field_name="username", message_en="Username must be at most 20 characters", message_ur="صارف نام زیادہ سے زیادہ 20 حروف ہونا چاہیے", error_type=ValidationErrorType.TOO_LONG, suggestion="Use a shorter username (max 20 chars)."))
        elif not re.match(r"^[a-zA-Z0-9_]+$", username):
            ferr(username_f, "Invalid format! | غلط فارمیٹ!")
            errors.append(ValidationError(field_name="username", message_en="Username can only contain letters, numbers, and underscores", message_ur="صارف نام میں صرف حروف، نمبر اور انڈر سکور ہو سکتے ہیں", error_type=ValidationErrorType.INVALID_FORMAT, suggestion="Use only a-z, 0-9, and _. Example: user_123"))

        email = (email_f.value or "").strip()
        if not email:
            ferr(email_f, "Required! | لازمی!")
            errors.append(ValidationError(field_name="email", message_en="Email is required", message_ur="ای میل لازمی ہے", error_type=ValidationErrorType.EMPTY_FIELD, suggestion="Enter a valid email address. Example: name@example.com"))
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            ferr(email_f, "Invalid format! | غلط فارمیٹ!")
            errors.append(ValidationError(field_name="email", message_en="Invalid email format", message_ur="غلط ای میل فارمیٹ", error_type=ValidationErrorType.INVALID_FORMAT, suggestion="Check for typos. Format: name@domain.com"))

        pw = password_f.value or ""
        if len(pw) < 8:
            ferr(password_f, "Min 8 chars! | کم از کم 8 حروف!")
            errors.append(ValidationError(field_name="password", message_en="Password must be at least 8 characters", message_ur="پاس ورڈ کم از کم 8 حروف ہونا چاہیے", error_type=ValidationErrorType.TOO_SHORT, suggestion="Use 8+ characters. Example: MyP@ssw0rd!"))
        elif not re.search(r"[A-Z]", pw):
            ferr(password_f, "Add A-Z! | بڑا حرف شامل کریں!")
            errors.append(ValidationError(field_name="password", message_en="Password must contain at least one uppercase letter (A-Z)", message_ur="پاس ورڈ میں کم از کم ایک بڑا حرف (A-Z) ہونا چاہیے", error_type=ValidationErrorType.WEAK_PASSWORD, suggestion="Add uppercase letters. Example: Password123"))
        elif not re.search(r"[a-z]", pw):
            ferr(password_f, "Add a-z! | چھوٹا حرف شامل کریں!")
            errors.append(ValidationError(field_name="password", message_en="Password must contain at least one lowercase letter (a-z)", message_ur="پاس ورڈ میں کم از کم ایک چھوٹا حرف (a-z) ہونا چاہیے", error_type=ValidationErrorType.WEAK_PASSWORD, suggestion="Add lowercase letters. Example: PASSWORD123"))
        elif not re.search(r"[0-9]", pw):
            ferr(password_f, "Add 0-9! | نمبر شامل کریں!")
            errors.append(ValidationError(field_name="password", message_en="Password must contain at least one digit (0-9)", message_ur="پاس ورڈ میں کم از کم ایک نمبر (0-9) ہونا چاہیے", error_type=ValidationErrorType.WEAK_PASSWORD, suggestion="Add numbers. Example: Password123"))
        elif not re.search(r"[^A-Za-z0-9]", pw):
            ferr(password_f, "Add symbol! | خاص حرف شامل کریں!")
            errors.append(ValidationError(field_name="password", message_en="Password must contain at least one special character", message_ur="پاس ورڈ میں کم از کم ایک خاص حرف ہونا چاہیے", error_type=ValidationErrorType.WEAK_PASSWORD, suggestion="Add special characters. Example: MyP@ssw0rd!"))

        if pw != (confirm_f.value or ""):
            ferr(confirm_f, "Do not match! | مطابقت نہیں!")
            errors.append(ValidationError(field_name="confirm_password", message_en="Passwords do not match", message_ur="پاس ورڈ مطابقت نہیں رکھتے", error_type=ValidationErrorType.PASSWORD_MISMATCH, suggestion="Both password fields must be identical. Check for typos."))

        if not (full_name_f.value or "").strip():
            ferr(full_name_f, "Required! | لازمی!")
            errors.append(ValidationError(field_name="full_name", message_en="Full name is required", message_ur="پورا نام لازمی ہے", error_type=ValidationErrorType.EMPTY_FIELD, suggestion="Enter your full name as it appears on your ID."))

        ph = (phone_f.value or "").strip()
        if not ph:
            ferr(phone_f, "Required! | لازمی!")
            errors.append(ValidationError(field_name="phone", message_en="Mobile number is required", message_ur="موبائل نمبر لازمی ہے", error_type=ValidationErrorType.EMPTY_FIELD, suggestion="Enter your mobile number. Example: 03001234567"))
        elif not re.match(r"^0?3[0-9]{9}$", ph):
            ferr(phone_f, "Invalid number! | غلط نمبر!")
            errors.append(ValidationError(field_name="phone", message_en="Invalid mobile number format", message_ur="غلط موبائل نمبر فارمیٹ", error_type=ValidationErrorType.INVALID_FORMAT, suggestion="Format: 03XXXXXXXXX (11 digits starting with 03)"))

        safe_update()
        return errors

    # ── Step Navigation ──────────────────────────────────────────
    STEP_VALIDATORS = [None, validate_step1, validate_step2, validate_step4, validate_step3, None]

    def _show_step_error(errors: List[ValidationError]):
        first_err = errors[0]
        dlg = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=18),
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ORANGE, size=26),
                ft.Text("Validation Error | تصدیق میں خرابی",
                        color=RED_DK, weight=ft.FontWeight.BOLD, size=14),
            ], spacing=10),
            content=ft.Container(
                bgcolor=RED_LT, border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                content=ft.Column([
                    ft.Text(first_err.message_ur, size=13, color="#212121",
                            weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                    ft.Text(first_err.message_en, size=12, color=GREY,
                            text_align=ft.TextAlign.CENTER),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            actions=[
                ft.ElevatedButton(
                    content=ft.Text("OK | ٹھیک ہے", color=WHITE, weight=ft.FontWeight.BOLD),
                    style=ft.ButtonStyle(bgcolor=RED, shape=ft.RoundedRectangleBorder(radius=12)),
                    on_click=lambda e: (page.pop_dialog(), page.update()),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        page.show_dialog(dlg)

    def _confirm_next_step():
        step = _current_step[0]
        STEP_NAMES_EN = ["Profile Photo", "Account Info", "Personal Info", "Contact Info", "Location Info", "Additional Info"]
        STEP_NAMES_UR = ["پروفائل تصویر", "اکاؤنٹ معلومات", "ذاتی معلومات", "رابطہ معلومات", "رہائش معلومات", "اضافی معلومات"]
        next_en = STEP_NAMES_EN[step + 1] if step + 1 < len(STEP_NAMES_EN) else "Next"
        next_ur = STEP_NAMES_UR[step + 1] if step + 1 < len(STEP_NAMES_UR) else "اگلا"

        dlg = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, color=GREEN, size=26),
                ft.Text("Step Complete! | مرحلہ مکمل!",
                        color=GREEN, weight=ft.FontWeight.BOLD, size=14),
            ], spacing=10),
            content=ft.Container(
                bgcolor=GREEN_LT, border_radius=10,
                padding=ft.padding.all(14),
                content=ft.Column([
                    ft.Text(f"Ready to proceed to:", size=12, color=GREY),
                    ft.Text(f"{next_en} | {next_ur}",
                            size=14, color=RED_DK, weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER),
                ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            actions=[
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=WHITE, size=16),
                        ft.Text("Yes, Continue | جاری رکھیں", color=WHITE,
                                weight=ft.FontWeight.BOLD, size=13),
                    ], spacing=6, tight=True),
                    style=ft.ButtonStyle(bgcolor=GREEN,
                                        shape=ft.RoundedRectangleBorder(radius=12), elevation=4),
                    on_click=lambda e: _go_next_confirmed(dlg),
                ),
                ft.OutlinedButton(
                    content=ft.Text("Stay Here | یہاں رہیں", color=RED, size=13),
                    style=ft.ButtonStyle(side=ft.BorderSide(1.5, RED),
                                        shape=ft.RoundedRectangleBorder(radius=12)),
                    on_click=lambda e: (page.pop_dialog(), page.update()),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        page.show_dialog(dlg)

    def _go_next_confirmed(dlg):
        page.pop_dialog()
        page.update()
        _go_to_step(_current_step[0] + 1)

    def _go_to_step(idx: int):
        _current_step[0] = idx
        progress_idx = max(0, idx - 1)
        _activate_step(progress_idx)
        for i, c in enumerate(step_containers):
            c.visible = (i == idx)
        back_btn.visible = (idx > 0)
        next_btn.visible = (idx < 5)
        sub_btn.visible = (idx == 5)
        safe_update()

    def on_next(e):
        step = _current_step[0]
        validator = STEP_VALIDATORS[step]
        if validator:
            errs = validator()
            if errs:
                _show_step_error(errs)
                return
        _confirm_next_step()

    def on_back(e):
        if _current_step[0] > 0:
            _go_to_step(_current_step[0] - 1)

    # ── Navigation Buttons ───────────────────────────────────────
    next_btn = ft.ElevatedButton(
        content=ft.Row([
            ft.Text("Next Step | اگلا مرحلہ", weight=ft.FontWeight.BOLD, size=14, color=WHITE),
            ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=WHITE, size=18),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(
            color=WHITE, bgcolor=RED,
            shape=ft.RoundedRectangleBorder(radius=14),
            elevation=6, shadow_color=SHADOW,
        ),
        width=W, height=52,
        on_click=on_next,
    )

    back_btn = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.ARROW_BACK_ROUNDED, color=RED, size=18),
            ft.Text("Back | واپس", weight=ft.FontWeight.BOLD, size=14, color=RED),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(
            bgcolor=WHITE,
            side=ft.BorderSide(1.5, RED),
            shape=ft.RoundedRectangleBorder(radius=14),
            elevation=0,
        ),
        width=W, height=48,
        visible=False,
        on_click=on_back,
    )

    # ── Submit Handler ───────────────────────────────────────────
    def on_submit(e):
        errors = validate_all()
        if errors:
            first_err = errors[0]

            FIELD_MAP = {
                "username": username_f, "email": email_f,
                "password": password_f, "confirm_password": confirm_f,
                "full_name": full_name_f, "phone": phone_f,
            }
            focus_widget = FIELD_MAP.get(first_err.field_name)

            dlg_val = ft.AlertDialog(
                modal=True,
                shape=ft.RoundedRectangleBorder(radius=18),
                title=ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#E65100", size=26),
                    ft.Text("Validation Error | تصدیق میں خرابی",
                            color="#B71C1C", weight=ft.FontWeight.BOLD, size=14),
                ], spacing=10),
                content=ft.Column([
                    ft.Container(
                        bgcolor="#FFEBEE", border_radius=10,
                        padding=ft.padding.symmetric(horizontal=14, vertical=12),
                        content=ft.Column([
                            ft.Text(first_err.message_ur, size=13, color="#212121",
                                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                            ft.Text(first_err.message_en, size=12, color="#757575",
                                    text_align=ft.TextAlign.CENTER),
                        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ),
                    ft.Container(
                        bgcolor="#E3F2FD", border_radius=10,
                        padding=ft.padding.all(10),
                        content=ft.Row([
                            ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color="#1565C0", size=14),
                            ft.Text(first_err.suggestion, size=11, color="#1565C0",
                                    weight=ft.FontWeight.W_500),
                        ], spacing=6),
                    ),
                ], spacing=10, tight=True, width=300),
                actions=[
                    ft.ElevatedButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CHECK_ROUNDED, color=WHITE, size=16),
                            ft.Text("OK | ٹھیک ہے", color=WHITE,
                                    weight=ft.FontWeight.BOLD, size=13),
                        ], spacing=6, tight=True),
                        style=ft.ButtonStyle(
                            bgcolor="#C62828",
                            shape=ft.RoundedRectangleBorder(radius=12),
                            elevation=4,
                        ),
                        on_click=lambda e: _dismiss_val_dialog(),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER,
            )

            async def _dismiss_val_dialog():
                page.pop_dialog()
                if focus_widget:
                    try:
                        await focus_widget.focus_async()
                        page.update()
                    except Exception:
                        try:
                            focus_widget.focus()
                            page.update()
                        except Exception:
                            pass

            page.show_dialog(dlg_val)
            return

        email = (email_f.value or "").strip()
        pwd = password_f.value or ""
        ph_raw = (phone_f.value or "").strip()
        ph_e164 = f"+92{ph_raw.lstrip('0')}" if ph_raw.startswith("0") else f"+92{ph_raw}"

        data = RegistrationData(
            username=(username_f.value or "").strip(),
            email=email,
            password=pwd,
            confirm_password=(confirm_f.value or "").strip(),
            full_name=(full_name_f.value or "").strip(),
            phone=ph_e164,
            date_of_birth=(dob_f.value or "").strip() or None,
            avatar_data=_avatar_data[0],
            avatar_name=_avatar_name[0],
            ip_address="127.0.0.1",
        )

        _gender_val = gender_f.value or ""
        _gender = (gender_other_f.value or "").strip() if _gender_val == "Other | دیگر" else _gender_val

        _religion_val = religion_f.value or ""
        _religion = (religion_other_f.value or "").strip() if _religion_val == "Other | دیگر" else _religion_val

        _country_val = country_f.value or ""
        if _country_val == "Other | دیگر":
            _country = (country_other_f.value or "").strip()
        elif " | " in _country_val:
            _country = _country_val.split(" | ")[0]
        else:
            _country = _country_val

        extra_fields: Dict[str, Any] = {
            "phone_dial": phone_dial_dd.value or DEFAULT_COUNTRY_CODE,
            "phone_num": ph_raw,
            "wp_dial": whatsapp_dial_dd.value or DEFAULT_COUNTRY_CODE,
            "wp_num": (whatsapp_f.value or "").strip(),
            "em_dial": emergency_dial_dd.value or DEFAULT_COUNTRY_CODE,
            "em_num": (emergency_f.value or "").strip(),
            "father_name": (father_name_f.value or "").strip() or None,
            "cnic": (cnic_f.value or "").strip() or None,
            "gender": _gender or None,
            "marital_status": marital_f.value or None,
            "blood_group": blood_f.value or None,
            "religion": _religion or None,
            "profession": (profession_f.value or "").strip() or None,
            "cast_name": (cast_f.value or "").strip() or None,
            "sub_cast": (sub_cast_f.value or "").strip() or None,
            "country": _country or None,
            "province": province_dd.value if province_dd.visible else None,
            "state": (province_txt.value or "").strip() if province_txt.visible else None,
            "city": (city_f.value or "").strip() if city_f.visible else (city_txt.value or "").strip() or None,
            "tehsil_village": (tehsil_f.value or "").strip() if tehsil_f.visible else (tehsil_txt.value or "").strip() or None,
            "address": (address_f.value or "").strip() or None,
            "is_available": (donor_status_f.value == "Available | دستیاب ہے"),
        }

        _set_btn_loading()
        show_loading()

        async def _do_submit():
            lat, lon = await get_location(page, geo)
            extra_fields["latitude"] = lat if lat != 0.0 else None
            extra_fields["longitude"] = lon if lon != 0.0 else None

            result = await reg_manager.register(data, extra_fields=extra_fields)
            hide_loading()

            if result.status == "success":
                logger.info("[SUBMIT] Registration success")
                for i in range(5):
                    mark_step_done(i)
                _set_btn_ready()
                sub_btn.disabled = True
                sub_btn.content = ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=WHITE, size=18),
                    ft.Text("Registered! | رجسٹریشن کامیاب!", color=WHITE, size=13),
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
                safe_update()

                dialog_manager.show_success_dialog(
                    result.email or email,
                    ph_e164,
                    on_verify=lambda: page.go("/verification"),
                )

                # ── Save user_id + email to session immediately ──
                try:
                    sess = get_session(page)
                    sess["user_id"]   = result.user_id
                    sess["email"]     = result.email or email
                    sess["full_name"] = (full_name_f.value or "").strip()
                    sess["role"]      = "member"
                except Exception as sess_ex:
                    logger.warning(f"[SUBMIT] Session save failed: {sess_ex}")
                page.update()
            else:
                _set_btn_ready()
                err_msgs = [str(e) for e in result.errors]
                is_duplicate_phone = any("23505" in m for m in err_msgs) or \
                                     any("phone" in m.lower() and "duplicate" in m.lower()
                                         for m in err_msgs)

                if is_duplicate_phone:
                    dup_dlg = ft.AlertDialog(
                        modal=True,
                        shape=ft.RoundedRectangleBorder(radius=18),
                        title=ft.Row([
                            ft.Icon(ft.Icons.PHONE_LOCKED_ROUNDED, color="#C62828", size=26),
                            ft.Text("Duplicate Number | نمبر پہلے سے موجود",
                                    color="#B71C1C", weight=ft.FontWeight.BOLD, size=13),
                        ], spacing=10),
                        content=ft.Container(
                            bgcolor="#FFEBEE", border_radius=10,
                            padding=ft.padding.all(14),
                            content=ft.Column([
                                ft.Text("یہ فون نمبر پہلے سے رجسٹرڈ ہے!",
                                        size=13, color="#212121", weight=ft.FontWeight.W_600,
                                        text_align=ft.TextAlign.CENTER),
                                ft.Text("This mobile number is already registered!",
                                        size=12, color="#757575", text_align=ft.TextAlign.CENTER),
                            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        ),
                        actions=[
                            ft.ElevatedButton(
                                content=ft.Text("OK | ٹھیک ہے", color=WHITE, weight=ft.FontWeight.BOLD),
                                style=ft.ButtonStyle(bgcolor="#C62828", shape=ft.RoundedRectangleBorder(radius=12)),
                                on_click=lambda e: (page.pop_dialog(), phone_f.focus(), page.update()),
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.CENTER,
                    )
                    page.show_dialog(dup_dlg)
                elif result.errors:
                    if len(result.errors) == 1:
                        dialog_manager.show_error_dialog(result.errors[0])
                    else:
                        dialog_manager.show_multiple_errors_dialog(result.errors)
                else:
                    toast_manager.show(result.message, "error")

        page.run_task(_do_submit)

    sub_btn.on_click = on_submit

    # ── Layout Helpers ───────────────────────────────────────────
    def card(controls, color=WHITE):
        return ft.Card(
            elevation=8, shadow_color=SHADOW,
            shape=ft.RoundedRectangleBorder(radius=20),
            content=ft.Container(
                bgcolor=color, border_radius=20,
                padding=ft.padding.symmetric(horizontal=22, vertical=20),
                width=430,
                content=ft.Column(controls, spacing=12),
            ),
        )

    def sec_header(icon, en: str, ur: str, step_num: int):
        return ft.Row([
            ft.Container(
                width=34, height=34, border_radius=17, bgcolor=RED_LT,
                content=ft.Icon(icon, color=RED, size=18),
                alignment=ft.Alignment.CENTER,
            ),
            ft.Column([
                ft.Text(en, size=14, weight=ft.FontWeight.BOLD, color=RED_DK),
                ft.Text(ur, size=11, color=GREY),
            ], spacing=0, tight=True),
            ft.Container(expand=True),
            ft.Container(
                content=ft.Text(f"Step {step_num}", size=10, color=RED, weight=ft.FontWeight.W_600),
                bgcolor=RED_LT, border_radius=8,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            ),
        ], spacing=10)

    # ── Step Containers ──────────────────────────────────────────
    logo_container = get_logo_control(logo_url=None, width=100, height=100)

    step_containers = [
        ft.Container(
            visible=True,
            content=ft.Column([
                card([
                    sec_header(ft.Icons.CAMERA_ALT_OUTLINED, "Profile Photo", "پروفائل تصویر", 0),
                    ft.Divider(color=RED_MID, thickness=1),
                    ft.Container(alignment=ft.Alignment.CENTER, content=avatar_area, width=120, height=120),
                    ft.Container(
                        content=ft.Text("JPG, PNG, WEBP — Optional | اختیاری",
                                        size=10, color=GREY, text_align=ft.TextAlign.CENTER),
                        alignment=ft.Alignment.CENTER,
                    ),
                ]),
            ], spacing=12),
        ),

        ft.Container(
            visible=False,
            content=ft.Column([
                card([
                    sec_header(ft.Icons.SECURITY_OUTLINED, "Account Info", "اکاؤنٹ معلومات", 1),
                    ft.Divider(color=RED_MID, thickness=1),
                    username_f, email_f, password_f,
                    strength_bar, strength_label,
                    confirm_f,
                ]),
            ], spacing=12),
        ),

        ft.Container(
            visible=False,
            content=ft.Column([
                card([
                    sec_header(ft.Icons.PERSON_OUTLINE, "Personal Info", "ذاتی معلومات", 2),
                    ft.Divider(color=RED_MID, thickness=1),
                    full_name_f,
                    father_name_f,
                    ft.Row([
                        ft.Column([
                            ft.Row([dob_f, dob_btn], spacing=4,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ], spacing=0, tight=True),
                    ], spacing=6),
                    gender_f, gender_other_f,
                    marital_f, blood_f, cnic_f,
                ]),
            ], spacing=12),
        ),

        ft.Container(
            visible=False,
            content=ft.Column([
                card([
                    sec_header(ft.Icons.LOCATION_ON_OUTLINED, "Location", "رہائش", 3),
                    ft.Divider(color=RED_MID, thickness=1),
                    location_fields_container,
                ]),
            ], spacing=12),
        ),

        ft.Container(
            visible=False,
            content=ft.Column([
                card([
                    sec_header(ft.Icons.CONTACT_PHONE_OUTLINED, "Contact Info", "رابطہ معلومات", 4),
                    ft.Divider(color=RED_MID, thickness=1),
                    ft.Text("Mobile | موبائل *", size=12, color=GREY, weight=ft.FontWeight.W_500),
                    phone_row,
                    ft.Text("WhatsApp | واٹس ایپ", size=12, color=GREY, weight=ft.FontWeight.W_500),
                    whatsapp_row,
                    ft.Text("Emergency Contact | ایمرجنسی رابطہ", size=12, color=GREY, weight=ft.FontWeight.W_500),
                    emergency_row,
                ]),
            ], spacing=12),
        ),

        ft.Container(
            visible=False,
            # پورٹل کو ہوریزونٹلی اور ورٹیکلی سینٹر کرنے کے لیے پوزیشننگ
            expand=True, 
            alignment=ft.Alignment.CENTER, 

            content=ft.Column([
                # کارڈ جس کے اندر تمام فیلڈز موجود ہیں
                card([
                    sec_header(ft.Icons.MORE_HORIZ_OUTLINED, "Additional Info", "اضافی معلومات", 5),
                    ft.Divider(color=RED_MID, thickness=1),

                    # فیلڈز کی ترتیب
                    religion_f, 
                    religion_other_f,
                    profession_f, 
                    cast_f, 
                    sub_cast_f,
                    donor_status_f,
                ]),

                ft.Container(height=6),

                # لازمی فیلڈز کا نوٹ
                ft.Row([
                    ft.Icon(ft.Icons.STAR_ROUNDED, color=RED, size=9),
                    ft.Text("  * Required fields | لازمی فیلڈز", size=11, color=GREY, italic=True),
                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER), # نوٹ کو بھی سینٹر کرنے کے لیے

            ], 
            spacing=12,
            alignment=ft.MainAxisAlignment.CENTER,       # کالم کے اندر کی چیزوں کو ورٹیکلی سینٹر کرے گا
            horizontal_alignment=ft.CrossAxisAlignment.CENTER # کالم کے اندر کی چیزوں کو ہوریزونٹلی سینٹر کرے گا
            ),
        ),
    ]



    sub_btn.visible = False

    return ft.View(
        route="/register",
        scroll=ft.ScrollMode.HIDDEN,
        bgcolor=BG,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color=WHITE,
                on_click=lambda _: page.go("/login"),
            ),
            title=ft.Column([
                ft.Text("Member Registration", size=15, weight=ft.FontWeight.BOLD, color=WHITE),
                ft.Text("ممبر رجسٹریشن", size=10, color=RED_MID),
            ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            center_title=True, bgcolor=RED, elevation=4,
        ),
        controls=[
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=16),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                    scroll=ft.ScrollMode.ALWAYS,
                    expand=True,
                    controls=[
                        logo_container,
                        ft.Container(height=8),
                        ft.Text("KHATTAK QAOMI ITTEHAD PAKISTAN",
                                size=12, color=RED, weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("خٹک قومی اتحاد پاکستان",
                                size=12, color=RED, weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=16),
                        progress_row,
                        ft.Container(height=14),
                        toast_manager._popup_box,
                        ft.Container(height=8),
                        *step_containers,
                        ft.Container(height=16),
                        back_btn,
                        ft.Container(height=8),
                        next_btn,
                        sub_btn,
                        ft.Container(height=10),
                        ft.Row([
                            ft.Text("Already a member? | پہلے سے ممبر؟", color=GREY, size=13),
                            ft.TextButton("Login | لاگ ان",
                                          style=ft.ButtonStyle(color=RED),
                                          on_click=lambda _: page.go("/login")),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=8),
                        ft.Row([
                            ft.Icon(ft.Icons.LOCK_OUTLINE_ROUNDED, color="#BDBDBD", size=12),
                            ft.Text("  Your data is secure | آپ کا ڈیٹا محفوظ ہے",
                                    size=11, color="#BDBDBD"),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=24),
                    ],
                ),
            ),
        ],
    )


# ════════════════════════════════════════════════════════════════
#  PHONE VERIFICATION VIEW  —  /verify_phone
# ════════════════════════════════════════════════════════════════

def verify_phone_view(page: ft.Page) -> ft.View:
    from services.firebase.firebase_otp import send_otp, verify_otp as firebase_verify_otp

    RED = "#C62828"
    RED_DK = "#B71C1C"
    RED_LT = "#FFEBEE"
    RED_MID = "#FFCDD2"
    GREEN = "#2E7D32"
    GREEN_LT = "#E8F5E9"
    GREY = "#757575"
    GREY_BDR = "#E0E0E0"
    WHITE = "#FFFFFF"
    BG = "#FDF8F8"
    SHADOW = "#33C62828"

    RESEND_SECONDS = 60

    _otp_session = [None]
    _countdown = [RESEND_SECONDS]
    _timer_ref: list = [None]

    def _get_phone() -> str:
        try:
            raw = page.session.get("session")
            data = json.loads(raw) if isinstance(raw, str) else (raw or {})
            return data.get("verify_phone", "") or data.get("phone", "")
        except Exception:
            return ""

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    otp_field = ft.TextField(
        label="6-Digit OTP | 6 ہندسہ کوڈ",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        hint_text="123456",
        keyboard_type=ft.KeyboardType.NUMBER,
        max_length=6,
        text_align=ft.TextAlign.CENTER,
        border_radius=14,
        focused_border_color=RED,
        border_color=GREY_BDR,
        text_size=22,
        content_padding=ft.padding.symmetric(horizontal=18, vertical=16),
        border_width=1.5,
        focused_border_width=2.5,
        bgcolor=WHITE,
        label_style=ft.TextStyle(color=GREY, size=12),
        width=300,
        autofocus=True,
    )

    status_text = ft.Text("", size=12, text_align=ft.TextAlign.CENTER)

    countdown_text = ft.Text(
        f"Resend OTP in {_countdown[0]}s | دوبارہ کوڈ {_countdown[0]} سیکنڈ میں",
        size=12, color=GREY, text_align=ft.TextAlign.CENTER,
    )
    resend_btn = ft.TextButton(
        "Resend OTP | دوبارہ کوڈ بھیجیں",
        style=ft.ButtonStyle(color=RED),
        visible=False,
    )

    verify_btn = ft.ElevatedButton(
        content=ft.Text("Verify | تصدیق کریں", weight=ft.FontWeight.BOLD, size=15),
        style=ft.ButtonStyle(
            color=WHITE, bgcolor=RED,
            shape=ft.RoundedRectangleBorder(radius=14),
            elevation=6, shadow_color=SHADOW,
        ),
        width=300, height=52,
    )

    def _set_verify_loading():
        verify_btn.disabled = True
        verify_btn.content = ft.Row([
            ft.ProgressRing(width=18, height=18, color=WHITE, stroke_width=2.5),
            ft.Text("Verifying... | تصدیق ہو رہی ہے...", color=WHITE, size=13),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        safe_update()

    def _set_verify_ready():
        verify_btn.disabled = False
        verify_btn.content = ft.Text("Verify | تصدیق کریں", weight=ft.FontWeight.BOLD, size=15)
        safe_update()

    def _tick():
        if _countdown[0] > 0:
            _countdown[0] -= 1
            countdown_text.value = (
                f"Resend OTP in {_countdown[0]}s | دوبارہ کوڈ {_countdown[0]} سیکنڈ میں"
            )
            safe_update()
            _timer_ref[0] = threading.Timer(1.0, _tick)
            _timer_ref[0].daemon = True
            _timer_ref[0].start()
        else:
            countdown_text.visible = False
            resend_btn.visible = True
            safe_update()

    def _send_initial_otp():
        phone = _get_phone()
        if not phone:
            status_text.value = "⚠ Phone not found — go back | فون نمبر نہیں ملا"
            status_text.color = RED
            safe_update()
            return

        status_text.value = "Sending OTP... | OTP بھیجا جا رہا ہے..."
        status_text.color = GREY
        safe_update()

        def _work():
            success, session, err_msg = send_otp(phone)
            if success:
                _otp_session[0] = session
                status_text.value = f"✓ OTP sent to {phone} | OTP بھیج دیا"
                status_text.color = GREEN
                _timer_ref[0] = threading.Timer(1.0, _tick)
                _timer_ref[0].daemon = True
                _timer_ref[0].start()
            else:
                status_text.value = f"⚠ {err_msg}"
                status_text.color = RED
                countdown_text.visible = False
                resend_btn.visible = True
            safe_update()

        threading.Thread(target=_work, daemon=True).start()

    threading.Thread(target=_send_initial_otp, daemon=True).start()

    def on_send_otp(e):
        phone = _get_phone()
        if not phone:
            status_text.value = "⚠ Phone not found | فون نہیں ملا"
            status_text.color = RED
            safe_update()
            return

        _countdown[0] = RESEND_SECONDS
        resend_btn.visible = False
        countdown_text.visible = True
        countdown_text.value = (
            f"Resend OTP in {_countdown[0]}s | دوبارہ کوڈ {_countdown[0]} سیکنڈ میں"
        )
        status_text.value = "Sending OTP... | OTP بھیجا جا رہا ہے..."
        status_text.color = GREY
        safe_update()

        if _timer_ref[0]:
            _timer_ref[0].cancel()

        def _work():
            success, session, err_msg = send_otp(phone)
            if success:
                _otp_session[0] = session
                status_text.value = "OTP sent again! | کوڈ دوبارہ بھیجا گیا!"
                status_text.color = GREEN
                _timer_ref[0] = threading.Timer(1.0, _tick)
                _timer_ref[0].daemon = True
                _timer_ref[0].start()
            else:
                status_text.value = f"⚠ {err_msg}"
                status_text.color = RED
                countdown_text.visible = False
                resend_btn.visible = True
            safe_update()

        threading.Thread(target=_work, daemon=True).start()
        logger.info("[VERIFY_PHONE] OTP resend requested")

    resend_btn.on_click = on_send_otp

    def on_verify(e):
        otp = (otp_field.value or "").strip()

        otp_field.error_text = None
        otp_field.border_color = GREY_BDR
        if not otp or len(otp) != 6 or not otp.isdigit():
            otp_field.error_text = "Enter 6-digit OTP | 6 ہندسہ کوڈ درج کریں"
            otp_field.border_color = RED
            safe_update()
            return

        if not _otp_session[0]:
            otp_field.error_text = "OTP not sent yet | پہلے OTP بھیجیں"
            otp_field.border_color = RED
            safe_update()
            return

        _set_verify_loading()
        status_text.value = ""
        safe_update()

        def _work():
            phone = _get_phone()
            success, _phone_out, err_msg = firebase_verify_otp(_otp_session[0], otp)

            if success:
                try:
                    email = ""
                    raw = page.session.get("session")
                    data = json.loads(raw) if isinstance(raw, str) else (raw or {})
                    email = data.get("email", "")
                    if email:
                        supabase.table("profiles").update({
                            "phone_verified": True,
                        }).eq("email", email).execute()
                        logger.info(f"[VERIFY_PHONE] phone_verified=True saved for {email}")
                except Exception as ex:
                    logger.error(f"[VERIFY_PHONE] DB update failed: {ex}", exc_info=True)

                if _timer_ref[0]:
                    _timer_ref[0].cancel()

                otp_field.border_color = GREEN
                status_text.value = "✓ Verified! | تصدیق کامیاب!"
                status_text.color = GREEN
                safe_update()

                ok_dlg = ft.AlertDialog(
                    modal=True,
                    shape=ft.RoundedRectangleBorder(radius=18),
                    title=ft.Row([
                        ft.Icon(ft.Icons.VERIFIED_ROUNDED, color=GREEN, size=28),
                        ft.Text("Verified! | تصدیق ہو گئی!",
                                color=GREEN, weight=ft.FontWeight.BOLD, size=14),
                    ], spacing=10),
                    content=ft.Container(
                        bgcolor=GREEN_LT, border_radius=10,
                        padding=ft.padding.all(14),
                        content=ft.Text(
                            "آپ کا فون نمبر کامیابی سے تصدیق ہو گیا!\n"
                            "Your phone number has been successfully verified!",
                            size=13, color="#212121",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ),
                    actions=[
                        ft.ElevatedButton(
                            content=ft.Text("Continue | جاری رکھیں",
                                            color=WHITE, weight=ft.FontWeight.BOLD),
                            style=ft.ButtonStyle(
                                bgcolor=GREEN,
                                shape=ft.RoundedRectangleBorder(radius=12),
                            ),
                            on_click=lambda e: (page.pop_dialog(), page.go("/home")),
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.CENTER,
                )
                page.show_dialog(ok_dlg)

            else:
                logger.error(f"[VERIFY_PHONE] OTP verification failed: {err_msg}")
                _set_verify_ready()
                otp_field.error_text = "Invalid OTP — try again | غلط کوڈ، دوبارہ کوشش کریں"
                otp_field.border_color = RED
                status_text.value = f"⚠ {err_msg}"
                status_text.color = RED
                safe_update()

        threading.Thread(target=_work, daemon=True).start()

    verify_btn.on_click = on_verify

    return ft.View(
        route="/verify_phone",
        scroll=ft.ScrollMode.AUTO,
        bgcolor=BG,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color=WHITE,
                on_click=lambda _: page.go("/home"),
            ),
            title=ft.Column([
                ft.Text("Phone Verification", size=15, weight=ft.FontWeight.BOLD, color=WHITE),
                ft.Text("فون تصدیق", size=10, color=RED_MID),
            ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            center_title=True, bgcolor=RED, elevation=4,
        ),
        controls=[
            ft.Container(
                padding=ft.padding.symmetric(horizontal=18, vertical=24),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                    controls=[
                        ft.Container(
                            width=80, height=80, border_radius=40,
                            bgcolor=RED_LT,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.PHONE_ANDROID_ROUNDED, color=RED, size=40),
                            border=ft.border.all(2, RED_MID),
                        ),
                        ft.Container(height=16),
                        ft.Text("Enter Verification Code",
                                size=18, weight=ft.FontWeight.BOLD, color=RED_DK,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("تصدیقی کوڈ درج کریں",
                                size=14, color=GREY, text_align=ft.TextAlign.CENTER),
                        ft.Container(height=6),
                        ft.Text(
                            "A 6-digit OTP has been sent to your registered phone number.\n"
                            "آپ کے رجسٹرڈ نمبر پر 6 ہندسہ کوڈ بھیجا گیا ہے۔",
                            size=12, color=GREY, text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=24),
                        ft.Card(
                            elevation=8, shadow_color=SHADOW,
                            shape=ft.RoundedRectangleBorder(radius=20),
                            content=ft.Container(
                                bgcolor=WHITE, border_radius=20,
                                padding=ft.padding.symmetric(horizontal=22, vertical=24),
                                width=360,
                                content=ft.Column([
                                    ft.Row([
                                        ft.Container(
                                            width=32, height=32, border_radius=16, bgcolor=RED_LT,
                                            content=ft.Icon(ft.Icons.VERIFIED_USER_ROUNDED, color=RED, size=16),
                                            alignment=ft.Alignment.CENTER,
                                        ),
                                        ft.Text("OTP Verification | کوڈ تصدیق",
                                                size=14, weight=ft.FontWeight.BOLD, color=RED_DK),
                                    ], spacing=10),
                                    ft.Divider(color=RED_MID, thickness=1),
                                    otp_field,
                                    ft.Container(height=4),
                                    status_text,
                                    ft.Container(height=8),
                                    verify_btn,
                                    ft.Container(height=12),
                                    ft.Column([
                                        countdown_text,
                                        resend_btn,
                                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                                ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            ),
                        ),
                        ft.Container(height=20),
                        ft.Row([
                            ft.Icon(ft.Icons.LOCK_OUTLINE_ROUNDED, color="#BDBDBD", size=12),
                            ft.Text("  Your data is secure | آپ کا ڈیٹا محفوظ ہے",
                                    size=11, color="#BDBDBD"),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=24),
                    ],
                ),
            ),
        ],
    )