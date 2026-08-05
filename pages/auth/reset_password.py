# ====================================================================
#  reset_password.py  –  Reset Password via Phone OTP (Fully Fixed)
#  Flow: Phone Entry → Firebase OTP → New Password → /login
# ====================================================================
from core.theme import Theme 
import re
import asyncio
import hashlib
import secrets
import base64
import flet as ft
from services.database.db import supabase, supabase_admin
from services.firebase.firebase_otp import send_otp, verify_otp
from home_module.home_config import get_session, set_session
from pages.auth.otp_dialog import show_otp_dialog

# ── theme ────────────────────────────────────────────────────────
C = {
    "primary":    "#C62828",
    "primary_dk": "#B71C1C",
    "primary_lt": "#FFEBEE",
    "primary_pl": "#FFCDD2",
    "green":      "#2E7D32",
    "green_lt":   "#E8F5E9",
    "orange":     "#E65100",
    "grey":       "#757575",
    "grey_lt":    "#9E9E9E",
    "grey_bdr":   "#E0E0E0",
    "text":       "#212121",
    "bg":         "#FFF8F8",
    "white":      "#FFFFFF",
    "shadow":     "#22C62828",
}

_PHONE_RE = re.compile(r"(03\d{9}|\+923\d{9})")


def _to_e164(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("+"):
        return raw
    if raw.startswith("03"):
        return "+92" + raw[1:]
    return "+92" + raw


# ════════════════════════════════════════════════════════════════
#  PASSWORD HASHER
# ════════════════════════════════════════════════════════════════
class PasswordHasher:
    @staticmethod
    def hash_password(password: str) -> tuple[str, str]:
        salt_bytes = secrets.token_bytes(16)
        iterations = 100000
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt_bytes,
            iterations
        )
        salt_b64 = base64.b64encode(salt_bytes).decode('utf-8')
        hash_b64 = base64.b64encode(hash_bytes).decode('utf-8')

        return salt_b64, hash_b64


