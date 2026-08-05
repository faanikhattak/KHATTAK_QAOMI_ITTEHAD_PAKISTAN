# ====================================================================
#  verification.py  –  Phone Verification (Splash + OTP Dialog)
#  Target: Flet 0.84+  |  Firebase OTP + Supabase (Fully Fixed)
# ====================================================================
from core.theme import Theme 
import re
import asyncio
import flet as ft
from services.database.db import supabase
from services.firebase.firebase_otp import send_otp, verify_otp
from home_module.home_config import get_session, set_session, clear_session
from pages.auth.otp_dialog import show_otp_dialog   # shared OTP dialog

# ── validators ──────────────────────────────────────────────────
def _valid_phone(p: str) -> bool:
    return bool(re.fullmatch(r"(03\d{9}|\+923\d{9})", p.strip()))


# ================================================================
#  VIEW
# ================================================================
def view(page: ft.Page):

    # ── resolve phone from session / page attributes ─────────────
    verify_phone: str = (
        getattr(page, "verify_phone", "") or
        get_session(page).get("verify_phone", "") or
        ""
    ).strip()

    # ── theme tokens ────────────────────────────────────────────
    C = {
        "primary":    "#C62828",
        "primary_dk": "#B71C1C",
        "primary_lt": "#FFEBEE",
        "primary_pl": "#FFCDD2",
        "green":      "#2E7D32",
        "blue":       "#1565C0",
        "grey":       "#757575",
        "grey_lt":    "#9E9E9E",
        "text":       "#212121",
        "bg":         "#FFF8F8",
        "white":      "#FFFFFF",
    }

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
        request_btn.disabled = active
        request_btn.content = (
            ft.Row(
                [ft.ProgressRing(width=18, height=18, color="white", stroke_width=2.5)],
                alignment=ft.MainAxisAlignment.CENTER,
            )
            if active
            else _btn_label()
        )
        safe_update()

    def _btn_label():
        return ft.Row(
            [
                ft.Icon(ft.Icons.SMS_OUTLINED, color="white", size=18),
                ft.Text(
                    "Request OTP Code | کوڈ منگوائیں",
                    color="white", weight=ft.FontWeight.BOLD, size=14,
                ),
            ],
            spacing=8, alignment=ft.MainAxisAlignment.CENTER,
        )

    # store session_info between send and verify
    _session_info = [""]

    # ── OTP verify callback ──────────────────────────────────────
    async def _verify_callback(code: str, dialog: ft.AlertDialog):
        # 🌟 فکس: فائر بیس کا او ٹی پی ہمیشہ 6 ہندسوں کا ہوتا ہے
        if len(code) != 6 or not code.isdigit():
            show_alert("⚠ Enter the complete 6-digit code.\nمکمل 6 ہندسوں کا کوڈ درج کریں۔")
            return

        dialog.open = False
        safe_update()

        session_info = _session_info[0]
        phone        = _resolved_phone()

        def _work():
            return verify_otp(session_info, code)

        ok, _verified_phone, err = await asyncio.to_thread(_work)

        if ok:
            # 1. پہلے سیشن کو محفوظ طریقے سے اپڈیٹ کریں
            set_session(page, {
                "phone_verified": True, 
                "verify_phone": phone,
                "email_verified": "True"
            })

            # 2. سپابیس پروفائل اپڈیٹ کرنے کا بالکل محفوظ طریقہ
            def _sync_supabase_profile():
                try:
                    # فون نمبر کی بنیاد پر پروفائل اپڈیٹ کریں تاکہ سیشن کا رپھڑ نہ ہو
                    supabase.table("profiles").update(
                        {"phone_verified": True, "email_verified": True}
                    ).eq("phone", phone).execute()
                    print(f"[VERIFY] Supabase profile synced for phone: {phone}")
                except Exception as db_err:
                    print(f"[VERIFY] Database sync warning: {db_err}")

            # نیٹ ورک کال کو بیک گراؤنڈ تھریڈ پر چلائیں
            await asyncio.to_thread(_sync_supabase_profile)

            # 3. کامیابی کا میسج دکھائیں اور ہوم پیج پر جائیں
            show_alert(
                "✓ Verified! Redirecting to home…\nتصدیق کامیاب! ہوم پر جا رہے ہیں۔",
                C["green"],
            )
            await asyncio.sleep(1.2)
            page.go("/home")
            
        else:
            show_alert(
                f"⚠ Invalid OTP. {err or ''}\nغلط کوڈ، دوبارہ کوشش کریں۔"
            )
            
    # ── send OTP logic ───────────────────────────────────────────
    async def on_request_otp(e):
        phone = _resolved_phone()

        if not phone:
            _show_phone_entry()
            return

        if not _valid_phone(phone):
            show_alert(
                "⚠ Invalid phone format.\nFormat: 03xxxxxxxxx or +923xxxxxxxxx",
                "#E65100",
            )
            return

        set_loading(True)

        # فون نمبر کو انٹرنیشنل فارمیٹ ای-164 میں بدلیں تاکہ فائر بیس ناراض نہ ہو
        raw_phone = phone.strip()
        if raw_phone.startswith("03"):
            formatted_phone = "+92" + raw_phone[1:]
        else:
            formatted_phone = raw_phone

        def _send():
            return send_otp(formatted_phone)

        ok, session_info, err = await asyncio.to_thread(_send)
        set_loading(False)

        if ok:
            _session_info[0] = session_info
            show_otp_dialog(
                page=page,
                phone_number=formatted_phone,
                on_verify_submit=lambda code, dlg: page.run_task(
                    _verify_callback, code, dlg
                ),
            )
        else:
            msg = str(err or "").lower()
            if "rate" in msg or "many" in msg:
                show_alert(
                    "⚠ Too many attempts. Wait 1 minute.\nبہت زیادہ کوششیں، 1 منٹ بعد ٹرائی کریں۔",
                    "#E65100",
                )
            else:
                show_alert(f"⚠ Could not send OTP: {str(err)[:60]}")

    def _resolved_phone() -> str:
        return (
            verify_phone or
            get_session(page).get("verify_phone", "") or
            getattr(page, "verify_phone", "") or
            ""
        ).strip()

    # ── inline phone-entry fallback dialog ──────────────────────
    def _show_phone_entry():
        tf = ft.TextField(
            label="Phone | فون نمبر",
            hint_text="03xxxxxxxxx",
            prefix_icon=ft.Icons.PHONE_OUTLINED,
            keyboard_type=ft.KeyboardType.PHONE,
            border_radius=12,
            focused_border_color=C["primary"],
            border_color="#E0E0E0",
            width=280,
        )

        async def _confirm(e):
            ph = (tf.value or "").strip()
            if not _valid_phone(ph):
                tf.error_text = "Format: 03xxxxxxxxx"
                safe_update()
                return
            set_session(page, {"verify_phone": ph})
            entry_dlg.open = False
            safe_update()
            await on_request_otp(None)

        entry_dlg = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(ft.Icons.PHONE_OUTLINED, color=C["primary"], size=20),
                    ft.Text("Enter Phone | فون نمبر",
                            weight=ft.FontWeight.BOLD, size=15),
                ],
            ),
            content=ft.Container(
                padding=ft.padding.symmetric(vertical=8),
                content=tf, width=300,
            ),
            actions=[
                ft.ElevatedButton(
                    "Continue | جاری",
                    style=ft.ButtonStyle(
                        bgcolor=C["primary"],
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=lambda e: page.run_task(_confirm, e),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        page.overlay.append(entry_dlg)
        entry_dlg.open = True
        safe_update()

    # ── controls ────────────────────────────────────────────────
    request_btn = ft.ElevatedButton(
        content=_btn_label(),
        style=ft.ButtonStyle(
            bgcolor=C["primary"],
            shape=ft.RoundedRectangleBorder(radius=12),
            overlay_color=C["primary_dk"],
        ),
        width=320, height=52,
        on_click=lambda e: page.run_task(on_request_otp, e),
    )

    # masked phone display
    _phone_str = _resolved_phone()
    _masked = (
        _phone_str[:-4] + "****"
        if len(_phone_str) >= 7
        else (_phone_str or "—")
    )

    phone_chip = ft.Container(
        visible=bool(_phone_str),
        border_radius=12,
        bgcolor=C["primary_lt"],
        border=ft.border.all(1.5, C["primary_pl"]),
        padding=ft.padding.symmetric(horizontal=20, vertical=12),
        content=ft.Row(
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.PHONE_ANDROID_ROUNDED,
                        color=C["primary"], size=22),
                ft.Text(
                    _masked,
                    size=18, weight=ft.FontWeight.BOLD,
                    color=C["primary_dk"],
                    style=ft.TextStyle(letter_spacing=2.0),
                ),
            ],
        ),
    )

    # ── layout ──────────────────────────────────────────────────
    return ft.View(
        route="/verification",
        bgcolor=C["bg"],
        padding=0,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/login"),
                tooltip="Back | واپس",
            ),
            title=ft.Column(
                spacing=0,
                controls=[
                    ft.Text("Phone Verification",
                            size=16, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("فون تصدیق", size=11, color=C["primary_pl"]),
                ],
            ),
            bgcolor=C["primary"],
            elevation=0,
            center_title=False,
        ),
        controls=[
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=24, vertical=32),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                    spacing=0,
                    controls=[

                        # ── hero icon ────────────────────────────
                        ft.Container(
                            width=100, height=100, border_radius=50,
                            bgcolor=C["primary_lt"],
                            border=ft.border.all(2.5, C["primary_pl"]),
                            content=ft.Icon(
                                ft.Icons.PHONE_ANDROID_ROUNDED,
                                size=52, color=C["primary"],
                            ),
                            alignment=ft.Alignment.CENTER,
                            shadow=ft.BoxShadow(
                                blur_radius=28, color="#44C62828",
                                offset=ft.Offset(0, 8),
                            ),
                        ),
                        ft.Container(height=24),

                        # ── headings ─────────────────────────────
                        ft.Text(
                            "Verify Your Phone",
                            size=26, weight=ft.FontWeight.BOLD,
                            color=C["primary_dk"],
                        ),
                        ft.Text(
                            "اپنا فون نمبر تصدیق کریں",
                            size=16, color=C["primary"],
                        ),
                        ft.Container(height=10),
                        # 🌟 فکس: 4 کی جگہ "6-digit OTP" لکھا ہے
                        ft.Text(
                            "We'll send a 6-digit OTP to your\n"
                            "registered phone number via SMS.",
                            size=13, color=C["grey"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=28),

                        # ── phone chip ───────────────────────────
                        phone_chip,
                        ft.Container(height=24 if _phone_str else 0),

                        # ── CTA button ───────────────────────────
                        request_btn,
                        ft.Container(height=20),

                        # ── info strip ───────────────────────────
                        ft.Container(
                            border_radius=12,
                            bgcolor="#F5F5F5",
                            padding=ft.padding.symmetric(
                                horizontal=16, vertical=10,
                            ),
                            width=340,
                            content=ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.INFO_OUTLINE_ROUNDED,
                                        color=C["blue"], size=16,
                                    ),
                                    ft.Text(
                                        "OTP expires in 5 minutes\n"
                                        "کوڈ 5 منٹ تک درست رہے گا",
                                        size=12, color=C["grey"], expand=True,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(height=28),

                        # ── wrong number link ─────────────────────
                        ft.Container(
                            border_radius=12,
                            bgcolor=C["white"],
                            border=ft.border.all(1, "#F0F0F0"),
                            padding=ft.padding.symmetric(
                                horizontal=20, vertical=4,
                            ),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=4,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.PERSON_OUTLINE_ROUNDED,
                                        color=C["grey_lt"], size=18,
                                    ),
                                    ft.Text(
                                        "Wrong number? | غلط نمبر؟",
                                        color=C["grey"], size=13,
                                    ),
                                    ft.TextButton(
                                        "Re-register | دوبارہ رجسٹر",
                                        style=ft.ButtonStyle(color=C["primary"]),
                                        on_click=lambda _: page.go("/register"),
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )



