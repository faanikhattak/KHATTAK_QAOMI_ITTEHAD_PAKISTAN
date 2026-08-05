import time
import json
import asyncio
import os
import logging
import flet as ft
from supabase import create_client 

# Module Imports
import pages.user.feedback          as feedback_page
from pages.user import leaders
from pages.user import leaders_view as leaders_view
import pages.user.community_updates as community_updates
import pages.user.leaderboard       as leaderboard_page
import pages.auth.login             as login
import pages.auth.register          as register
import pages.auth.verification      as verification
import pages.auth.reset_password    as reset_password
import pages.user.home              as home_page
import pages.user.donor             as donor
import pages.admin.admin_main       as admin
import pages.user.request           as request
import pages.user.profile           as profile_page
import pages.auth.welcome           as welcome
import pages.admin.reports          as reports_page

from services.database.db import supabase as _public_supabase, SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("flet").setLevel(logging.WARNING)


# ═══════════════════════════════════════════════════════════════
#  SESSION HELPERS — Safe Multi-Platform Access
# ═══════════════════════════════════════════════════════════════

_SESSION_KEYS = [
    "access_token", "refresh_token",
    "user_id", "email", "email_verified",
    "role", "full_name", "blood_group",
]

def get_session(page: ft.Page) -> dict:
    """موجودہ پیج سیشن سے تمام ضروری کیز محفوظ طریقے سے پڑھنے کا فنکشن۔"""
    data: dict = {}
    try:
        if hasattr(page.session, "_Session__store"):
            store = page.session._Session__store
            for k in _SESSION_KEYS:
                v = store.get(k)
                if v is not None and v != "":
                    data[k] = v
        else:
            for k in _SESSION_KEYS:
                v = page.session.get(k) if hasattr(page.session, "get") else None
                if v is not None and v != "":
                    data[k] = v
    except Exception as ex:
        print(f"[SESSION GET ERROR] {ex}")
    return data


def set_session(page: ft.Page, data: dict) -> None:
    """موجودہ پیج سیشن میں ڈیٹا لکھنے کا فنکشن۔"""
    try:
        if hasattr(page.session, "_Session__store"):
            store = page.session._Session__store
            for k, v in data.items():
                store.set(k, str(v) if v is not None else "")
        else:
            for k, v in data.items():
                if hasattr(page.session, "set"):
                    page.session.set(k, str(v) if v is not None else "")
                elif hasattr(page.session, "set_value"):
                    page.session.set_value(k, str(v) if v is not None else "")
    except Exception as ex:
        print(f"[SESSION SET ERROR] {ex}")


def clear_session(page: ft.Page) -> None:
    """تمام سیشن کیز ختم کرنے کا فنکشن۔"""
    for k in _SESSION_KEYS:
        try:
            page.session.remove(k)
        except Exception:
            pass
    print("[SESSION] cleared ✅")


# ═══════════════════════════════════════════════════════════════
#  PER-REQUEST AUTHENTICATED CLIENT
# ═══════════════════════════════════════════════════════════════

def _make_authed_client(access_token: str, refresh_token: str):
    client = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())
    try:
        client.auth.set_session(access_token, refresh_token or "")
    except Exception as ex:
        print(f"[AUTH CLIENT] set_session failed: {ex}")
    return client


# ═══════════════════════════════════════════════════════════════
#  LOGO SYNC
# ═══════════════════════════════════════════════════════════════

async def sync_window_icon_async():
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(
            None,
            lambda: _public_supabase
                .table("app_settings")
                .select("value")
                .eq("key", "org_logo_url")
                .execute()
        )
        if res and res.data:
            db_url = res.data[0].get("value")
            if db_url:
                import requests

                def download_file():
                    response = requests.get(db_url, timeout=5)
                    if response.status_code == 200:
                        os.makedirs("assets", exist_ok=True)
                        with open("assets/logo.png", "wb") as f:
                            f.write(response.content)

                await loop.run_in_executor(None, download_file)
                print("[SYNC] Window icon synced successfully.")
    except Exception as e:
        print(f"[SYNC] Sync failed safely: {e}")


