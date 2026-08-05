


# ################### new 2/ remember login
from core.theme import Theme 
import re
import asyncio
import flet as ft
from services.database.db import supabase
from home_module.home_config import get_logo_control

# Email validation regex
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")

# ═══════════════════════════════════════════════════════════════
#  ERROR CLASSIFICATION & STYLES
# ═══════════════════════════════════════════════════════════════
ERRORS: dict[str, tuple[str, str, str]] = {
    "email_blank":   ("⚠ ای میل لازمی ہے!",          "Email is required!",               "error"),
    "email_invalid": ("⚠ ای میل کا فارمیٹ غلط ہے!",  "Invalid email format!",            "warn"),
    "pwd_blank":     ("⚠ پاس ورڈ لازمی ہے!",          "Password is required!",            "error"),
    "pwd_short":     ("⚠ پاس ورڈ کم از کم 6 حروف!",   "Minimum 6 characters required!",     "warn"),
    "wrong_creds":   ("⚠ ای میل یا پاس ورڈ غلط ہے!", "Wrong email or password!",            "error"),
    "not_found":     ("⚠ یہ اکاؤنٹ موجود نہیں!",      "Account not found!",                  "warn"),
    "not_confirmed": ("⚠ پہلے ای میل تصدیق کریں!",    "Please verify your email first!",    "info"),
    "network":       ("⚠ انٹرنیٹ چیک کریں!",          "Check your internet connection!",    "warn"),
    "rate_limit":    ("⚠ بہت زیادہ کوششیں!",           "Too many attempts! Try again later.", "warn"),
    "server":        ("⚠ سرور میں خرابی!",              "Server error, please try again.",    "error"),
}

TYPE_STYLE: dict[str, dict] = {
    "error": {
        "icon":   ft.Icons.ERROR_OUTLINE_ROUNDED,
        "color":  ft.Colors.RED_400,
        "bg":     ft.Colors.with_opacity(0.12, ft.Colors.RED_400),
        "border": ft.Colors.with_opacity(0.40, ft.Colors.RED_400),
        "label":  "Error",
    },
    "warn": {
        "icon":   ft.Icons.WARNING_AMBER_ROUNDED,
        "color":  ft.Colors.AMBER_700,
        "bg":     ft.Colors.with_opacity(0.12, ft.Colors.AMBER_700),
        "border": ft.Colors.with_opacity(0.40, ft.Colors.AMBER_700),
        "label":  "Warning",
    },
    "info": {
        "icon":   ft.Icons.INFO_OUTLINE_ROUNDED,
        "color":  ft.Colors.BLUE_400,
        "bg":     ft.Colors.with_opacity(0.12, ft.Colors.BLUE_400),
        "border": ft.Colors.with_opacity(0.40, ft.Colors.BLUE_400),
        "label":  "Info",
    },
}

def classify_error(ex_msg: str) -> str:
    m = ex_msg.lower()
    if "invalid" in m or "credentials" in m or "wrong" in m:
        return "wrong_creds"
    if "not found" in m or "no user" in m:
        return "not_found"
    if "not confirmed" in m or ("email" in m and "confirm" in m):
        return "not_confirmed"
    if "network" in m or "connect" in m or "timeout" in m:
        return "network"
    if "rate" in m or "limit" in m or "too many" in m:
        return "rate_limit"
    return "server"


# ── DESIGN TOKENS ────────────────────────────────────────────────
RED       = "#C62828"
RED_DARK  = "#B71C1C"
RED_LIGHT = "#FFEBEE"
WHITE     = "#FFFFFF"
BG        = "#FFF5F5"
GREY_TXT  = "#757575"
GREY_BDR  = "#BDBDBD"
W         = 370

FS = dict(
    border_radius=14,
    focused_border_color=RED,
    border_color=GREY_BDR,
    text_size=14,
    label_style=ft.TextStyle(color=GREY_TXT, size=13),
)


# ═══════════════════════════════════════════════════════════════
#  SESSION HELPER
# ═══════════════════════════════════════════════════════════════
def _save_session(page: ft.Page, data: dict) -> bool:
    try:
        if hasattr(page.session, "_Session__store"):
            store = page.session._Session__store
            for k, v in data.items():
                store.set(k, str(v) if v is not None else "")
            
            saved = store.get("access_token")
            print(f"[LOGIN] Session saved ✅ | token_preview={str(saved)[:20]}...")
            return True
        else:
            print("[LOGIN] Session save FAILED ❌: _Session__store not found")
            return False
    except Exception as ex:
        print(f"[LOGIN] Session save FAILED ❌: {ex}")
        return False


