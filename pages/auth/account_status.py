# ================================================================
#  pages/auth/account_status.py  —  Access Gate Screen
#  Shown instead of /home whenever the admin has NOT approved the
#  member, or has restricted them (blocked / banned / frozen /
#  rejected). This is the enforcement side of the admin's approve/
#  reject/block/ban/freeze actions in admin_main.py — those actions
#  write flags to `profiles`, and this screen (via the gate in
#  main.py's route_change) is what actually stops access.
# ================================================================

import asyncio
import flet as ft
from services.database.db import supabase

RED       = "#C62828"
RED_DARK  = "#B71C1C"
WHITE     = "#FFFFFF"
BG        = "#FFF5F5"
GREY_TXT  = "#757575"
ORANGE    = "#E65100"
BLUE      = "#1565C0"
GREEN     = "#2E7D32"

# Each status maps to: (emoji, english_title, urdu_title, english_body, urdu_body, color)
STATUS_META = {
    "pending": (
        "⏳", "Awaiting Admin Approval", "منتظر منظوری",
        "Your account has been created but is still waiting for admin approval. "
        "You'll be able to use the app as soon as an admin approves you.",
        "آپ کا اکاؤنٹ بن چکا ہے لیکن ابھی ایڈمن کی منظوری کا انتظار ہے۔ "
        "منظوری ملتے ہی آپ ایپ استعمال کر سکیں گے۔",
        ORANGE,
    ),
    "rejected": (
        "❌", "Application Rejected", "درخواست مسترد",
        "Your membership request was rejected by an admin. If you think this is "
        "a mistake, please contact support.",
        "آپ کی رکنیت کی درخواست ایڈمن نے مسترد کر دی ہے۔ اگر آپ کے خیال میں یہ "
        "غلطی ہے تو براہ کرم سپورٹ سے رابطہ کریں۔",
        RED,
    ),
    "blocked": (
        "⛔", "Account Blocked", "اکاؤنٹ بلاک",
        "Your account has been temporarily blocked by an admin. Please contact "
        "support for more information.",
        "آپ کا اکاؤنٹ ایڈمن نے عارضی طور پر بلاک کر دیا ہے۔ مزید معلومات کے "
        "لیے سپورٹ سے رابطہ کریں۔",
        ORANGE,
    ),
    "banned": (
        "🚫", "Account Banned", "اکاؤنٹ پابندی",
        "Your account has been banned by an admin and access has been revoked.",
        "آپ کا اکاؤنٹ ایڈمن نے پابندی کا شکار کر دیا ہے اور رسائی منسوخ کر دی گئی ہے۔",
        RED_DARK,
    ),
    "frozen": (
        "❄️", "Account Frozen", "اکاؤنٹ منجمد",
        "Your account has been frozen by an admin. Please contact support to "
        "resolve this.",
        "آپ کا اکاؤنٹ ایڈمن نے منجمد کر دیا ہے۔ اسے حل کرنے کے لیے سپورٹ سے "
        "رابطہ کریں۔",
        BLUE,
    ),
}


def view(page: ft.Page) -> ft.View:

    # ── Read status set by main.py's route_change gate ─────────
    def sess_get(key: str, default: str = "") -> str:
        try:
            if hasattr(page.session, "_Session__store"):
                return page.session._Session__store.get(key) or default
            return page.session.get(key) or default
        except Exception:
            return default

    full_name   = sess_get("full_name", "Member")
    is_approved = sess_get("is_approved", "False").lower() in ("true", "1", "yes")
    acc_status  = sess_get("account_status", "active") or "active"

    # Decide which message to show:
    #  - not approved yet AND not explicitly rejected → still pending
    #  - otherwise use whatever restriction status is set
    if not is_approved and acc_status not in ("rejected", "blocked", "banned", "frozen"):
        key = "pending"
    elif acc_status in STATUS_META:
        key = acc_status
    else:
        key = "pending"

    emoji, en_title, ur_title, en_body, ur_body, color = STATUS_META[key]

    # ── Logout ───────────────────────────────────────────────
    def do_logout(e=None):
        async def _do():
            try:
                await asyncio.to_thread(supabase.auth.sign_out)
            except Exception as ex:
                print(f"[ACCOUNT STATUS] sign_out error: {ex}")
            try:
                if hasattr(page.session, "_Session__store"):
                    store = page.session._Session__store
                    for k in ("access_token", "refresh_token", "user_id", "email",
                              "email_verified", "role", "full_name", "blood_group",
                              "is_approved", "account_status"):
                        try:
                            store.remove(k)
                        except Exception:
                            pass
                else:
                    for k in ("access_token", "refresh_token", "user_id", "email",
                              "email_verified", "role", "full_name", "blood_group",
                              "is_approved", "account_status"):
                        try:
                            page.session.remove(k)
                        except Exception:
                            pass
            except Exception as ex:
                print(f"[ACCOUNT STATUS] session clear error: {ex}")
            try:
                await page.push_route("/login")
            except Exception:
                page.go("/login")
        page.run_task(_do)

    def do_refresh(e=None):
        # Re-runs route_change, which re-checks is_approved / account_status
        # from the database — lets the member self-check after an admin
        # has approved / reactivated them, without needing to log out.
        async def _do():
            try:
                await page.push_route("/home")
            except Exception:
                page.go("/home")
        page.run_task(_do)

    card = ft.Container(
        width=380,
        padding=ft.padding.all(28),
        border_radius=20,
        bgcolor=WHITE,
        shadow=ft.BoxShadow(blur_radius=24, color="#22000000", offset=ft.Offset(0, 8)),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=14,
            controls=[
                ft.Text(emoji, size=52),
                ft.Text(f"Hi {full_name} 👋", size=14, color=GREY_TXT),
                ft.Text(en_title, size=19, weight=ft.FontWeight.BOLD, color=color,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(ur_title, size=16, color=color, rtl=True,
                        text_align=ft.TextAlign.CENTER),
                ft.Divider(height=10, color="#EEEEEE"),
                ft.Text(en_body, size=13, color="#424242",
                        text_align=ft.TextAlign.CENTER),
                ft.Text(ur_body, size=13, color="#424242", rtl=True,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=8),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        ft.OutlinedButton(
                            "Check Again | دوبارہ چیک کریں",
                            icon=ft.Icons.REFRESH_ROUNDED,
                            on_click=do_refresh,
                        ),
                        ft.ElevatedButton(
                            "Logout | لاگ آؤٹ",
                            icon=ft.Icons.LOGOUT_ROUNDED,
                            style=ft.ButtonStyle(
                                color=WHITE, bgcolor=RED,
                                shape=ft.RoundedRectangleBorder(radius=12),
                            ),
                            on_click=do_logout,
                        ),
                    ],
                ),
            ],
        ),
    )

    return ft.View(
        route="/account-status",
        bgcolor=BG,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[card],
    )