# ═══════════════════════════════════════════════════════════════
#  PROFILE FETCH
# ═══════════════════════════════════════════════════════════════

def fetch_profile(user_id: str, client, expect_verified: bool = False) -> dict | None:
    max_attempts = 6 if expect_verified else 1
    data = None
    for attempt in range(1, max_attempts + 1):
        try:
            res = (
                client.table("profiles")
                .select("role, email_verified, is_approved, full_name, blood_group")
                .eq("id", user_id)
                .single()
                .execute()
            )
            data = res.data if res else None
            print(f"[PROFILE attempt={attempt}] {data}")
            if expect_verified and data and not data.get("email_verified"):
                time.sleep(0.5)
                continue
            return data
        except Exception as ex:
            print(f"[PROFILE ERROR] {ex}")
            return None
    return data


# ═══════════════════════════════════════════════════════════════
#  MAIN APP ENTRY
# ═══════════════════════════════════════════════════════════════

async def main(page: ft.Page):
    # Assets Directory Configuration
    page.assets_dir = "assets"

    asyncio.create_task(sync_window_icon_async())

    # ── Page setup ────────────────────────────────────────────
    page.title      = "KHATTAK QOMI ITTEHAD PAKISTAN | خٹک قومی اتحاد پاکستان"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor    = "#FFF5F5"
    page.window.width     = 480
    page.window.min_width = 380
    page.fonts = {
        "Urdu": "https://fonts.gstatic.com/s/notosansnastaliqurdu/v19/"
                "LhW-MGl7WossbGkGFBpSXtOaJsn9MkSex4fQ.woff2"
    }
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="#C62828",
            secondary="#EF9A9A",
            surface="white",
            on_primary="white",
        ),
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    if os.path.exists("assets/logo.ico"):
        page.window_icon = "logo.ico"
    elif os.path.exists("assets/logo.png"):
        page.window_icon = "logo.png"
    else:
        page.window_icon = "icon.jpg"

    page.update()

    # Helper function to render view safely (supports sync and async views)
    async def get_view_obj(view_func):
        if asyncio.iscoroutinefunction(view_func):
            return await view_func(page)
        return view_func(page)

    # ── Route change handler ──────────────────────────────────
    async def route_change(e):
        page.views.clear()
        route = page.route
        print(f"[NAVIGATING TO] {route}")

        # ── 1. Supabase password-recovery link ────────────────
        if "access_token" in route or "type=recovery" in route or "error" in route:
            print("[ROUTE] Recovery/Reset link detected!")
            page.views.append(await get_view_obj(reset_password.view))
            page.update()
            return

        # ── 2. Strictly Unauthenticated Public Routes ─────────
        if route == "/welcome":
            page.views.append(await get_view_obj(welcome.view))
            page.update()
            return

        if route == "/login":
            page.views.append(await get_view_obj(login.view))
            page.update()
            return

        if route == "/register":
            page.views.append(await get_view_obj(register.view))
            page.update()
            return

        if route == "/verification":
            page.views.append(await get_view_obj(verification.view))
            page.update()
            return
            
        if route == "/reset_password":
            page.views.append(await get_view_obj(reset_password.view))
            page.update()
            return

        # ── 3. Session Check ──────────────────────────────────
        await asyncio.sleep(0.05)
        session_map   = get_session(page)
        access_token  = session_map.get("access_token", "")
        refresh_token = session_map.get("refresh_token", "")

        if not access_token:
            print("[ROUTE] No session → Redirecting to /login")
            page.views.append(await get_view_obj(login.view))
            page.update()
            return

        # ── 4. Authenticated Client & Profile Fetch ───────────
        user_id = session_map.get("user_id", "")
        authed_client = _make_authed_client(access_token, refresh_token)

        user_profile = await asyncio.to_thread(
            fetch_profile, user_id, authed_client
        )
        print(f"[PROFILE] {user_profile}")

        # ── 5. Email Verification Check ───────────────────────
        session_verified = session_map.get("email_verified", "").lower() in ("true", "1", "yes")
        
        if not session_verified:
            if user_profile and not user_profile.get("email_verified"):
                print("[ROUTE] Email not verified → /verification")
                page.views.append(await get_view_obj(verification.view))
                page.update()
                return
            elif user_profile and user_profile.get("email_verified"):
                set_session(page, {"email_verified": "True"})

        role = user_profile.get("role", "member") if user_profile else "member"
        print(f"[ROUTE SUCCESS] role={role} | route={route}")

        set_session(page, {
            "role":        role,
            "full_name":   (user_profile or {}).get("full_name",  "ممبر"),
            "blood_group": (user_profile or {}).get("blood_group", ""),
        })

        # ── 6. Authenticated & Protected Routes ───────────────
        try:
            if route in ("/", "/home"):
                page.views.append(await get_view_obj(home_page.view))

            elif route == "/admin":
                if role in ("admin", "head_admin"):
                    page.views.append(await get_view_obj(admin.view))
                else:
                    page.views.append(await get_view_obj(home_page.view))
            
            elif route == "/feedback":
                page.views.append(await get_view_obj(feedback_page.view))

            elif route == "/admin/reports": 
                page.views.append(await get_view_obj(reports_page.view)) 

            elif route == "/leaderboard":
                page.views.append(await get_view_obj(leaderboard_page.view))

            elif route == "/community-updates":
                page.views.append(await get_view_obj(community_updates.view))

            elif route == "/donor":
                page.views.append(await get_view_obj(donor.view))

            elif route == "/request":
                page.views.append(await get_view_obj(request.view))
            
            elif route == "/leaders":
                page.views.append(await get_view_obj(leaders.view))

            elif route == "/leaders_view":
                page.views.append(await get_view_obj(leaders_view.view))

            elif route == "/profile":
                page.views.append(await get_view_obj(profile_page.view))

            else:
                page.views.append(await get_view_obj(home_page.view))

        except Exception as ex:
            print(f"[ROUTE ROUTING ERROR] {ex}")
            page.views.append(await get_view_obj(home_page.view))

        # ── 7. Fallback Safety Guard ─────────────────────────
        if not page.views:
            print(f"[FALLBACK] Warning: page.views empty for '{route}'!")
            page.views.append(await get_view_obj(home_page.view if session_map.get("access_token") else welcome.view))

        # Single UI Batch Update (Prevents WS Reconnects)
        page.update()

    # ── View pop handler ──────────────────────────────────────
    async def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            page.update()
        else:
            await route_change(None)

    page.on_route_change = route_change
    page.on_view_pop     = view_pop

    # ── App initial execution ─────────────────────────────────
    session_map = get_session(page)
    if session_map.get("access_token"):
        print("[INIT] Active session found. Navigating to /home")
        page.go("/home")
    else:
        print("[INIT] No session. Navigating to /welcome")
        page.go("/welcome")


# ═══════════════════════════════════════════════════════════════
#  ENTRYPOINT (Streamlit Thread & Signal Bypass)
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    port = int(os.environ.get("PORT", 8550))

    # Streamlit Sub-thread میں signal.signal کا کریش روکنے کے لیے bypass:
    import signal
    import threading

    if threading.current_thread() is not threading.main_thread():
        orig_signal = signal.signal
        def safe_signal(sig, handler):
            try:
                return orig_signal(sig, handler)
            except ValueError:
                # Secondary thread میں سگنل ایرر کو چپ چاپ بائی پاس کریں
                return None
        signal.signal = safe_signal

    # Flet App کو رن کریں
    ft.app(
        target=main,
        port=port,
        view=ft.AppView.WEB_BROWSER,
    )
