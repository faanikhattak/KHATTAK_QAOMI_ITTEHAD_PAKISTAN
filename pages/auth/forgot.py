# ================================================================
#  forgot.py  –  Forgot Password | Phone OTP Flow
#  Target: Flet 0.84+  |  Supabase + Firebase SMS
# ================================================================
from core.theme import Theme 
import re
import asyncio
import flet as ft
from services.database.db import supabase
from services.firebase.firebase_otp import send_otp
from home_module.home_config import set_session
from pages.auth.otp_dialog import show_otp_dialog   # shared OTP dialog

# ── theme tokens ────────────────────────────────────────────────
C = {
    "primary":    "#C62828",
    "primary_dk": "#B71C1C",
    "primary_lt": "#FFEBEE",
    "primary_pl": "#FFCDD2",
    "green":      "#2E7D32",
    "grey":       "#757575",
    "grey_lt":    "#9E9E9E",
    "text":       "#212121",
    "bg":         "#FFF8F8",
    "white":      "#FFFFFF",
}

# ── phone validator (Pakistan: 03xxxxxxxxx / +923xxxxxxxxx) ─────
def _valid_phone(p: str) -> bool:
    return bool(re.fullmatch(r"(03\d{9}|\+923\d{9})", p.strip()))


# ================================================================
#  VIEW
# ================================================================
def view(page: ft.Page):

    # ── helpers ─────────────────────────────────────────────────
    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    def show_alert(text: str, color: str = C["primary"]):
        icon = (
            ft.Icons.CHECK_CIRCLE_OUTLINE  if color == C["green"] else
            ft.Icons.WARNING_AMBER_OUTLINED if color == "#E65100" else
            ft.Icons.ERROR_OUTLINE
        )
        dlg = ft.AlertDialog(
            modal=False,
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(icon, color=color, size=22),
                    ft.Text(text, size=13, color=C["text"], expand=True),
                ],
            ),
            actions=[
                ft.TextButton(
                    "OK | ٹھیک ہے",
                    on_click=lambda _: _close(dlg),
                    style=ft.ButtonStyle(color=color),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        safe_update()

    def _close(dlg):
        dlg.open = False
        safe_update()

    def set_loading(active: bool):
        send_btn.disabled = active
        send_btn.content = (
            ft.Row(
                [ft.ProgressRing(width=18, height=18, color="white", stroke_width=2.5)],
                alignment=ft.MainAxisAlignment.CENTER,
            )
            if active
            else ft.Row(
                [
                    ft.Icon(ft.Icons.SEND_ROUNDED, color="white", size=18),
                    ft.Text(
                        "Send OTP | کوڈ بھیجیں",
                        color="white", weight=ft.FontWeight.BOLD, size=14,
                    ),
                ],
                spacing=8, alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        safe_update()

    # ── OTP verify callback ──────────────────────────────────────
    async def _process_forgot_otp(code: str, dialog: ft.AlertDialog):
        """Called when user submits the 6-digit code from the OTP dialog."""
        from services.firebase.firebase_otp import verify_otp  # lazy import

        if len(code) != 6 or not code.isdigit():
            show_alert("⚠ Please enter the complete 6-digit code.\nبراہ کرم 6 ہندسوں کا کوڈ مکمل درج کریں۔")
            return

        # close dialog first
        dialog.open = False
        safe_update()

        phone = phone_tf.value.strip()

        def _verify():
            ok, err = verify_otp(phone, code)
            return ok, err

        ok, err = await asyncio.to_thread(_verify)

        if ok:
            # save verified phone to session; navigate to reset password
            set_session(page, "reset_phone", phone)
            show_alert(
                "✓ Phone verified! Redirecting…\nتصدیق کامیاب! آگے جا رہے ہیں۔",
                C["green"],
            )
            await asyncio.sleep(1.2)
            page.route = "/reset_password"
            safe_update()
        else:
            show_alert(f"⚠ Invalid OTP. {err or ''}\nغلط کوڈ، دوبارہ کوشش کریں۔")

    # ── Send OTP click ───────────────────────────────────────────
    async def on_send_click(e):
        phone = (phone_tf.value or "").strip()

        if not phone:
            phone_tf.error_text = "Required | ضروری ہے"
            safe_update()
            return

        if not _valid_phone(phone):
            phone_tf.error_text = "Format: 03xxxxxxxxx or +923xxxxxxxxx"
            safe_update()
            return

        phone_tf.error_text = None
        set_loading(True)

        def _send():
            return send_otp(phone)

        ok, err = await asyncio.to_thread(_send)
        set_loading(False)

        if ok:
            show_otp_dialog(
                page=page,
                phone_number=phone,
                on_verify_submit=lambda code, dlg: page.run_task(
                    _process_forgot_otp, code, dlg
                ),
            )
        else:
            msg = str(err or "").lower()
            if "rate" in msg:
                show_alert("⚠ Too many attempts. Wait 1 minute.\nبہت زیادہ کوششیں، 1 منٹ بعد ٹرائی کریں۔", "#E65100")
            else:
                show_alert(f"⚠ Could not send OTP: {str(err)[:60]}")

    # ── UI controls ──────────────────────────────────────────────
    phone_tf = ft.TextField(
        label="Phone Number | فون نمبر",
        hint_text="03xxxxxxxxx  یا  +923xxxxxxxxx",
        prefix_icon=ft.Icons.PHONE_OUTLINED,
        keyboard_type=ft.KeyboardType.PHONE,
        border_radius=14,
        focused_border_color=C["primary"],
        border_color="#E0E0E0",
        bgcolor=C["white"],
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
        width=340,
        text_size=14,
    )

    send_btn = ft.ElevatedButton(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.SEND_ROUNDED, color="white", size=18),
                ft.Text(
                    "Send OTP | کوڈ بھیجیں",
                    color="white", weight=ft.FontWeight.BOLD, size=14,
                ),
            ],
            spacing=8, alignment=ft.MainAxisAlignment.CENTER,
        ),
        style=ft.ButtonStyle(
            bgcolor=C["primary"],
            shape=ft.RoundedRectangleBorder(radius=12),
            overlay_color=C["primary_dk"],
        ),
        width=340, height=50,
        on_click=lambda e: page.run_task(on_send_click, e),
    )

    # ── layout ──────────────────────────────────────────────────
    return ft.View(
        route="/forgot",
        bgcolor=C["bg"],
        padding=20,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=0,
                    controls=[

                        # ── hero ────────────────────────────────
                        ft.Container(
                            width=90, height=90, border_radius=45,
                            bgcolor=C["primary_lt"],
                            border=ft.border.all(2, C["primary_pl"]),
                            content=ft.Icon(
                                ft.Icons.LOCK_RESET_ROUNDED,
                                size=48, color=C["primary"],
                            ),
                            alignment=ft.alignment.center,
                            shadow=ft.BoxShadow(
                                blur_radius=24, color="#33C62828",
                                offset=ft.Offset(0, 6),
                            ),
                        ),
                        ft.Container(height=20),

                        # ── headings ────────────────────────────
                        ft.Text(
                            "Forgot Password",
                            size=26, weight=ft.FontWeight.BOLD,
                            color=C["primary_dk"],
                        ),
                        ft.Text(
                            "پاس ورڈ بھول گئے؟",
                            size=15, color=C["primary"],
                        ),
                        ft.Container(height=6),
                        ft.Text(
                            "Enter your registered phone number.\nWe'll send a 4-digit OTP to verify.",
                            size=13, color=C["grey"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=24),

                        # ── card ────────────────────────────────
                        ft.Card(
                            elevation=8,
                            shape=ft.RoundedRectangleBorder(radius=22),
                            shadow_color="#22C62828",
                            content=ft.Container(
                                bgcolor=C["white"],
                                border_radius=22,
                                padding=ft.padding.symmetric(
                                    horizontal=28, vertical=28,
                                ),
                                width=400,
                                content=ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=16,
                                    controls=[
                                        # info strip
                                        ft.Container(
                                            border_radius=10,
                                            bgcolor="#F5F5F5",
                                            padding=ft.padding.symmetric(
                                                horizontal=12, vertical=8,
                                            ),
                                            content=ft.Row(
                                                spacing=8,
                                                controls=[
                                                    ft.Icon(
                                                        ft.Icons.INFO_OUTLINE_ROUNDED,
                                                        color="#1565C0", size=16,
                                                    ),
                                                    ft.Text(
                                                        "An OTP will be sent via SMS\n"
                                                        "SMS کے ذریعے OTP بھیجا جائے گا",
                                                        size=12, color=C["grey"],
                                                        expand=True,
                                                    ),
                                                ],
                                            ),
                                        ),
                                        phone_tf,
                                        send_btn,
                                    ],
                                ),
                            ),
                        ),

                        ft.Container(height=20),

                        # ── back link ───────────────────────────
                        ft.TextButton(
                            content=ft.Row(
                                spacing=4,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.ARROW_BACK_IOS_ROUNDED,
                                        color=C["primary"], size=14,
                                    ),
                                    ft.Text(
                                        "Back to Login | لاگ ان پر واپس",
                                        color=C["primary"], size=13,
                                    ),
                                ],
                            ),
                            on_click=lambda _: page.go("/login"),
                        ),
                    ],
                ),
            ),
        ],
    )
