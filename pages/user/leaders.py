



# ================================================================
#  pages/user/leaders.py — Central Leadership View
#  Route: /leaders
#  Displays Central Leadership only, with a bottom button to 
#  navigate to the full tree view (/leaders_view).
# ================================================================

from typing import List, Dict
import flet as ft

from home_module.home_config import T
from pages.user.leaders_common import (
    init_common,
    fetch_leaders,
    leader_card_row,
)


def view(page: ft.Page) -> ft.View:
    sb, role, can_edit, can_delete, restore, snack = init_common(page)

    leaders_state: Dict[str, List[dict]] = {"central": []}
    list_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def _render():
        central_leaders = leaders_state["central"]
        controls: List[ft.Control] = []

        if central_leaders:
            for ldr in central_leaders:
                controls.append(
                    leader_card_row(
                        ldr, 
                        page, 
                        can_edit=can_edit, 
                        on_edit_click=None # Read-only or handles edit if configured
                    )
                )
        else:
            controls.append(
                ft.Container(
                    alignment=ft.Alignment(0, 0),
                    padding=ft.padding.all(40),
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=48, color=T.get("text_hint", ft.Colors.GREY_400)),
                            ft.Text("No central leaders found.", size=13, color=T.get("text_sub", ft.Colors.GREY)),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    )
                )
            )

        list_col.controls = controls
        try:
            page.update()
        except Exception:
            pass

    async def _load():
        try:
            data = await fetch_leaders(sb, restore, query="")
            # Filter only Central level leaders
            leaders_state["central"] = [
                ldr for ldr in data if (ldr.get("level") or "central") == "central"
            ]
            _render()
        except Exception as ex:
            list_col.controls = [
                ft.Text(f"Error loading leaders: {str(ex)[:80]}", size=12, color=T.get("primary", ft.Colors.RED))
            ]
            try:
                page.update()
            except Exception:
                pass

    def load_leaders():
        try:
            page.run_task(_load)
        except Exception:
            pass

    # Floating Bottom Button for "View All Leaders"
    view_all_btn = ft.Container(
        alignment=ft.Alignment(0, 0),
        padding=ft.padding.only(bottom=16),
        content=ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ACCOUNT_TREE_ROUNDED, color="white", size=18),
                    ft.Text("View All Leaders | تمام رہنما دیکھیں", size=13, weight=ft.FontWeight.BOLD, color="white"),
                ],
                tight=True,
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                bgcolor=T.get("primary", ft.Colors.RED),
                shape=ft.RoundedRectangleBorder(radius=24),
                padding=ft.padding.symmetric(horizontal=24, vertical=12),
            ),
            on_click=lambda _: page.go("/leaders_view"),
        ),
    )

    # Top Add Button for authorized users
    add_btn = (
        ft.IconButton(
            icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED,
            icon_color="white",
            tooltip="Add Leader",
            on_click=lambda _: page.go("/admin"),
        )
        if can_edit
        else ft.Container(width=0)
    )

    # Initial Data Load
    load_leaders()

    return ft.View(
        route="/leaders",
        bgcolor=T.get("bg", ft.Colors.GREY_100),
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/"),
            ),
            title=ft.Column(
                [
                    ft.Text("Central Leadership | مرکزی قیادت", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("قومی سطح کی مرکزی قیادت", size=10, color=T.get("primary_md", ft.Colors.BLUE_100)),
                ],
                spacing=0,
            ),
            bgcolor=T.get("primary", ft.Colors.RED),
            actions=[add_btn],
        ),
        controls=[
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                content=ft.Column(
                    expand=True,
                    controls=[
                        list_col,
                        view_all_btn,
                    ],
                ),
            ),
        ],
    )