# ================================================================
#  VIEW  —  3-step wizard in a single view
# ================================================================
def view(page: ft.Page):

    _step       = [0]
    _phone        = [""]
    _session_info = [""]

    password_hasher = PasswordHasher()

    # ── helpers ──────────────────────────────────────────────────
    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    def show_alert(text: str, color: str = C["primary"]):
        icon = (
            ft.Icons.CHECK_CIRCLE_OUTLINE   if color == C["green"]  else
            ft.Icons.WARNING_AMBER_OUTLINED if color == C["orange"] else
            ft.Icons.ERROR_OUTLINE
        )
        dlg = ft.AlertDialog(
            modal=False,
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(spacing=10, controls=[
                ft.Icon(icon, color=color, size=22),
                ft.Text(text, size=13, color=C["text"], expand=True),
            ]),
            actions=[
                ft.TextButton(
                    "OK | ٹھیک ہے",
                    on_click=lambda _: _close_dlg(dlg),
                    style=ft.ButtonStyle(color=color),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        safe_update()

    def _close_dlg(dlg):
        dlg.open = False
        safe_update()

    _field_style = dict(
        border_radius=14,
        focused_border_color=C["primary"],
        border_color=C["grey_bdr"],
        bgcolor=C["white"],
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
        width=340,
        text_size=14,
    )

    # ════════════════════════════════════════════════════════════
    #  STEP 0  —  Phone Entry
    # ════════════════════════════════════════════════════════════
    phone_f = ft.TextField(
        label="Phone Number | فون نمبر *",
        hint_text="03xxxxxxxxx  or  +923xxxxxxxxx",
        prefix_icon=ft.Icons.PHONE_OUTLINED,
        keyboard_type=ft.KeyboardType.PHONE,
        **_field_style,
    )

    send_btn = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.SMS_OUTLINED, color="white", size=18),
            ft.Text("Send OTP | کوڈ بھیجیں",
                    color="white", weight=ft.FontWeight.BOLD, size=14),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(
            bgcolor=C["primary"],
            shape=ft.RoundedRectangleBorder(radius=12),
            overlay_color=C["primary_dk"],
        ),
        width=340, height=50,
        on_click=lambda e: page.run_task(_on_send_otp, e),
    )

    def _set_send_loading(active: bool):
        send_btn.disabled = active
        send_btn.content = (
            ft.Row([ft.ProgressRing(width=18, height=18, color="white", stroke_width=2.5)],
                   alignment=ft.MainAxisAlignment.CENTER)
            if active else
            ft.Row([
                ft.Icon(ft.Icons.SMS_OUTLINED, color="white", size=18),
                ft.Text("Send OTP | کوڈ بھیجیں",
                        color="white", weight=ft.FontWeight.BOLD, size=14),
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        )
        safe_update()

    async def _on_send_otp(e):
        raw = (phone_f.value or "").strip()
        if not raw or not _PHONE_RE.fullmatch(raw):
            phone_f.error_text = "Format: 03xxxxxxxxx or +923xxxxxxxxx"
            phone_f.border_color = C["primary"]
            safe_update()
            return

        phone_f.error_text = None
        phone_f.border_color = C["grey_bdr"]
        safe_update()

        e164 = _to_e164(raw)

        def _check():
            try:
                res = supabase.table("profiles").select("id").eq("phone", e164).limit(1).execute()
                return bool(res.data)
            except Exception:
                return False

        exists = await asyncio.to_thread(_check)
        if not exists:
            show_alert(
                "⚠ No account found with this number.\nاس نمبر سے کوئی اکاؤنٹ نہیں ملا۔",
                C["orange"],
            )
            return

        _set_send_loading(True)

        def _send():
            return send_otp(e164)

        ok, session_info, err = await asyncio.to_thread(_send)
        _set_send_loading(False)

        if ok:
            _phone[0] = e164
            _session_info[0] = session_info
            show_otp_dialog(
                page=page,
                phone_number=e164,
                on_verify_submit=lambda code, dlg: page.run_task(
                    _on_otp_verify, code, dlg
                ),
            )
        else:
            msg = str(err or "").lower()
            if "rate" in msg or "many" in msg:
                show_alert(
                    "⚠ Too many attempts. Wait 1 minute.\nبہت زیادہ کوششیں، 1 منٹ بعد ٹرائی کریں۔",
                    C["orange"],
                )
            else:
                show_alert(f"⚠ Could not send OTP: {str(err)[:60]}")

    # ════════════════════════════════════════════════════════════
    #  STEP 1  —  OTP verification callback
    # ════════════════════════════════════════════════════════════
    async def _on_otp_verify(code: str, dialog: ft.AlertDialog):
        if len(code) != 6 or not code.isdigit():
            show_alert("⚠ Enter the complete 6-digit code.\nمکمل 6 ہندسوں کا کوڈ درج کریں۔")
            return

        dialog.open = False
        safe_update()

        def _verify():
            return verify_otp(_session_info[0], code)

        ok, _verified_phone, err = await asyncio.to_thread(_verify)

        if ok:
            set_session(page, {"reset_phone": _phone[0]})
            verified_badge.content.controls[1].value = f"Verified: {_phone[0]}"
            verified_badge.visible = True
            _go_step(2)
        else:
            show_alert(
                f"⚠ Invalid OTP. {err or ''}\nغلط کوڈ، دوبارہ کوشش کریں۔"
            )

    # ════════════════════════════════════════════════════════════
    #  STEP 2  —  New Password
    # ════════════════════════════════════════════════════════════
    def _strength(pwd: str):
        score = sum([
            len(pwd) >= 8,
            any(c.isupper() for c in pwd),
            any(c.isdigit() for c in pwd),
            any(c in "!@#$%^&*()_+-=" for c in pwd),
        ])
        labels = ["", "Weak | کمزور", "Fair | ٹھیک", "Good | اچھا", "Strong | مضبوط"]
        colors = ["", "#E53935", "#FB8C00", "#43A047", "#2E7D32"]
        return score, labels[score] if score else "", colors[score] if score else C["grey_bdr"]

    strength_bar = ft.ProgressBar(
        value=0, bgcolor="#F0F0F0",
        color=C["primary"], border_radius=4,
        height=6, width=340,
    )
    strength_lbl = ft.Text("", size=11, color=C["grey_lt"])

    def on_pass_change(e):
        score, label, color = _strength(pass_f.value or "")
        strength_bar.value = score / 4
        strength_bar.color = color
        strength_lbl.value = label
        strength_lbl.color = color
        safe_update()

    verified_badge = ft.Container(
        visible=False,
        border_radius=12,
        bgcolor=C["primary_lt"],
        border=ft.border.all(1.5, C["primary_pl"]),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        content=ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER, controls=[
            ft.Icon(ft.Icons.VERIFIED_USER_OUTLINED, color=C["green"], size=18),
            ft.Text("", size=13, weight=ft.FontWeight.W_600, color=C["primary_dk"]),
        ]),
    )

    pass_f = ft.TextField(
        label="New Password | نیا پاس ورڈ",
        password=True, can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK_OUTLINED,
        on_change=on_pass_change,
        **_field_style,
    )

    confirm_f = ft.TextField(
        label="Confirm Password | پاس ورڈ کی تصدیق",
        password=True, can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK_CLOCK_OUTLINED,
        **_field_style,
    )

    update_btn = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.LOCK_OPEN_ROUNDED, color="white", size=18),
            ft.Text("Update Password | پاس ورڈ تبدیل کریں",
                    color="white", weight=ft.FontWeight.BOLD, size=14),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(
            bgcolor=C["primary"],
            shape=ft.RoundedRectangleBorder(radius=12),
            overlay_color=C["primary_dk"],
        ),
        width=340, height=50,
        on_click=lambda e: page.run_task(_on_update_password, e),
    )

    def _set_update_loading(active: bool):
        update_btn.disabled = active
        update_btn.content = (
            ft.Row([ft.ProgressRing(width=18, height=18, color="white", stroke_width=2.5)],
                   alignment=ft.MainAxisAlignment.CENTER)
            if active else
            ft.Row([
                ft.Icon(ft.Icons.LOCK_OPEN_ROUNDED, color="white", size=18),
                ft.Text("Update Password | پاس ورڈ تبدیل کریں",
                        color="white", weight=ft.FontWeight.BOLD, size=14),
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        )
        safe_update()

    async def _on_update_password(e):
        pwd     = (pass_f.value or "").strip()
        confirm = (confirm_f.value or "").strip()

        if not pwd or not confirm:
            show_alert("⚠ Please fill all fields.\nبراہ کرم تمام فیلڈز پُر کریں۔")
            return
        if len(pwd) < 8:
            show_alert("⚠ Password must be at least 8 characters.\nپاس ورڈ کم از کم 8 حروف کا ہونا چاہیے۔")
            return
        if pwd != confirm:
            show_alert("⚠ Passwords do not match.\nپاس ورڈز آپس میں نہیں ملتے۔")
            return

        _set_update_loading(True)
        phone = _phone[0] or get_session(page).get("reset_phone", "")

        def _work():
            try:
                # 1. phone سے user ID لو
                print(f"[RESET] step1: fetching uid for phone={phone!r}")
                res = supabase.table("profiles").select("id").eq("phone", phone).limit(1).execute()
                if not res.data: 
                    return False, "No account found for this phone number. | اس نمبر سے کوئی اکاؤنٹ نہیں ملا۔"
                
                uid = res.data[0]["id"]
                print(f"[RESET] step1 done: uid={uid}")
        
                # 2. نیا hash اور salt بناؤ
                new_salt, new_hash = password_hasher.hash_password(pwd)
                print("[RESET] step2 done: hash generated")
        
                # 3. Supabase Auth پاس ورڈ update کرو (تاکہ لاگ ان کام کرے)
                print("[RESET] step3: calling admin.update_user_by_id...")
                supabase_admin.auth.admin.update_user_by_id(uid, {"password": pwd})
                print("[RESET] step3 done: auth password updated")
        
                # 4. profiles table میں hash اور salt save کرو (تاکہ کسٹم لاگ ان بھی سنک رہے)
                print("[RESET] step4: updating profiles table...")
                supabase_admin.table("profiles").update({
                    "password_hash": new_hash,
                    "password_salt": new_salt,
                }).eq("id", uid).execute()
                print("[RESET] step4 done: profile updated")
        
                return True, None
        
            except Exception as ex:
                print(f"[RESET] _work EXCEPTION: {ex}")
                return False, str(ex)

        # رن ٹاسک کے ذریعے بیک اینڈ تھریڈ کو فائر کریں
        success, err_msg = await asyncio.to_thread(_work)
        _set_update_loading(False)

        if success:
            show_alert("✅ Password updated successfully!\nپاس ورڈ کامیابی سے تبدیل ہو گیا ہے۔", C["green"])
            await asyncio.sleep(2)
            page.go("/login")
        else:
            show_alert(f"⚠ Database Error: {err_msg}")

    # ════════════════════════════════════════════════════════════
    #  STEP CONTAINERS
    # ════════════════════════════════════════════════════════════
    step_containers = [
        # step 0 — phone entry
        ft.Container(
            visible=True,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    ft.Container(
                        width=90, height=90, border_radius=45,
                        bgcolor=C["primary_lt"],
                        border=ft.border.all(2, C["primary_pl"]),
                        content=ft.Icon(ft.Icons.PHONE_ANDROID_ROUNDED,
                                        size=48, color=C["primary"]),
                        alignment=ft.Alignment.CENTER,
                        shadow=ft.BoxShadow(blur_radius=24, color=C["shadow"],
                                            offset=ft.Offset(0, 6)),
                    ),
                    ft.Text("Reset Password", size=26,
                            weight=ft.FontWeight.BOLD, color=C["primary_dk"]),
                    ft.Text("پاس ورڈ دوبارہ ترتیب دیں", size=15, color=C["primary"]),
                    ft.Text(
                        "Enter your registered phone number.\nAn OTP will be sent for verification.",
                        size=13, color=C["grey"], text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Card(
                        elevation=8, shadow_color=C["shadow"],
                        shape=ft.RoundedRectangleBorder(radius=22),
                        content=ft.Container(
                            bgcolor=C["white"], border_radius=22,
                            padding=ft.padding.symmetric(horizontal=28, vertical=28),
                            width=400,
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=16,
                                controls=[
                                    ft.Row([
                                        ft.Icon(ft.Icons.PHONE_OUTLINED,
                                                color=C["primary"], size=20),
                                        ft.Text("Phone Verification | فون تصدیق",
                                                size=14, weight=ft.FontWeight.BOLD,
                                                color=C["primary_dk"]),
                                    ], spacing=10),
                                    ft.Divider(color=C["primary_pl"], thickness=1),
                                    phone_f,
                                    send_btn,
                                ],
                            ),
                        ),
                    ),
                    ft.TextButton(
                        "Back to Login | لاگ ان پر واپس",
                        style=ft.ButtonStyle(color=C["grey"]),
                        on_click=lambda _: page.go("/login"),
                    ),
                ],
            ),
        ),

        # step 2 — new password
        ft.Container(
            visible=False,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    ft.Container(
                        width=90, height=90, border_radius=45,
                        bgcolor=C["primary_lt"],
                        border=ft.border.all(2, C["primary_pl"]),
                        content=ft.Icon(ft.Icons.LOCK_OPEN_ROUNDED,
                                        size=48, color=C["primary"]),
                        alignment=ft.Alignment.CENTER,
                        shadow=ft.BoxShadow(blur_radius=24, color=C["shadow"],
                                            offset=ft.Offset(0, 6)),
                    ),
                    ft.Text("Create New Password", size=26,
                            weight=ft.FontWeight.BOLD, color=C["primary_dk"]),
                    ft.Text("نیا پاس ورڈ بنائیں", size=15, color=C["primary"]),
                    ft.Text(
                        "Your phone has been verified.\nPlease set a strong new password.",
                        size=13, color=C["grey"], text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Card(
                        elevation=8, shadow_color=C["shadow"],
                        shape=ft.RoundedRectangleBorder(radius=22),
                        content=ft.Container(
                            bgcolor=C["white"], border_radius=22,
                            padding=ft.padding.symmetric(horizontal=28, vertical=28),
                            width=400,
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=16,
                                controls=[
                                    verified_badge,
                                    pass_f,
                                    ft.Column(spacing=4, controls=[
                                        strength_bar, strength_lbl,
                                    ]),
                                    confirm_f,
                                    ft.Container(height=4),
                                    update_btn,
                                ],
                            ),
                        ),
                    ),
                ],
            ),
        ),
    ]

    # ── step switcher ────────────────────────────────────────────
    def _go_step(idx: int):
        container_idx = 0 if idx == 0 else 1
        for i, c in enumerate(step_containers):
            c.visible = (i == container_idx)
        _step[0] = idx
        safe_update()

    # ── layout ──────────────────────────────────────────────────
    return ft.View(
        route="/reset_password",
        bgcolor=C["bg"],
        padding=20,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/login"),
                tooltip="Back | واپس",
            ),
            title=ft.Column(spacing=0, controls=[
                ft.Text("Reset Password", size=16,
                        weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("پاس ورڈ ری سیٹ", size=11, color=C["primary_pl"]),
            ]),
            bgcolor=C["primary"],
            elevation=0,
            center_title=False,
        ),
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                    spacing=0,
                    controls=step_containers,
                ),
            ),
        ],
    )



