########################################
###  no static data in home_config.py anymore
########################################

#  home_config.py 

import mimetypes
import logging
import time
import httpx
import flet as ft
from typing import Optional, Callable


from services.database.db import supabase, SUPABASE_URL_STR, SUPABASE_KEY_STR
import os

from flet.auth.providers import GoogleOAuthProvider


_log = logging.getLogger(__name__)

# line 13


# line 20
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")  # your supabase project URL

def get_google_oauth_url() -> str:
    """Get Supabase Google OAuth URL directly."""
    return f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=http://localhost:8550/oauth/callback"

import flet as ft

_EMPTY_SESSION = {
    "access_token":  "",
    "refresh_token": "",
    "user_id":       "",
    "email":         "",
    "role":          "member",
    "full_name":     "ممبر",
    "blood_group":   "",
}

def get_session(page: ft.Page) -> dict:
    try:
        if hasattr(page, "_my_custom_session"):
            return page._my_custom_session
        page._my_custom_session = dict(_EMPTY_SESSION)
        return page._my_custom_session
    except Exception as ex:
        print(f"[SESSION GET ERROR]: {ex}")
        return {}

def set_session(page: ft.Page, data: dict) -> None:
    try:
        current = get_session(page)
        for k, v in data.items():
            current[k] = str(v) if v is not None else ""
        page._my_custom_session = current
    except Exception as ex:
        print(f"[SESSION SET ERROR]: {ex}")

def clear_session(page: ft.Page) -> None:
    page._my_custom_session = dict(_EMPTY_SESSION)
    print("[SESSION] cleared ✅")


def err(tag: str, msg: str) -> None:
    """Structured error helper: [TAG] message."""
    _log.error("[%s] %s", tag, msg)


# ── Optional flet_video ────────────────────────────────────────
try:
    from flet_video import Video, VideoMedia  # type: ignore
    HAS_VIDEO = True
except ImportError:
    HAS_VIDEO = False
    Video = VideoMedia = None


BUCKET = "app-assets"


# ════════════════════════════════════════════════════════════════
#  THEME — single source of truth (light / normal — no dark bg)
# ════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════
#  THEME — imported from core.theme, the ONLY place colors live.
#  This used to be a second, hand-written copy of the color dict
#  (light-mode values, out of sync with core/theme.py's dark
#  values) — that's why changing a color in core/theme.py never
#  showed up on the home page. Now there is exactly one T.
# ════════════════════════════════════════════════════════════════
from core.theme import T

CARD_COLORS: list[str] = [
    T["primary"], T["blue"], T["orange"],
    T["green"],   T["purple"], T["teal"],
]


# ════════════════════════════════════════════════════════════════
#  ROLE SYSTEM
# ════════════════════════════════════════════════════════════════
ROLE_META: dict[str, tuple[str, str, str]] = {
    "head_admin": ("👑 Head Admin", "#5E35B1", "#EDE7F6"),
    "admin":      ("⚙️ Admin",      "#1565C0", "#E3F2FD"),
    "verified":   ("✅ Verified",   "#2E7D32", "#E8F5E9"),
    "member":     ("👤 Member",     "#B26A00", "#FFF3E0"),
}


def role_label(role: str) -> tuple[str, str, str]:
    return ROLE_META.get(role, ("👤 Member", "#B26A00", "#FFF3E0"))


def is_admin(role: str) -> bool:
    return role in ("head_admin", "admin")


def is_head_admin(role: str) -> bool:
    return role == "head_admin"


def is_verified_or_admin(role: str) -> bool:
    return role in ("head_admin", "admin", "verified")


# ════════════════════════════════════════════════════════════════
#  ICON ALIASES
# ════════════════════════════════════════════════════════════════
IC = ft.Icons

I_CLOSE      = IC.CLOSE
I_PEOPLE     = IC.PEOPLE
I_HEART      = IC.FAVORITE
I_BLOOD      = IC.BLOODTYPE
I_CAMPAIGN   = IC.CAMPAIGN
I_STAR       = IC.STAR
I_APPS       = IC.APPS
I_ADMIN      = IC.ADMIN_PANEL_SETTINGS
I_CHEVRON    = IC.CHEVRON_RIGHT
I_REFRESH    = IC.REFRESH
I_LOGOUT     = IC.LOGOUT
I_NOTIF      = IC.NOTIFICATIONS
I_ATTACH     = IC.ATTACH_FILE
I_WALL       = IC.WALLPAPER
I_EDIT       = IC.EDIT
I_GROUP      = IC.GROUPS
I_ERROR      = IC.ERROR
I_INBOX      = IC.INBOX
I_PLAY       = IC.PLAY_CIRCLE
I_ADD        = IC.ADD_CIRCLE
I_PHONE      = IC.PHONE
I_LOCATION   = IC.LOCATION_ON
I_NEWS       = IC.ARTICLE
I_DONOR      = IC.VOLUNTEER_ACTIVISM
I_UPLOAD     = IC.UPLOAD_FILE
I_LEADER     = IC.MILITARY_TECH
I_PERSON2    = IC.PERSON
I_CHECK      = IC.CHECK_CIRCLE
I_PERSON_ADD = IC.PERSON_ADD
I_HISTORY_EDU = IC.HISTORY_EDU_SHARP


