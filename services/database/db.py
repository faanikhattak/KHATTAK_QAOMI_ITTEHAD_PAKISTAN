# ================================================================
#  db.py  —  Supabase Database Connection (100% Pure .env)
# ================================================================

import os
from pathlib import Path
from dotenv import load_dotenv
import httpx
from supabase import create_client, Client, ClientOptions

# ۱. روٹ فولڈر سے .env فائل لوڈ کریں
# NOTE: relative to this file's own location, NOT by searching for a
# folder named "blood_donation_flet" or "app.py" — those don't exist
# inside the packaged Android app (bundle root is renamed to .../app/).
# db.py lives at <root>/services/database/db.py, so root is 2 levels up.
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parents[1]

env_path = root_dir / ".env"
print(f"[DB_INIT] Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path, override=True)

# ۲. انوائرمنٹ ویریبلز کو خالص اسٹرنگز میں محفوظ کریں (کوئی ہارڈکوڈ نہیں)
SUPABASE_URL_STR     = str(os.getenv("SUPABASE_URL")          or "").strip()
SUPABASE_KEY_STR     = str(os.getenv("SUPABASE_KEY")          or "").strip()
SUPABASE_SERVICE_STR = str(os.getenv("SUPABASE_SERVICE_KEY")  or "").strip()

if not SUPABASE_URL_STR or not SUPABASE_KEY_STR:
    print("\n❌ [CRITICAL ERROR] .env file completely missing or corrupted!")
    print(f"👉 SUPABASE_URL: {SUPABASE_URL_STR}")
    print(f"👉 SUPABASE_KEY: {'Found' if SUPABASE_KEY_STR else 'Missing'}\n")

def http1_options() -> ClientOptions:
    """Force HTTP/1.1 for a Supabase client.

    Root cause of the ConnectionTerminated / RemoteProtocolError crashes
    seen across this app (empty member/request/donor lists, "no profile
    to show" etc.): this network (or an antivirus/firewall doing SSL
    inspection) silently drops long-lived HTTP/2 streams mid-request.
    HTTP/1.1 opens a plain connection per request and avoids this.

    IMPORTANT: every file that calls create_client() directly should
    pass options=http1_options() (import this from services.database.db)
    instead of creating a client with no options — otherwise that client
    still defaults to HTTP/2 and can silently fail the same way, with
    fetch functions swallowing the error and returning an empty list.

    A fresh httpx.Client is created per call (not shared/reused across
    create_client() calls) — supabase-py has a known bug where a single
    shared httpx_client's base_url gets mutated when reused across
    postgrest/storage/auth services, causing wrong-endpoint 404s.
    """
    return ClientOptions(httpx_client=httpx.Client(http2=False, timeout=30.0))


# Kept for any existing internal references in this file.
_http1_options = http1_options


try:
    supabase: Client = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())
    print("✅ [SUPABASE] Connection initialized successfully (HTTP/1.1).")
except Exception as e:
    print(f"❌ [SUPABASE] Initialization failed: {e}")
if not SUPABASE_URL_STR or not SUPABASE_KEY_STR:
    raise EnvironmentError("❌ .env file missing or values are empty!")

# ۳. مین سپابیس کلائنٹ انیشلائزیشن
supabase: Client = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())

# ۴. ایڈمن کلائنٹ — service role key for admin ops (password reset etc.)
supabase_admin: Client = create_client(
    SUPABASE_URL_STR,
    SUPABASE_SERVICE_STR if SUPABASE_SERVICE_STR else SUPABASE_KEY_STR,
    options=http1_options(),
)
if SUPABASE_SERVICE_STR:
    print("✅ [SUPABASE] Admin client initialized with service role key.")
else:
    print("⚠️  [SUPABASE] SUPABASE_SERVICE_KEY missing — using anon key for admin client.")

# ڈیٹا بیس فنکشنز
def get_all_admins():
    try:
        return supabase.table("admins").select("*").execute().data or []
    except Exception as e:
        print(f"Error: {e}")
        return []

def get_all_donors():
    try:
        return supabase.table("donors").select("*").execute().data or []
    except Exception as e:
        print(f"Error: {e}")
        return []
# db.py — add this at the bottom

def get_authed_client(access_token: str) -> Client:
    """Return a fresh client authenticated with the given user's JWT."""
    client = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=_http1_options())
    client.postgrest.auth(access_token)
    return client


















