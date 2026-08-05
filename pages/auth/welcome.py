import flet as ft
import tomllib
from home_module.home_config import get_logo_control
from services.database.db import supabase
from core.theme import Theme
from support import show_support_dialog
from flet import Icons as IC

I_HISTORY_EDU = IC.HISTORY_EDU_SHARP


def get_app_version():
    """pyproject.toml سے version read کریں"""
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "1.0.0")
    except Exception:
        return "1.0.0"


def view(page: ft.Page):
    page.title = "Khattak qomi itehad pakistan | خٹک قومی اتحاد پاکستان"

    current_version = get_app_version()

    # ✅ BEST PRACTICE (No warning, stable)
    def launch_telegram(e):
        page.run_task(_open_telegram)

    async def _open_telegram():
        try:
            # Works on mobile + desktop
            await page.launch_url("https://t.me/FaaniKhattak")
        except Exception as ex:
            print("Telegram error:", ex)

            try:
                # fallback
                await page.launch_url("tg://resolve?domain=FaaniKhattak")
            except Exception:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Telegram open nahi ho saka"),
                    open=True
                )
                page.update()

    # 🔷 Logo
    logo_holder = ft.Container(
        content=get_logo_control(
            logo_url="assets/app_logo.gif",
            width=120,
            height=120,
        ),
        alignment=ft.Alignment.CENTER,
    )

    # 🔷 Welcome Text
    welcome_text = ft.Column(
        controls=[
            ft.Text(
                "WELCOME TO KHATTAK QAOMI ITTEHAD PAKISTAN",
                size=22,
                weight=ft.FontWeight.BOLD,
                color="#C62828",
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Unity is our strength, service is our commitment",
                size=10,
                text_align=ft.TextAlign.CENTER,
                color="#1A252F",
            ),
            ft.Text(
                "خٹک قومی اتحاد پاکستان میں خوش آمدید",
                size=20,
                weight=ft.FontWeight.BOLD,
                color="#C62828",
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "اتحاد ہماری طاقت، خدمت ہمارا عزم",
                size=10,
                font_family="Urdu",
                text_align=ft.TextAlign.CENTER,
                color="#1A252F",
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=5,
    )

    # 🔷 Buttons
    buttons_col = ft.Column(
        controls=[
            ft.ElevatedButton(
                "Login | لاگ ان کریں",
                width=280,
                height=50,
                style=ft.ButtonStyle(
                    bgcolor="#C62828",
                    color="white",
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=lambda _: page.go("/login"),
            ),
            ft.OutlinedButton(
                "Register | نیا اکاؤنٹ بنائیں",
                width=280,
                height=50,
                style=ft.ButtonStyle(
                    color="#C62828",
                    shape=ft.RoundedRectangleBorder(radius=8),
                    side=ft.BorderSide(color="#C62828", width=1.5),
                ),
                on_click=lambda _: page.go("/register"),
            ),
        ],
        spacing=15,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # 🔷 Footer
    footer = ft.Container(
        content=ft.Column(
            controls=[
                # Help
                ft.GestureDetector(
                    mouse_cursor=ft.MouseCursor.CLICK,
                    on_tap=lambda e: show_support_dialog(page, {}),
                    content=ft.Container(
                        margin=ft.Margin(0, 0, 0, 4),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.SUPPORT_AGENT_ROUNDED, size=14, color="#00897B"),
                                ft.Text(
                                    "Need help? Contact us | مدد چاہیے؟",
                                    size=11,
                                    color="#00897B",
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=5,
                        ),
                    ),
                ),

                # Version
                ft.Text(f"v{current_version}", size=10, color=ft.Colors.GREY_500),

                ft.Container(height=5),

                # Telegram link
                ft.GestureDetector(
                    mouse_cursor=ft.MouseCursor.CLICK,
                    on_tap=launch_telegram,
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.SEND_ROUNDED, size=14, color="#24A1DE"),
                                ft.Text(
                                    "Developed by Irfan Khattak",
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=5,
                        ),
                    ),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        ),
        margin=ft.Margin(0, 40, 0, 0),
    )

    # 🔷 Main Layout
    main_layout = ft.Column(
        controls=[
            ft.Container(height=20),
            logo_holder,
            ft.Container(height=10),
            welcome_text,
            ft.Container(height=30),
            buttons_col,
            footer,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
    )

    return ft.View(
        route="/welcome",
        controls=[main_layout],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        padding=20,
    )