# ═══════════════════════════════════════════════════════════════
#  REMEMBER-ME (shared_preferences) HELPERS
#  Device-level persistent storage — survives app restarts.
# ═══════════════════════════════════════════════════════════════
REMEMBER_KEY_EMAIL = "remember_email"
REMEMBER_KEY_PWD   = "remember_pwd"
REMEMBER_KEY_FLAG   = "remember_flag"


async def _save_remember_me(page: ft.Page, email: str, pwd: str) -> bool:
    try:
        await page.shared_preferences.set(REMEMBER_KEY_EMAIL, email)
        await page.shared_preferences.set(REMEMBER_KEY_PWD, pwd)
        await page.shared_preferences.set(REMEMBER_KEY_FLAG, "1")
        print("[LOGIN] remember-me saved ✅ (async)")
        return True
    except Exception as ex:
        print(f"[LOGIN] remember-me save error: {ex}")
        return False


async def _clear_remember_me(page: ft.Page) -> None:
    try:
        await page.shared_preferences.remove(REMEMBER_KEY_EMAIL)
        await page.shared_preferences.remove(REMEMBER_KEY_PWD)
        await page.shared_preferences.remove(REMEMBER_KEY_FLAG)
        print("[LOGIN] remember-me cleared (async)")
    except Exception as ex:
        print(f"[LOGIN] remember-me clear error: {ex}")


async def _load_remember_me(page: ft.Page) -> tuple[str, str, bool]:
    try:
        flag = await page.shared_preferences.get(REMEMBER_KEY_FLAG)
        print(f"[LOGIN] remember-me load: flag={flag!r} (type={type(flag).__name__})")
        if flag == "1":
            email = await page.shared_preferences.get(REMEMBER_KEY_EMAIL) or ""
            pwd   = await page.shared_preferences.get(REMEMBER_KEY_PWD) or ""
            print(f"[LOGIN] remember-me load: email={email!r} pwd_len={len(pwd)}")
            return email, pwd, True
        print("[LOGIN] remember-me load: flag did not match '1', skipping auto-fill")
    except Exception as ex:
        print(f"[LOGIN] remember-me load error: {ex}")
    return "", "", False


# ═══════════════════════════════════════════════════════════════
#  NAVIGATION HELPER
# ═══════════════════════════════════════════════════════════
def _nav(page: ft.Page, route: str) -> None:
    async def _coro():
        try:
            await page.push_route(route)
        except Exception as ex:
            print(f"[LOGIN NAV] push_route failed: {ex}")
            try:
                page.go(route)
            except Exception:
                pass
    try:
        page.run_task(_coro)
    except Exception as ex:
        print(f"[LOGIN NAV] run_task error: {ex}")


