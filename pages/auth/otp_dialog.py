# ================================================================
#  otp_dialog.py – Premium 6 Digit OTP Dialog (Flet 0.84 Stable)
# ================================================================

import asyncio
import flet as ft

from core.theme import Theme 
def show_otp_dialog(page: ft.Page, phone_number: str, on_verify_submit: callable):
    OTP_LENGTH = 6
    code_fields = []

    async def _focus(idx: int):
        try:
            if 0 <= idx < OTP_LENGTH:
                await code_fields[idx].focus()
        except Exception:
            pass

    def on_change(idx):
        def handler(e: ft.ControlEvent):
            value = e.control.value or ""

            # Paste full OTP
            if len(value) > 1:
                cleaned = "".join(c for c in value if c.isdigit())[:OTP_LENGTH]
                for i, char in enumerate(cleaned):
                    code_fields[i].value = char
                page.update()
                page.run_task(_focus, min(len(cleaned), OTP_LENGTH) - 1)
                return

            # Single digit
            if value:
                if not value[-1].isdigit():
                    e.control.value = ""
                    e.control.update()
                    return
                e.control.value = value[-1]
                e.control.update()
                page.run_task(_focus, idx + 1)

            # Backspace
            else:
                if idx > 0:
                    code_fields[idx - 1].value = ""
                    code_fields[idx - 1].update()
                    page.run_task(_focus, idx - 1)

        return handler

    for i in range(OTP_LENGTH):
        field = ft.TextField(
            width=48, height=56,
            text_align=ft.TextAlign.CENTER,
            text_size=22,
            border_radius=12,
            border_color="#E0E0E0",
            focused_border_color="#C62828",
            bgcolor="#FAFAFA",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=ft.padding.all(0),
            max_length=1,
            counter_style=ft.TextStyle(size=0),
        )
        field.on_change = on_change(i)
        code_fields.append(field)

    digits = "".join(c for c in phone_number if c.isdigit())
    masked = phone_number[:-4] + "****" if len(digits) >= 7 else phone_number

    def _close_dialog():
        otp_dialog.open = False
        page.update()

    otp_dialog = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=24),
        title=ft.Column(
            spacing=8, tight=True,
            controls=[
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Container(
                            width=40, height=40, border_radius=20,
                            bgcolor="#FFEBEE",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.LOCK_CLOCK_OUTLINED,
                                color="#C62828", size=22,
                            ),
                        ),
                        ft.Column(
                            spacing=1, tight=True,
                            controls=[
                                ft.Text(
                                    "Phone Verification",
                                    weight=ft.FontWeight.BOLD,
                                    size=16, color="#212121",
                                ),
                                ft.Text(
                                    "فون نمبر کی تصدیق",
                                    size=12, color="#C62828",
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Container(
                    border_radius=10, bgcolor="#F5F5F5",
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.SMS_OUTLINED, size=15, color="#757575"),
                            ft.Text(
                                f"Code sent to {masked}",
                                size=12, color="#616161", expand=True,
                            ),
                        ],
                    ),
                ),
            ],
        ),
        content=ft.Container(
            padding=ft.padding.symmetric(vertical=16),
            width=320,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12, tight=True,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                        controls=code_fields,
                    ),
                    ft.Text(
                        "Enter the 6-digit OTP | 6 ہندسوں کا کوڈ درج کریں",
                        size=11, color="#9E9E9E",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        ),
        actions=[
            ft.ElevatedButton(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.VERIFIED_OUTLINED, color="white", size=18),
                        ft.Text(
                            "Verify Code | تصدیق کریں",
                            color="white",
                            weight=ft.FontWeight.BOLD,
                            size=14,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
                style=ft.ButtonStyle(
                    bgcolor="#C62828",
                    shape=ft.RoundedRectangleBorder(radius=12),
                    overlay_color="#B71C1C",
                ),
                width=280, height=48,
                on_click=lambda e: on_verify_submit(
                    "".join(f.value or "" for f in code_fields),
                    otp_dialog,
                ),
            ),
            ft.TextButton(
                "Cancel | منسوخ",
                style=ft.ButtonStyle(color="#9E9E9E"),
                on_click=lambda e: _close_dialog(),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    page.overlay.append(otp_dialog)
    otp_dialog.open = True
    page.update()
    page.run_task(_focus, 0)

    return otp_dialog