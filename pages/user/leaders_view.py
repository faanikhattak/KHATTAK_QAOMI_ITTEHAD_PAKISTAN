

# ================================================================
#  pages/user/leaders_view.py — Full Leadership Tree Page (Read-Only)
#  Route: /leaders_view
#  Central leaders on top, then Provincial / District / Overseas
#  grouped by location.
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
    sb, role, _can_edit, _can_delete, restore, snack = init_common(page)

    leaders_state: Dict[str, List[dict]] = {"all": [], "filtered": []}
    expanded: Dict[str, bool] = {"provincial": True, "district": False, "overseas": False}
    tree_col = ft.Column(spacing=8)

    def _section_header(icon: str, label: str, key: str, count: int) -> ft.Container:
        def _toggle(e=None):
            expanded[key] = not expanded[key]
            _render_tree()

        return ft.Container(
            on_click=_toggle,
            padding=ft.padding.symmetric(horizontal=4, vertical=6),
            content=ft.Row(
                [
                    ft.Icon(icon, size=18, color=T.get("primary", ft.Colors.BLUE)),
                    ft.Container(width=8),
                    ft.Text(label, size=14, weight=ft.FontWeight.W_700, color=T.get("text", ft.Colors.BLACK), expand=True),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        border_radius=10, bgcolor=T.get("primary_lt", ft.Colors.BLUE_50),
                        content=ft.Text(str(count), size=10, color=T.get("primary", ft.Colors.BLUE), weight=ft.FontWeight.BOLD),
                    ),
                    ft.Container(width=6),
                    ft.Icon(
                        ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED if expanded[key] else ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED,
                        size=20, color=T.get("text_sub", ft.Colors.GREY),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _group_block(group_label: str, rows: List[dict]) -> ft.Container:
        return ft.Container(
            margin=ft.margin.only(left=12, bottom=6),
            content=ft.Column(
                [
                    ft.Text(group_label, size=11, weight=ft.FontWeight.W_700, color=T.get("text_sub", ft.Colors.GREY)),
                    ft.Container(height=4),
                    ft.Column(
                        [leader_card_row(l, page) for l in rows],  # read-only
                        spacing=6,
                    ),
                ],
                spacing=2,
            ),
        )

    def _render_tree():
        data = leaders_state["filtered"]
        central    = [l for l in data if (l.get("level") or "central") == "central"]
        provincial = [l for l in data if l.get("level") == "provincial"]
        district   = [l for l in data if l.get("level") == "district"]
        overseas   = [l for l in data if l.get("level") == "overseas"]

        controls: List[ft.Control] = []

        # ── Central (always on top) ──
        controls.append(ft.Text("🏛️ Central Leadership | مرکزی قیادت",
                                 size=14, weight=ft.FontWeight.W_700, color=T.get("text", ft.Colors.BLACK)))
        controls.append(ft.Container(height=6))
        if central:
            controls.append(ft.Column(
                [leader_card_row(l, page) for l in central],  # read-only
                spacing=6,
            ))
        else:
            controls.append(ft.Text("No central leaders found.", size=12, color=T.get("text_sub", ft.Colors.GREY)))
        controls.append(ft.Divider(height=24, color=T.get("primary_lt", ft.Colors.BLUE_50)))

        # ── Provincial (grouped by province) ──
        by_province: Dict[str, List[dict]] = {}
        for l in provincial:
            by_province.setdefault(l.get("province") or "Unspecified", []).append(l)
        controls.append(_section_header(ft.Icons.MAP_OUTLINED, "Provincial | صوبائی", "provincial", len(provincial)))
        if expanded["provincial"]:
            for prov, rows in sorted(by_province.items()):
                controls.append(_group_block(prov, rows))
            if not provincial:
                controls.append(ft.Text("No provincial leaders found.", size=12, color=T.get("text_sub", ft.Colors.GREY)))
        controls.append(ft.Container(height=4))

        # ── District (grouped by district — province) ──
        by_pd: Dict[tuple, List[dict]] = {}
        for l in district:
            key = (l.get("province") or "Unspecified", l.get("district") or "Unspecified")
            by_pd.setdefault(key, []).append(l)
        controls.append(_section_header(ft.Icons.LOCATION_CITY_OUTLINED, "District | ضلعی", "district", len(district)))
        if expanded["district"]:
            for (prov, dist), rows in sorted(by_pd.items()):
                controls.append(_group_block(f"{dist} — {prov}", rows))
            if not district:
                controls.append(ft.Text("No district leaders found.", size=12, color=T.get("text_sub", ft.Colors.GREY)))
        controls.append(ft.Container(height=4))

        # ── Overseas (grouped by country) ──
        by_country: Dict[str, List[dict]] = {}
        for l in overseas:
            by_country.setdefault(l.get("country") or "Unspecified", []).append(l)
        controls.append(_section_header(ft.Icons.PUBLIC, "Overseas | بیرون ملک", "overseas", len(overseas)))
        if expanded["overseas"]:
            for country, rows in sorted(by_country.items()):
                controls.append(_group_block(country, rows))
            if not overseas:
                controls.append(ft.Text("No overseas leaders found.", size=12, color=T.get("text_sub", ft.Colors.GREY)))

        tree_col.controls = controls
        try:
            page.update()
        except Exception:
            pass

    async def _load(query: str = ""):
        try:
            data = await fetch_leaders(sb, restore, query)
            leaders_state["all"] = data
            leaders_state["filtered"] = data
            _render_tree()
        except Exception as ex:
            tree_col.controls = [ft.Text(f"Error loading leaders: {str(ex)[:80]}",
                                          size=12, color=T.get("primary", ft.Colors.RED))]
            try:
                page.update()
            except Exception:
                pass

    def load_leaders(query: str = ""):
        try:
            page.run_task(_load, query)
        except Exception:
            pass

    search_tf = ft.TextField(
        hint_text="Search leader by name, designation, city...",
        prefix_icon=ft.Icons.SEARCH, border_radius=10, content_padding=10,
        on_change=lambda e: load_leaders(e.control.value),
    )

    # Initial Load
    load_leaders()

    return ft.View(
        route="/leaders_view",
        bgcolor=T.get("bg", ft.Colors.WHITE),
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color="white",
                on_click=lambda _: page.go("/leaders"),
            ),
            title=ft.Column([
                ft.Text("Leadership | قیادت", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("مرکزی، صوبائی، ضلعی اور بیرون ملک", size=10, color=T.get("primary_md", ft.Colors.BLUE_100)),
            ], spacing=0),
            bgcolor=T.get("primary", ft.Colors.BLUE),
        ),
        controls=[
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                content=ft.Column(
                    expand=True,
                    controls=[
                        search_tf,
                        ft.Container(height=6),
                        ft.Column(
                            expand=True, scroll=ft.ScrollMode.AUTO,
                            controls=[tree_col, ft.Container(height=30)],
                        ),
                    ],
                ),
            ),
        ],
    )