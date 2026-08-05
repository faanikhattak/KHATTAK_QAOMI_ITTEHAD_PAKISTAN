# ================================================================
#  pages/user/community_updates.py  —  Community Updates Feed
#  Dedicated scrollable page (Facebook-style) opened when the user
#  taps "See Updates" on Home. This feed no longer shows inline on
#  the Home page — it lives only here.
#  Flet 0.84 compatible.
# ================================================================

import asyncio
import flet as ft
from supabase import create_client

from services.database.db import SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options
from home_module.home_config import T, is_admin, _pa
from home_module.home_widgets import build_instagram_feed, empty_state
from home_module.home_dialogs import DialogManager, show_update_detail


PAGE_SIZE = 12  # updates fetched per page (initial load + each "load more")


def view(page: ft.Page) -> ft.View:

    # ── Session helpers (same pattern as request.py) ─────────
    def sess_get(key: str, default="") -> str:
        try:
            if hasattr(page.session, "_Session__store"):
                return page.session._Session__store.get(key) or default
            return page.session.get(key) or default
        except Exception:
            return default

    _sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())

    async def _restore_session():
        try:
            at = sess_get("access_token")
            rt = sess_get("refresh_token", "")
            if at:
                await asyncio.to_thread(_sb.auth.set_session, at, rt)
        except Exception as ex:
            print(f"[COMM_UPD] session restore error: {ex}")

    def snack(msg: str, color: str = None):
        async def _show():
            try:
                sb = ft.SnackBar(
                    content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD, size=13),
                    bgcolor=color or T["primary"], duration=3500,
                )
                page.overlay.append(sb)
                sb.open = True
                page.update()
            except Exception:
                pass
        try:
            page.run_task(_show)
        except Exception:
            pass

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    role   = sess_get("role", "member")
    uid    = sess_get("user_id")

    dm = DialogManager(page, safe_update)

    # ── Feed state ────────────────────────────────────────────
    all_items: list = []
    offset = 0
    has_more = True
    loading = {"value": False}

    feed_col = ft.Column(spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

    load_more_btn = ft.Container(
        padding=_pa(16),
        alignment=ft.Alignment(0, 0),
        content=ft.ElevatedButton(
            "Load More | مزید دیکھیں",
            style=ft.ButtonStyle(
                bgcolor=T["surface"], color=T["primary"],
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            on_click=lambda e: _load_more(),
        ),
    )

    loading_row = ft.Container(
        padding=_pa(20),
        alignment=ft.Alignment(0, 0),
        content=ft.ProgressRing(width=28, height=28, stroke_width=3, color=T["primary"]),
    )

    def _on_media_tap(item):
        show_update_detail(
            item, dm, page, safe_update,
            role=role,
            supabase_client=_sb,
            on_deleted=lambda: _refresh(reset=True),
        )

    def _render():
        feed_col.controls.clear()

        if not all_items:
            feed_col.controls.append(
                empty_state(
                    "🩸", "No updates yet",
                    "کوئی اپڈیٹ نہیں — بعد میں دوبارہ چیک کریں",
                )
            )
        else:
            feed = build_instagram_feed(
                page=page,
                news_items=all_items,
                user_id=str(uid or ""),
                supabase_client=_sb,
                safe_update=safe_update,
                on_media_tap=_on_media_tap,
                on_deleted=lambda: _refresh(reset=True),
                user_role=role,
            )
            feed_col.controls.append(feed)

            if has_more:
                feed_col.controls.append(load_more_btn)

        safe_update()

    def _fetch_page(start: int, count: int):
        return (
            _sb.table("community_updates")
            .select("*")
            .order("created_at", desc=True)
            .range(start, start + count - 1)
            .execute()
        )

    def _load_more():
        if loading["value"] or not has_more:
            return
        loading["value"] = True

        feed_col.controls[-1:] = [loading_row] if feed_col.controls else [loading_row]
        safe_update()

        async def _work():
            nonlocal offset, has_more
            try:
                await _restore_session()
                res = await asyncio.to_thread(_fetch_page, offset, PAGE_SIZE)
                rows = res.data or []
                all_items.extend(rows)
                offset += len(rows)
                if len(rows) < PAGE_SIZE:
                    has_more = False
            except Exception as ex:
                print(f"[COMM_UPD] load_more error: {ex}")
                snack(f"⚠ Load failed: {str(ex)[:50]}")
            finally:
                loading["value"] = False
                _render()

        page.run_task(_work)

    def _refresh(reset: bool = False):
        nonlocal offset, has_more
        if reset:
            all_items.clear()
            offset = 0
            has_more = True

        feed_col.controls = [loading_row]
        safe_update()

        async def _work():
            nonlocal offset, has_more
            try:
                await _restore_session()
                res = await asyncio.to_thread(_fetch_page, 0, PAGE_SIZE)
                rows = res.data or []
                all_items.clear()
                all_items.extend(rows)
                offset = len(rows)
                has_more = len(rows) >= PAGE_SIZE
            except Exception as ex:
                print(f"[COMM_UPD] refresh error: {ex}")
                snack(f"⚠ Load failed: {str(ex)[:50]}")
            finally:
                _render()

        page.run_task(_work)

    # ── Initial load ────────────────────────────────────────
    _refresh(reset=True)

    # ════════════════════════════════════════════════════════
    #  BUILD UI
    # ════════════════════════════════════════════════════════
    return ft.View(
        route="/community-updates",
        bgcolor=T["bg"],
        padding=0,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/home"),
            ),
            title=ft.Column(
                [
                    ft.Text("Community Updates", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("کمیونٹی اپڈیٹس", size=11, color="#FFCDD2"),
                ],
                spacing=0,
            ),
            bgcolor=T["primary"],
            actions=[
                ft.IconButton(
                    icon=ft.Icons.REFRESH_ROUNDED,
                    icon_color="white",
                    tooltip="Refresh | تازہ کریں",
                    on_click=lambda e: _refresh(reset=True),
                ),
            ],
        ),
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=ft.Container(
                    width=min(600, page.width) if page.width else 600,
                    expand=True,
                    content=feed_col,
                ),
            ),
        ],
    )