# ════════════════════════════════════════════════════════════════
#  Static leader/news/ticker placeholder data has been removed.
#  All of this now comes from Supabase:
#    - Leaders   -> `leaders` table, loaded into state["leaders"]
#                   and passed as leaders_data to build_leaders().
#                   If the table is empty, the UI shows a real
#                   "no leaders yet" empty state instead of fake names.
#    - News/ticker -> `community_updates` table, loaded into
#                   state["news"] and pushed into NewsTicker via
#                   update_text() once it arrives. The ticker starts
#                   blank/"Loading…" rather than showing invented
#                   camp/meeting announcements that were never real.
# ════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════
#  LAYOUT HELPERS
# ════════════════════════════════════════════════════════════════

def _p(l: int = 0, t: int = 0, r: int = 0, b: int = 0) -> ft.Padding:
    return ft.Padding(l, t, r, b)


def _pa(v: int) -> ft.Padding:
    return ft.Padding(v, v, v, v)


def _ps(h: int = 0, v: int = 0) -> ft.Padding:
    return ft.Padding(h, v, h, v)


def _m(l: int = 0, t: int = 0, r: int = 0, b: int = 0) -> ft.Margin:
    return ft.Margin(l, t, r, b)


def _ms(h: int = 0, v: int = 0) -> ft.Margin:
    return ft.Margin(h, v, h, v)


def _border(w: float, c: str) -> ft.Border:
    s = ft.BorderSide(w, c)
    return ft.Border(top=s, bottom=s, left=s, right=s)


def _shadow(blur: int = 8, color: str = "#14000000", dy: int = 3) -> ft.BoxShadow:
    return ft.BoxShadow(
        blur_radius=blur,
        color=color,
        offset=ft.Offset(0, dy),
        spread_radius=0,
    )


def _circle(
    size: int,
    bgcolor: str,
    content: ft.Control,
    border_color: str | None = None,
) -> ft.Container:
    return ft.Container(
        width=size,
        height=size,
        border_radius=size // 2,
        bgcolor=bgcolor,
        border=_border(1.5, border_color) if border_color else None,
        content=content,
        alignment=ft.Alignment(0, 0),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def _divider_line() -> ft.Container:
    return ft.Container(
        margin=_m(l=14, t=6, r=14, b=6),
        height=1,
        bgcolor=T["primary_md"],
    )


# ════════════════════════════════════════════════════════════════
#  SUPABASE HELPERS — call ONLY from background threads
# ════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════
#  Replace upload_to_bucket in home_config.py with this version.
#  Real byte-level progress using httpx streaming + supabase-py v2.
# ════════════════════════════════════════════════════════════════

def upload_to_bucket(
    data: bytes,
    filename: str,
    dest_prefix: str,
    access_token: str,
    on_progress: Optional[Callable[[float], None]] = None,
) -> str:
    """
    Upload *data* to Supabase Storage with real byte-level progress.
    on_progress(float 0.0→1.0) is called as bytes are sent.

    Uses httpx directly so we can stream chunks and report real progress.
    Falls back to supabase-py client for the public URL lookup.

    access_token must be the CALLING USER's session token (not a shared
    global client/key) so uploads stay scoped to that user's session.
    """
    if not access_token:
        raise ValueError("access_token is required (user must be logged in).")

    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    ext  = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    path = f"{dest_prefix}.{ext}"

    total = len(data)
    print(f"[BUCKET] Uploading {total} bytes → {BUCKET}/{path}  mime={mime}")

    # ── Build the Supabase Storage REST URL ──────────────────────────
    # POST  /storage/v1/object/{bucket}/{path}  → create
    # PUT   /storage/v1/object/{bucket}/{path}  → upsert (overwrite)
    storage_url = f"{SUPABASE_URL_STR}/storage/v1/object/{BUCKET}/{path}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  mime,
        "x-upsert":      "true",       # overwrite if exists
    }

    # ── Chunked generator so httpx reports real progress ─────────────
    CHUNK_SIZE = 64 * 1024  # 64 KB per chunk — good balance for mobile
    sent = 0

    def _byte_stream():
        nonlocal sent
        for i in range(0, total, CHUNK_SIZE):
            chunk = data[i: i + CHUNK_SIZE]
            yield chunk
            sent += len(chunk)
            if on_progress and total > 0:
                # Reserve 0.0–0.95 for upload, 0.95–1.0 for DB step
                on_progress(min(0.95, sent / total * 0.95))

    # ── Upload with real streaming ────────────────────────────────────
    with httpx.Client(timeout=120) as client:   # 2 min timeout for large files
        resp = client.post(
            storage_url,
            content=_byte_stream(),
            headers=headers,
        )

    print(f"[BUCKET] HTTP {resp.status_code}: {resp.text[:120]}")

    if resp.status_code not in (200, 201):
        # If object already exists and POST fails, retry with PUT (upsert)
        if resp.status_code == 409:
            print("[BUCKET] 409 conflict — retrying with PUT")
            with httpx.Client(timeout=120) as client:
                resp = client.put(
                    storage_url,
                    content=data,          # full bytes for retry
                    headers=headers,
                )
            print(f"[BUCKET] PUT HTTP {resp.status_code}: {resp.text[:120]}")

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Upload failed {resp.status_code}: {resp.text[:120]}"
            )

    if on_progress:
        on_progress(0.97)

    # ── Get public URL via supabase-py (no HTTP needed) ──────────────
    url = supabase.storage.from_(BUCKET).get_public_url(path)
    print(f"[BUCKET] Public URL: {url}")

    if on_progress:
        on_progress(1.0)

    return url