# ═══════════════════════════════════════════════════════════════
#  VIEW ENTRY-POINT
# ═══════════════════════════════════════════════════════════════
def view(page: ft.Page) -> ft.View:

    _logging_in: list[bool] = [False]

    def safe_update() -> None:
        async def _coro():
            try:
                page.update()
            except Exception:
                pass
        try:
            page.run_task(_coro)
        except Exception:
            pass

    def goto(route: str) -> None:
        _nav(page, route)

    def show_snack(msg: str, color: str = RED) -> None:
        async def _coro():
            try:
                sb = ft.SnackBar(
                    content=ft.Text(msg, color=WHITE, weight=ft.FontWeight.BOLD, size=13),
                    bgcolor=color,
                    duration=3500,
                )
                page.overlay.append(sb)
                sb.open = True
                page.update()
            except Exception as ex:
                print(f"[LOGIN] SnackBar error: {ex}")
        try:
            page.run_task(_coro)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    #  ERROR DIALOG
    # ═══════════════════════════════════════════════════════════
    dialog_icon = ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, size=24)
    dialog_icon_wrap = ft.Container(
        content=dialog_icon,
        width=46, height=46,
        border_radius=23,
        alignment=ft.Alignment(0, 0),
    )
    dialog_label   = ft.Text("", size=12, weight=ft.FontWeight.W_600)
    dialog_urdu    = ft.Text("", size=15, rtl=True, text_align=ft.TextAlign.RIGHT, color="#1a1a1a")
    dialog_english = ft.Text("", size=13, color=GREY_TXT)

    ok_btn = ft.ElevatedButton(
        "OK",
        style=ft.ButtonStyle(
            color=WHITE,
            bgcolor={
                ft.ControlState.DEFAULT: RED,
                ft.ControlState.HOVERED: RED_DARK,
            },
            shape=ft.RoundedRectangleBorder(radius=9),
            padding=ft.padding.symmetric(horizontal=32, vertical=10),
        ),
    )

    dialog_card = ft.Container(
        width=310,
        padding=ft.padding.all(24),
        border_radius=16,
        bgcolor=WHITE,
        shadow=ft.BoxShadow(blur_radius=32, color="#33000000", offset=ft.Offset(0, 8)),
        content=ft.Column(
            spacing=16, tight=True,
            controls=[
                ft.Row(
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        dialog_icon_wrap,
                        ft.Column(
                            spacing=3, expand=True,
                            controls=[dialog_label, dialog_urdu, dialog_english],
                        ),
                    ],
                ),
                ft.Row(alignment=ft.MainAxisAlignment.END, controls=[ok_btn]),
            ],
        ),
    )

    overlay = ft.Container(
        visible=False,
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.45, ft.Colors.BLACK),
        alignment=ft.Alignment(0, 0),
        content=dialog_card,
    )

    def show_error(key: str) -> None:
        urdu_txt, en_txt, etype = ERRORS[key]
        st = TYPE_STYLE[etype]
        async def _coro():
            try:
                dialog_icon.name         = st["icon"]
                dialog_icon.color        = st["color"]
                dialog_icon_wrap.bgcolor = st["bg"]
                dialog_icon_wrap.border  = ft.border.all(1, st["border"])
                dialog_label.value       = st["label"]
                dialog_label.color       = st["color"]
                dialog_urdu.value        = urdu_txt
                dialog_english.value     = en_txt
                overlay.visible          = True
                page.update()
            except Exception as ex:
                print(f"[LOGIN] Dialog error: {ex}")
        try:
            page.run_task(_coro)
        except Exception:
            pass

    def close_dialog(e=None) -> None:
        overlay.visible = False
        safe_update()

    ok_btn.on_click = close_dialog

    # ═══════════════════════════════════════════════════════════
    #  INPUT FIELDS
    # ═══════════════════════════════════════════════════════════
    email_f = ft.TextField(
        label="Email * | ای میل *",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        hint_text="yourname@gmail.com",
        keyboard_type=ft.KeyboardType.EMAIL,
        autocorrect=False,
        width=W, **FS,
    )
    password_f = ft.TextField(
        label="Password * | پاس ورڈ *",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        hint_text="کم از کم 6 حروف | At least 6 chars",
        password=True,
        can_reveal_password=True,
        width=W, **FS,
    )

    remember_me_cb = ft.Checkbox(
        label="مجھے یاد رکھیں | Remember me",
        value=False,
        check_color=WHITE,
        active_color=RED,
        label_style=ft.TextStyle(size=12, color=GREY_TXT),
    )

    def ferr(field: ft.TextField, msg: str) -> None:
        field.error_text   = msg
        field.border_color = RED

    def freset(field: ft.TextField) -> None:
        field.error_text   = None
        field.border_color = GREY_BDR

    # ═══════════════════════════════════════════════════════════
    #  LOGIN BUTTON & LOADING STATE
    # ═══════════════════════════════════════════════════════════
    login_btn = ft.ElevatedButton(
        content=ft.Text("Login | لاگ ان کریں", weight=ft.FontWeight.BOLD, size=15),
        style=ft.ButtonStyle(
            color=WHITE,
            bgcolor={
                ft.ControlState.DEFAULT: RED,
                ft.ControlState.HOVERED: RED_DARK,
            },
            shape=ft.RoundedRectangleBorder(radius=13),
            elevation=4,
        ),
        width=W, height=52,
    )

    def _set_btn_loading(loading: bool) -> None:
        if loading:
            login_btn.disabled = True
            login_btn.content  = ft.Row(
                [
                    ft.ProgressRing(width=18, height=18, color=WHITE, stroke_width=2.5),
                    ft.Text("انتظار کریں... | Please wait…", color=WHITE, size=13),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
            )
        else:
            login_btn.disabled = False
            login_btn.content  = ft.Text("Login | لاگ ان کریں", weight=ft.FontWeight.BOLD, size=15)

    # ═══════════════════════════════════════════════════════════
    #  MAIN LOGIN FLOW
    # ═══════════════════════════════════════════════════════════
    async def async_login_flow(email: str, pwd: str):
        try:
            loop = asyncio.get_running_loop()

            # ── Supabase Auth ──────────────────────────────────
            res = await loop.run_in_executor(
                None,
                lambda: supabase.auth.sign_in_with_password({"email": email, "password": pwd})
            )

            if not (res and res.user and res.session):
                show_error("wrong_creds")
                show_snack(ERRORS["wrong_creds"][1])
                return

            # ── Profile Fetch ──────────────────────────────────
            profile_data: dict = {}
            try:
                pr = await loop.run_in_executor(
                    None,
                    lambda: supabase.table("profiles")
                    .select("email_verified, role, full_name, blood_group")
                    .eq("id", res.user.id)
                    .single()
                    .execute()
                )
                profile_data = pr.data or {}
            except Exception as ex:
                print(f"[LOGIN] Exception TYPE: {type(ex).__name__}")
                print(f"[LOGIN] Exception FULL: {repr(ex)}")  # ← full detail
                print(f"[LOGIN] Exception STR: {str(ex)}")
                key = classify_error(str(ex))

            # ── Prepare Session Data ─────────────────────────
            session_data = {
                "access_token":   str(res.session.access_token),
                "refresh_token":  str(res.session.refresh_token),
                "user_id":        str(res.user.id),
                "email":          str(res.user.email),
                "email_verified": str(profile_data.get("email_verified", False)),
                "role":           str(profile_data.get("role", "member")),
                "full_name":      str(profile_data.get("full_name", "ممبر")),
                "blood_group":    str(profile_data.get("blood_group", "")),
            }

            # ── Save Session (Flet 0.84 Internal Store) ────────
            saved_ok = _save_session(page, session_data)
            if not saved_ok:
                show_snack("Session error! Try again.", ft.Colors.ORANGE_700)
                return

            # ── Remember Me (shared_preferences, device-level) ─────
            print(f"[LOGIN] DEBUG: reached remember-me block, checkbox value={remember_me_cb.value!r}")
            try:
                if remember_me_cb.value:
                    ok = await _save_remember_me(page, email, pwd)
                    print(f"[LOGIN] DEBUG: save_remember_me returned {ok}")
                else:
                    await _clear_remember_me(page)
                    print("[LOGIN] DEBUG: cleared remember-me (checkbox was off)")
            except Exception as rmex:
                print(f"[LOGIN] DEBUG: remember-me block raised: {rmex!r}")

            # **SUCCESS SNACKBAR SHOW KARNA**
            show_snack("Login Successful!       |     !لاگ ان کامیاب رہا ", ft.Colors.GREEN_700)

            # ── Determine Route ──────────────────────────────
            is_verified = profile_data.get("email_verified", False)
            route = "/home" if is_verified else "/verification"
            print(f"[LOGIN] success → routing to: {route}")
            

            await asyncio.sleep(1.0) # Snack bar dekhne ke liye thora rukein
            _nav(page, route)

        except Exception as ex:
            print(f"[LOGIN] Exception: {ex}")
            key = classify_error(str(ex))
            show_error(key)
            show_snack(ERRORS[key][1])

            if key == "wrong_creds":
                ferr(email_f,    "غلط | Wrong")
                ferr(password_f, "غلط | Wrong")
                # Wrong saved creds — clear them so we don't loop auto-login forever
                await _clear_remember_me(page)
            elif key == "not_found":
                ferr(email_f, "موجود نہیں | Not found")

            safe_update()

            if key == "not_confirmed":
                _nav(page, "/verification")

        finally:
            _logging_in[0] = False
            _set_btn_loading(False)
            safe_update()

    # ── Login Trigger ─────────────────────────────────────────
    def on_login(e) -> None:
        if _logging_in[0]:
            return

        email = (email_f.value or "").strip()
        pwd   = (password_f.value or "")

        freset(email_f)
        freset(password_f)

        if not email:
            ferr(email_f, "لازمی | Required")
            page.update()
            show_error("email_blank")
            return
        if not EMAIL_RE.match(email):
            ferr(email_f, "غلط فارمیٹ | Invalid format")
            page.update()
            show_error("email_invalid")
            return
        if not pwd:
            ferr(password_f, "لازمی | Required")
            page.update()
            show_error("pwd_blank")
            return
        if len(pwd) < 6:
            ferr(password_f, "کم از کم 6 حروف | Min 6 chars")
            page.update()
            show_error("pwd_short")
            return

        _logging_in[0] = True
        _set_btn_loading(True)
        page.update()
        page.run_task(async_login_flow, email, pwd)

    login_btn.on_click   = on_login
    email_f.on_submit    = on_login
    password_f.on_submit = on_login

    # ═══════════════════════════════════════════════════════════
    #  AUTO-FILL ON LOAD (WITHOUT AUTO-LOGIN TRIGER)
    # ═══════════════════════════════════════════════════════════
    def _check_remembered_login() -> None:
        async def _coro():
            try:
                print("[LOGIN] credentials restore: started")
                await asyncio.sleep(0.3)

                saved_email, saved_pwd, has_saved = await _load_remember_me(page)
                if not has_saved or not saved_email or not saved_pwd:
                    print(f"[LOGIN] credentials restore: nothing to restore")
                    return

                # **CRITICAL CHANGE**: data textfields mein dalega aur checkbox true hoga, login trigger nahi hoga!
                email_f.value = saved_email
                password_f.value = saved_pwd
                remember_me_cb.value = True
                page.update()
                print("[LOGIN] credentials auto-filled successfully. Waiting for manual click.")

            except Exception as ex:
                print(f"[LOGIN] auto-fill check error: {ex}")

        try:
            page.run_task(_coro)
        except Exception as ex:
            print(f"[LOGIN] auto-fill trigger error: {ex}")

    _check_remembered_login()

    # ── Google Login Button ───────────────────────────────────
    async def show_auto_popup(e):
        try:
            google_login_btn.content = ft.Text(
                "گوگل لاگ ان دستیاب نہیں، ای میل درج کریں", 
                weight=ft.FontWeight.W_500,
                size=16,
                color=WHITE
            )
            google_login_btn.style.bgcolor = ft.Colors.RED_600
            page.update()
            
            await asyncio.sleep(3)
            
            google_login_btn.content = ft.Text("Sign in with Google", weight=ft.FontWeight.W_500)
            google_login_btn.style.bgcolor = None
            page.update()
            
        except Exception as ex:
            print(f"[POPUP ERROR]: {ex}")

    google_login_btn = ft.ElevatedButton(
        content=ft.Text("Sign in with Google", weight=ft.FontWeight.W_500),
        icon=ft.Icons.G_MOBILEDATA_ROUNDED,
        width=W,
        height=48,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        on_click=show_auto_popup,
    )
    
    # ═══════════════════════════════════════════════════════════
    #  UI ASSEMBLY
    # ═══════════════════════════════════════════════════════════
    logo_container = get_logo_control(logo_url=None, width=100, height=100)
    
    login_ui = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
        controls=[
            logo_container, 
            ft.Container(height=12),
            ft.Text(
                "KHATTAK QAOMI ITTEHAD PAKISTAN",
                size=20, weight=ft.FontWeight.BOLD,
                color=RED_DARK, no_wrap=True,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Text(
                "خٹک قومی اتحاد پاکستان",
                size=18, color=RED_DARK, no_wrap=True,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Container(height=18),

            ft.Card(
                elevation=12,
                shape=ft.RoundedRectangleBorder(radius=22),
                content=ft.Container(
                    bgcolor=WHITE,
                    border_radius=22,
                    padding=ft.padding.symmetric(horizontal=28, vertical=26),
                    width=430,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Row([
                                ft.Icon(ft.Icons.STAR, color=RED, size=10),
                                ft.Text(" لازمی فیلڈز | Required fields", size=10, color=GREY_TXT, italic=True),
                            ], spacing=2),

                            email_f,
                            password_f,

                            remember_me_cb,

                            ft.Row([
                                ft.Container(expand=True),
                                ft.TextButton(
                                    "Forgot Password? | پاس ورڈ بھولے؟",
                                    style=ft.ButtonStyle(color=RED, padding=ft.padding.all(0)),
                                    on_click=lambda _: goto("/reset_password"),
                                ),
                            ]),

                            login_btn,

                            ft.Row([
                                ft.Divider(color="#EEEEEE", thickness=1, expand=True),
                                ft.Text("  یا  |  or  ", size=11, color="#BDBDBD"),
                                ft.Divider(color="#EEEEEE", thickness=1, expand=True),
                            ]),

                            google_login_btn,

                            ft.Row(
                                [
                                    ft.Text("نئے ممبر؟ | New member?", color=GREY_TXT, size=13),
                                    ft.TextButton(
                                        "Register | رجسٹر کریں",
                                        style=ft.ButtonStyle(color=RED),
                                        on_click=lambda _: goto("/register"),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                    ),
                ),
            ),

            ft.Container(height=16),
            ft.Text(
                "آپ کا ڈیٹا محفوظ ہے | Your data is secure  🔒",
                size=11, color="#BDBDBD",
                text_align=ft.TextAlign.CENTER,
            ),
        ],
    )

    return ft.View(
        route="/login",
        bgcolor=BG,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Stack(
                expand=True,
                controls=[
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                        padding=ft.padding.symmetric(vertical=30),
                        content=login_ui,
                    ),
                    overlay,
                ],
            )
        ],
    )