def set_app_setting(key: str, value: str) -> None:
    """Upsert a key/value row in the app_settings table."""
    supabase.table("app_settings").upsert(
        {"key": key, "value": value},
        on_conflict="key",
    ).execute()


# ════════════════════════════════════════════════════════════════
#  get_current_uid — SESSION-SAFE VERSION
#
#  OLD (leaky):
#      supabase.auth.get_session()   ← global client, shared JWT
#
#  NEW (safe):
#      page.session.get("user_id")   ← per-connection Flet session
#
#  The caller must pass the page object.  If the uid is not yet in
#  session (e.g. first load), home.py's load_data() puts it there
#  after verifying with the per-session user_supabase client.
# ════════════════════════════════════════════════════════════════


def get_current_uid(page: ft.Page) -> str | None:
    """
    Return the authenticated user's UUID from the Flet Session store.
    """
    if not page or not hasattr(page, "session") or not page.session:
        return None
        
    try:
        sess = page.session
        
        # 🌟 فلیٹ کا اصل ڈیٹا سٹور 'store' نامی ڈکشنری میں ہوتا ہے
        if hasattr(sess, "store") and isinstance(sess.store, dict):
            uid = sess.store.get("user_id")
            if uid:
                return str(uid)
                
        return None
        
    except Exception as ex:
        print(f"[AUTH] get_current_uid failed: {ex}")
        return None


# Default logo shown until head_admin uploads a real one via the admin
# panel (pick_logo -> app_settings.org_logo_url). It's a local animated
# GIF bundled in the app's assets folder — NOT a Supabase URL — so it
# always loads instantly, even offline.
#
# Place the file at:  <project>/assets/app_logo.gif
# Default logo shown until head_admin uploads a real one via the admin
# panel (pick_logo -> app_settings.org_logo_url). It's a local animated
# GIF bundled in the app's assets folder — NOT a Supabase URL — so it
# always loads instantly, even offline.
#
# IMPORTANT (Flet asset path rule): this project's ft.run() is started
# with assets_dir="." (the project ROOT is the asset base, not an
# "assets" subfolder resolved on its own). That means any src path here
# must be given RELATIVE TO THE PROJECT ROOT, including the "assets/"
# folder name itself. So the physical file lives at:
#   <project>/assets/app_logo.gif
# and the src string must be exactly:
#   "assets/app_logo.gif"
# (If assets_dir were instead "assets", you'd drop the prefix — but
# that is NOT this project's setup, so keep the prefix here.)
_DEFAULT_LOGO_GIF = "assets/app_logo.gif"


def get_logo_control(
    logo_url: str | None = None,
    width: int = 52,
    height: int = 52,
    # page parameter kept for backward compatibility but no longer used
    page: ft.Page | None = None,
) -> ft.Container:
    """
    Return a circular logo Container.

    Args:
        logo_url:  Pre-resolved URL (from state["logo_url"]). Once the
                   admin uploads a logo, this is a Supabase Storage URL
                   and takes priority. If None/empty, falls back to the
                   bundled default GIF (assets/app_logo.gif).
        width:     Container width in pixels.
        height:    Container height in pixels.
        page:      Ignored (kept for call-site compatibility).
    """
    resolved = (logo_url or "").strip() or _DEFAULT_LOGO_GIF

    # Only cache-bust remote (http/https) URLs. A local asset path like
    # "assets/app_logo.gif" must NOT get a "?v=..." suffix — Flet resolves
    # asset paths literally and a query string breaks the lookup, which is
    # why the old fallback ("assets/logo.png?v=...") never actually showed.
    if resolved.startswith("http"):
        ts = int(time.time())
        busted = f"{resolved}&v={ts}" if "?" in resolved else f"{resolved}?v={ts}"
    else:
        busted = resolved

    return ft.Container(
        width=width,
        height=height,
        border_radius=int(width // 2),
        bgcolor=ft.Colors.TRANSPARENT,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        # Slight inset so a square/rect GIF logo isn't hard-cropped by the
        # circular clip; CONTAIN keeps the whole mark visible (COVER used
        # to crop the edges of non-square default logos).
        padding=max(1, int(width * 0.06)),
        content=ft.Image(
            src=busted,
            fit=ft.BoxFit.CONTAIN,
            error_content=ft.Icon(
                ft.Icons.BLOODTYPE,
                color="#C62828",
                size=float(width * 0.6),
            ),
        ),
    )

