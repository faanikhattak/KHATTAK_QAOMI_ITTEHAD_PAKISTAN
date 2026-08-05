

#  home.py  —  Blood Fion App | Main View
#  REFACTORED: Independent Main View & Sidebar Scrolling with Toggle Support
# ════════════════════════════════════════════════════════════
from home_module.notification_bell import NotificationBell
from core.theme import Theme
import threading
import time
import flet as ft
from supabase import create_client
from services.database.db import http1_options
from typing import Callable, Optional, List
from home_module.home_config import get_logo_control
from support import show_support_dialog
from services.utils_services.location import add_geolocator, get_location
try:
    from core.app_version import APP_VERSION
except Exception:
    APP_VERSION = "1.0.0"

from home_module.home_config import (
    T, CARD_COLORS,
    I_BLOOD, I_REFRESH, I_LOGOUT, I_NOTIF, I_CAMPAIGN,
    I_WALL, I_EDIT, I_ERROR,
    is_admin, is_head_admin, is_verified_or_admin,
    set_app_setting, get_current_uid,
    supabase,
    _p, _pa, _ps, _m, _ms, _shadow, _circle,
)
from home_module.home_widgets import (
    build_hero, build_stats, build_leaders,
    build_actions, build_donor_row, build_quick_cta,
    build_sidebar, NewsTicker,
    section_header, empty_state,
)
from home_module.home_dialogs import (
    DialogManager,
    show_members, show_donors, show_requests,
    show_leaders_popup, show_logout_confirm,
    show_add_donor,
)

from home_module.media_picker import MediaPickerManager, _bust_url, _clean_url, PickedFile
import asyncio

_NETWORK_ERR_HINTS = (
    "connectionterminated", "remoteprotocolerror", "timeout", "httpcore",
    "connectionerror", "connectionreset", "network is unreachable",
    "temporarily unavailable", "name or service not known", "nodename",
)


def _is_network_error(err: BaseException) -> bool:
    if isinstance(err, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
        return True
    return any(h in str(err).lower() for h in _NETWORK_ERR_HINTS)


async def _to_thread_timeout(fn, *args, timeout: float = 12.0, **kwargs):
    return await asyncio.wait_for(asyncio.to_thread(fn, *args, **kwargs), timeout=timeout)


def _url_to_storage_path(url: str, bucket: str) -> str:
    marker = f"/object/public/{bucket}/"
    idx = url.find(marker)
    if idx == -1:
        return ""
    return url[idx + len(marker):].split("?")[0]


async def _delete_post(supabase_client, post: dict, on_done=None) -> None:
    import asyncio

    post_id   = post.get("id")
    media_url = post.get("media_url") or ""

    def _db_delete():
        supabase_client.table("community_updates").delete().eq("id", post_id).execute()
        print(f"[DELETE] post {post_id} removed")

    try:
        await asyncio.to_thread(_db_delete)
    except Exception as ex:
        print(f"[DELETE] DB error: {ex}")
        return

    if media_url:
        path = _url_to_storage_path(media_url, "app-assets")
        if path:
            def _storage_delete():
                supabase_client.storage.from_("app-assets").remove([path])
                print(f"[DELETE] storage file removed: {path}")
            try:
                await asyncio.to_thread(_storage_delete)
            except Exception as ex:
                print(f"[DELETE] storage error: {ex}")

    if on_done:
        on_done()


SUCCESS_GREEN = "#16A34A"


class SuccessPopup:
    def __init__(self, page: ft.Page, safe_update: Callable):
        self._page = page
        self._safe_update = safe_update
        self._active_dlgs: list = []

    def _close_dlg(self, dlg: ft.AlertDialog) -> None:
        try:
            dlg.open = False
            if dlg in self._active_dlgs:
                self._active_dlgs.remove(dlg)
            self._page.update()

            def _remove_from_overlay():
                try:
                    if dlg in self._page.overlay:
                        self._page.overlay.remove(dlg)
                        self._page.update()
                except Exception as ex:
                    print(f"[POPUP] overlay remove error: {ex}")

            threading.Timer(0.3, _remove_from_overlay).start()
        except Exception as ex:
            print(f"[POPUP] close error: {ex}")

    def close_all(self) -> None:
        for dlg in list(self._active_dlgs):
            self._close_dlg(dlg)

    def show(self, title: str, body: str, duration: float = 2.2):
        async def _open():
            try:
                dlg = ft.AlertDialog(
                    modal=False,
                    bgcolor=T.get("surface", "#FFFFFF"),
                    shape=ft.RoundedRectangleBorder(radius=24),
                    content=ft.Container(
                        width=260, padding=_pa(28),
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=SUCCESS_GREEN, size=60),
                                ft.Container(height=10),
                                ft.Text(
                                    title, size=17, weight=ft.FontWeight.W_800,
                                    color=T.get("on_surface", "#212121"),
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Container(height=6),
                                ft.Text(body, size=13, color="#757575", text_align=ft.TextAlign.CENTER),
                                ft.Container(height=12),
                                ft.TextButton(
                                    "Close",
                                    on_click=lambda e: self._close_dlg(dlg),
                                    style=ft.ButtonStyle(color=T["primary"]),
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0, tight=True,
                        ),
                    ),
                )

                self._active_dlgs.append(dlg)
                if dlg not in self._page.overlay:
                    self._page.overlay.append(dlg)
                dlg.open = True
                self._page.update()

                import asyncio
                await asyncio.sleep(duration)
                self._close_dlg(dlg)

            except Exception as ex:
                print(f"[POPUP] error: {ex}")

        try:
            self._page.run_task(_open)
        except Exception:
            pass


class MediaPreviewDialog:
    def __init__(self, page: ft.Page, safe_update: Callable):
        self._page = page
        self._safe_update = safe_update
        self._active_dlgs: List[ft.AlertDialog] = []

    def _close_all(self):
        for dlg in self._active_dlgs:
            try:
                dlg.open = False
            except Exception:
                pass
        self._active_dlgs.clear()
        self._safe_update()

    def show_video(self, url: str, title: str = "",
                   role: str = "member", item: dict = None,
                   supabase_client=None, on_deleted=None):
        try:
            clean_url = str(url).strip().replace("'", "").replace('"', "")
            if not clean_url or clean_url.lower() == "none":
                return

            self._close_all()

            async def _launch():
                await self._page.launch_url(clean_url)
            
            self._page.run_task(_launch)
            
        except Exception as ex:
            print(f"[VIDEO_LAUNCH_ERROR]: {ex}")

    def show_image(self, url: str, title: str = "Preview"):
        async def _open():
            try:
                self._close_all()
                vh = min(340, int((self._page.height or 600) * 0.50))
                vw = min(500, int((self._page.width or 400) * 0.90))

                image = ft.Image(src=url, fit="contain", width=vw, height=vh)
                
                dlg = ft.AlertDialog(
                    modal=True, bgcolor="#000000",
                    barrier_color="#CC000000",
                    shape=ft.RoundedRectangleBorder(radius=16),
                    content_padding=ft.padding.all(0),
                    content=ft.Container(
                        width=vw,
                        padding=ft.padding.only(top=4, bottom=8, left=4, right=4),
                        bgcolor="#000000", border_radius=16,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            title, size=13,
                                            weight=ft.FontWeight.W_600,
                                            color="white", expand=True,
                                            overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True,
                                        ),
                                        ft.IconButton(
                                            ft.Icons.CLOSE,
                                            icon_color="white",
                                            icon_size=20,
                                            tooltip="Close",
                                            on_click=lambda e: self._close_dialog(dlg),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Container(
                                    content=image, width=vw, height=vh,
                                    bgcolor="#000000", border_radius=12,
                                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                ),
                            ],
                            spacing=4, tight=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                )

                self._active_dlgs.append(dlg)
                if dlg not in self._page.overlay:
                    self._page.overlay.append(dlg)
                dlg.open = True
                self._page.update()

            except Exception as ex:
                print(f"[IMAGE] preview error: {ex}")

        self._page.run_task(_open)

    def _close_dialog(self, dlg: ft.AlertDialog):
        async def _close():
            try:
                dlg.open = False
                if dlg in self._active_dlgs:
                    self._active_dlgs.remove(dlg)
                self._page.update()
            except Exception:
                pass
        self._page.run_task(_close)

    def cleanup(self):
        self._close_all()


class SettingsPoller:
    def __init__(self, interval: int = 5):
        self._interval = interval
        self._running = False
        self._lock = threading.Lock()
        self._callbacks: list = []
        self._last: dict = {}

        clean_url = str(supabase.supabase_url).strip()
        clean_key = str(supabase.supabase_key).strip()
        self._public_supabase = create_client(clean_url, clean_key, options=http1_options())

    def register(self, state: dict, build_fn: Callable, active_fn: Callable, page: ft.Page) -> None:
        with self._lock:
            self._callbacks.append((state, build_fn, active_fn, page))

    def unregister(self, build_fn: Callable) -> None:
        with self._lock:
            self._callbacks = [
                (s, b, a, p) for s, b, a, p in self._callbacks if b is not build_fn
            ]

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        import concurrent.futures
        while self._running:
            try:
                def _fetch():
                    return (
                        self._public_supabase.table("app_settings")
                        .select("key,value")
                        .in_("key", ["hero_bg_url", "org_logo_url"])
                        .execute()
                        .data or []
                    )
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    rows = pool.submit(_fetch).result(timeout=10)
                finally:
                    pool.shutdown(wait=False)

                changed: dict = {}
                with self._lock:
                    for r in rows:
                        k, v = r["key"], _clean_url(r.get("value")) or None
                        if self._last.get(k) != v:
                            changed[k] = v
                            self._last[k] = v

                if changed:
                    with self._lock:
                        cbs = list(self._callbacks)

                    for state, build_fn, active_fn, pg in cbs:
                        try:
                            if not active_fn():
                                continue

                            updated = False
                            if "hero_bg_url" in changed:
                                new_bg = _bust_url(changed["hero_bg_url"])
                                if _clean_url(state.get("bg_url")) != changed["hero_bg_url"]:
                                    state["bg_url"] = new_bg
                                    updated = True

                            if "org_logo_url" in changed:
                                new_logo = _bust_url(changed["org_logo_url"])
                                if _clean_url(state.get("logo_url")) != changed["org_logo_url"]:
                                    state["logo_url"] = new_logo
                                    updated = True

                            if updated:
                                async def _rebuild(fn=build_fn, p=pg):
                                    fn()
                                try:
                                    pg.run_task(_rebuild)
                                except Exception as ex:
                                    print(f"[POLLER] run_task error: {ex}")

                        except Exception as ex:
                            print(f"[POLLER] rebuild error: {ex}")

            except Exception as ex:
                print(f"[POLLER] poll error: {ex}")

            time.sleep(self._interval)


def view(page: ft.Page) -> ft.View:
    import asyncio

    _poller = SettingsPoller(interval=5)
    _poller.start()

    geo = add_geolocator(page)

    def sess_get(key: str, default=None):
        try:
            if hasattr(page.session, "_Session__store"):
                return page.session._Session__store.get(key) or default
            elif hasattr(page.session, "get_value"):
                return page.session.get_value(key) or default
            else:
                return page.session.get(key) or default
        except Exception:
            return default

    def sess_set(key: str, val) -> None:
        try:
            if hasattr(page.session, "_Session__store"):
                page.session._Session__store.set(key, val)
            elif hasattr(page.session, "set_value"):
                page.session.set_value(key, val)
            else:
                page.session.set(key, val)
        except Exception:
            pass

    _active = [True]

    import threading
    _ui_lock = threading.RLock()

    clean_url = str(supabase.supabase_url).strip()
    clean_key = str(supabase.supabase_key).strip()
    user_supabase = create_client(clean_url, clean_key, options=http1_options())

    state: dict = {
        "requests": [], 
        "news": [], 
        "donors": [],
        "leaders": [],
        "stats": {"members": 0, "donors": 0, "requests": 0},
        "bg_url": None,
        "logo_url": None,
        "user_id": sess_get("user_id", ""),
        "_loaded_once": False,
        "_retry_count": 0,
    }

    state["profile"] = {
        "id": sess_get("user_id", ""),
        "role": sess_get("role") or "member",
        "full_name": sess_get("full_name") or "ممبر",
        "blood_group": sess_get("blood_group", ""),
        "email_verified": sess_get("email_verified", "False"),
        "is_approved": sess_get("is_approved", "False"),
        "avatar_url": sess_get("avatar_url", ""),
    }

    def safe_update() -> None:
        if not _active[0]:
            return
        async def _coro():
            try:
                page.update()
            except Exception:
                pass
        try:
            page.run_task(_coro)
        except Exception as ex:
            print(f"[UPDATE] failed: {ex}")

    def snack(msg: str, color: str = T["primary"]) -> None:
        if not _active[0]:
            return
        async def _show():
            try:
                sb = ft.SnackBar(
                    content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD, size=13),
                    bgcolor=color,
                    duration=3500,
                )
                page.overlay.append(sb)
                sb.open = True
                page.update()
            except Exception:
                pass
        try:
            page.run_task(_show)
        except Exception as ex:
            print(f"[SNACK] error: {ex}")

    def go(route: str) -> None:
        async def _coro():
            try:
                if hasattr(page, "push_route"):
                    await page.push_route(route)
                else:
                    page.go(route)
            except Exception as ex:
                print(f"[GO] nav error: {ex}")
        try:
            page.run_task(_coro)
        except Exception:
            snack(f"Navigation error: {route}")

    media_manager = MediaPickerManager(page, access_token=sess_get("access_token", ""))
    _notif_bell = NotificationBell(
        page=page,
        supabase_client=user_supabase,
        user_id=sess_get("user_id", ""),
        safe_update=safe_update,
    )
    media_preview = MediaPreviewDialog(page, safe_update)
    success_popup = SuccessPopup(page, safe_update)

    bg_btn_ref: list = [None]
    logo_btn_ref: list = [None]

    def pick_bg(e=None) -> None:
        if bg_btn_ref[0] and bg_btn_ref[0].disabled:
            return

        async def _trigger() -> None:
            def _on_complete(url: str) -> None:
                async def _rebuild() -> None:
                    build_home_ui()
                try:
                    page.run_task(_rebuild)
                except Exception:
                    pass
                success_popup.show("Background Updated!", "New background saved.")

            await media_manager.upload_background_async(
                state, btn_ref=bg_btn_ref, on_complete=_on_complete
            )

        page.run_task(_trigger)

    def pick_logo(e=None) -> None:
        if logo_btn_ref[0] and logo_btn_ref[0].disabled:
            return

        async def _trigger() -> None:
            def _on_complete(url: str) -> None:
                async def _rebuild() -> None:
                    build_home_ui()
                try:
                    page.run_task(_rebuild)
                except Exception:
                    pass
                success_popup.show("Logo Updated!", "New logo saved.")

            await media_manager.upload_logo_async(
                state, btn_ref=logo_btn_ref, on_complete=_on_complete
            )

        page.run_task(_trigger)

    _post_update_state = {
        "attached_file": None,
        "file_label": None,
        "title_field": None,
        "content_field": None,
        "dialog": None,
    }

    def pick_media_attach() -> None:
        async def _trigger() -> None:
            def on_file_picked(picked: PickedFile) -> None:
                _post_update_state["attached_file"] = picked
                if _post_update_state.get("file_label"):
                    _post_update_state["file_label"].value = f"📎 {picked.name}"
                    _post_update_state["file_label"].color = T["primary"]
                    _post_update_state["file_label"].italic = False
                    try:
                        _post_update_state["file_label"].update()
                    except Exception:
                        pass
                snack(f"Attached: {picked.name}", T["green"])

            await media_manager.attach_media_async(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "mp4", "mov", "avi", "mkv", "webm"],
                on_picked=on_file_picked,
            )

        page.run_task(_trigger)

    def pick_media_publish(on_publish_complete=None) -> None:
        async def _trigger() -> None:
            attached = _post_update_state.get("attached_file")

            if not attached:
                if on_publish_complete:
                    try:
                        on_publish_complete(None, False)
                    except Exception as ex:
                        print(f"[PUBLISH] on_publish_complete error (no media): {ex}")
                return

            def on_upload_complete(url: str, is_vid: bool) -> None:
                if on_publish_complete:
                    try:
                        on_publish_complete(url, is_vid)
                    except Exception as ex:
                        print(f"[PUBLISH] on_publish_complete error (with media): {ex}")

            media_manager._picked_file = attached
            await media_manager.upload_attached_async(
                bucket_path="home/updates",
                on_complete=on_upload_complete,
            )

        page.run_task(_trigger)

    content_col = ft.Column(
        controls=[], spacing=0, expand=True,
    )

    _ui_state: dict = {"sidebar_open": True, "is_desktop": None}
    menu_btn_ref: list = [None]

    sidebar_holder = ft.Container(expand=True)
    desktop_sidebar_wrapper = ft.Container(visible=True)

    def _set_sidebar_visual(open_: bool) -> None:
        is_desktop = _ui_state.get("is_desktop", False)
        if is_desktop:
            desktop_sidebar_wrapper.visible = open_
        else:
            mobile_sidebar_panel.left = 0 if open_ else -260
            sidebar_backdrop.visible = open_
            
        async def _coro():
            try:
                page.update()
            except Exception:
                pass
        try:
            page.run_task(_coro)
        except Exception:
            try:
                page.update()
            except Exception:
                pass

    def _close_sidebar(e=None) -> None:
        _ui_state["sidebar_open"] = False
        _set_sidebar_visual(False)

    def _toggle_sidebar(e=None) -> None:
        _ui_state["sidebar_open"] = not _ui_state["sidebar_open"]
        _set_sidebar_visual(_ui_state["sidebar_open"])

    sidebar_backdrop = ft.GestureDetector(
        left=0, top=0, right=0, bottom=0,
        on_tap=_close_sidebar,
        content=ft.Container(expand=True, bgcolor="#66000000"),
    )
    sidebar_backdrop.visible = False

    mobile_sidebar_panel = ft.Container(
        top=0, bottom=0, left=-260,
        width=240,
        bgcolor=T["bg"],
        animate_position=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
        shadow=_shadow(20, "#55000000"),
        content=sidebar_holder,
    )

    news_ticker = NewsTicker()
    news_ticker.start()

    _post_action_ref: dict = {"fn": None}

    def _post_update_dispatch(e=None):
        fn = _post_action_ref.get("fn")
        if fn:
            fn(e)

    post_update_fab = ft.Container(
        right=16, bottom=16,
        visible=False,
        content=ft.FloatingActionButton(
            icon=ft.Icons.ADD_ROUNDED,
            foreground_color="white",
            bgcolor=T["primary"],
            shape=ft.CircleBorder(),
            tooltip="Post Update | نئی خبر شامل کریں",
            on_click=_post_update_dispatch,
        ),
    )

    def build_home_ui() -> None:
        if not _active[0]:
            return

        def _get_home_session_val(key: str) -> str:
            try:
                if hasattr(page.session, "_Session__store"):
                    return page.session._Session__store.get(key) or ""
                elif hasattr(page.session, "get_value"):
                    return page.session.get_value(key) or ""
                else:
                    return page.session.get(key) or ""
            except Exception:
                return ""

        role = _get_home_session_val("role") or "member"
        full_name = _get_home_session_val("full_name") or "ممبر"
        user_id = _get_home_session_val("user_id")

        current_user_profile = {
            "id": user_id,
            "role": role,
            "full_name": full_name,
            "blood_group": _get_home_session_val("blood_group"),
            "email_verified": _get_home_session_val("email_verified"),
            "is_approved": _get_home_session_val("is_approved"),
            "avatar_url": _get_home_session_val("avatar_url"),
        }

        async def _handle_update_location(e=None):
            try:
                lat, lon = await get_location(page, geo)

                if lat == 0.0 and lon == 0.0:
                    snack = ft.SnackBar(
                        content=ft.Text("Could not determine location | لوکیشن معلوم نہیں ہو سکی"),
                        bgcolor="#C62828",
                    )
                else:
                    from services.database.db import supabase
                    supabase.table("profiles").update({
                        "latitude": lat,
                        "longitude": lon,
                    }).eq("id", current_user_profile.get("id")).execute()

                    snack = ft.SnackBar(
                        content=ft.Text("Location updated | لوکیشن اپڈیٹ ہو گئی"),
                        bgcolor="#2E7D32",
                    )

                page.overlay.append(snack)
                snack.open = True
                page.update()

            except Exception as ex:
                snack = ft.SnackBar(
                    content=ft.Text("Location update failed | لوکیشن اپڈیٹ ناکام"),
                    bgcolor="#C62828",
                )
                page.overlay.append(snack)
                snack.open = True
                page.update()

        try:
            dm = DialogManager(page, safe_update)

            def _show_members(e=None): show_members(dm, page, safe_update)
            def _show_donors(e=None): show_donors(dm, page, safe_update)
            def _show_requests(e=None): show_requests(dm, safe_update)

            def _request_choice(e=None):
                if dm.busy:
                    return
                dm.busy = True
                dlg_ref: list = [None]

                def _close(ev=None):
                    dm.busy = False
                    if dlg_ref[0]:
                        dm.close(dlg_ref[0])

                def _go_my_requests(ev=None):
                    _close()
                    _show_requests()

                def _go_new_request(ev=None):
                    _close()
                    go("/request")

                dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Blood Request | خون کی درخواست",
                                   weight=ft.FontWeight.BOLD, size=15, color=T["primary"]),
                    content=ft.Container(
                        width=300,
                        content=ft.Column(
                            [
                                ft.Text(
                                    "What would you like to do? | آپ کیا کرنا چاہتے ہیں؟",
                                    size=12, color=T["text_sub"],
                                ),
                                ft.Container(height=8),
                                ft.ElevatedButton(
                                    "📋 My Requests | میری درخواستیں",
                                    width=float("inf"),
                                    style=ft.ButtonStyle(
                                        bgcolor=T["surface_2"], color=T["text"],
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                    ),
                                    on_click=_go_my_requests,
                                ),
                                ft.Container(height=8),
                                ft.ElevatedButton(
                                    "🩸 Request Blood | نئی درخواست",
                                    width=float("inf"),
                                    style=ft.ButtonStyle(
                                        bgcolor=T["primary"], color="white",
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                    ),
                                    on_click=_go_new_request,
                                ),
                            ],
                            tight=True, spacing=0,
                        ),
                    ),
                    actions=[ft.TextButton("Cancel | منسوخ", on_click=_close)],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                dlg_ref[0] = dlg
                dm.open(dlg)

            def _show_updates(e=None): page.go("/community-updates")
            def _show_leaders(e=None): go("/leaders_view")

            def _show_post(e=None):
                async def _on_submit(title: str, body: str, media_url, is_vid):
                    import asyncio

                    dlg = _post_update_state.get("dialog")
                    if dlg is not None:
                        try:
                            dlg.open = False
                            if hasattr(page, "close"):
                                page.close(dlg)
                            page.update()
                        except Exception as ce:
                            print(f"[POST] Immediate close error: {ce}")
                    _post_update_state["dialog"] = None

                    uid = _get_home_session_val("user_id") or state.get("user_id") or ""
                    media_type = "video" if is_vid else ("image" if media_url else "")
                    payload = {
                        "title": title,
                        "content": body,
                        "media_url": media_url or None,
                        "media_type": media_type or None,
                        "admin_id": str(uid),
                    }
                    try:
                        await asyncio.to_thread(
                            lambda: user_supabase.table("community_updates").insert(payload).execute()
                        )
                    except Exception as ex:
                        snack("❌ Publish failed!", T["primary"])
                        return

                    _post_update_state["attached_file"] = None
                    if _post_update_state.get("title_field"):
                        _post_update_state["title_field"].value = ""
                    if _post_update_state.get("content_field"):
                        _post_update_state["content_field"].value = ""
                    if _post_update_state.get("file_label"):
                        _post_update_state["file_label"].value = "No file selected"
                        _post_update_state["file_label"].color = "grey"
                        _post_update_state["file_label"].italic = True

                    snack("✅ Update published!", T["green"])
                    load_data()

                from home_module.home_widgets import build_post_dialog
                dlg = build_post_dialog(
                    page=page,
                    dm=dm,
                    on_submit=_on_submit,
                    pick_media_attach=pick_media_attach,
                    pick_media_publish=pick_media_publish,
                    post_update_state=_post_update_state,
                )
                _post_update_state["dialog"] = dlg
                try:
                    page.show_dialog(dlg)
                except Exception as ex:
                    print(f"[POST] show_dialog error: {ex}")
            
            def _show_add_donor(e=None): show_add_donor(dm, state, load_data, snack, safe_update)

            hero = build_hero(
                page=page,
                profile=current_user_profile,
                bg_url=state.get("bg_url"),
                logo_url=state.get("logo_url"),
                on_tap_bg=pick_bg,
                on_tap_logo=pick_logo,
                on_nav_profile=lambda e: go("/profile"),
            )

            stats_row = ft.Row(
                controls=[
                    build_stats(
                        state.get("stats", {"members": 0, "donors": 0, "requests": 0}),
                        on_members=_show_members,
                        on_donors=_show_donors,
                        on_requests=_show_requests,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )

            action_callbacks = {
                "request":         _request_choice,
                "donor":           lambda e: go("/donor"),
                "requests_popup":  _show_requests,
                "profile":         lambda e: go("/profile"),
                "updates":         _show_updates,
                "admin":           lambda e: go("/admin"),
                "leaderboard":     lambda e: go("/leaderboard"),
                "feedback":        lambda e: go("/feedback"),
                "support":         lambda e: show_support_dialog(page, current_user_profile),
                "update_location": lambda e: page.run_task(_handle_update_location),
                "leaders_view":    lambda e: go("/leaders_view"),
                "leaders":         lambda e: go("/leaders_view"),
            }

            quick_cta = build_quick_cta(action_callbacks)
            actions = build_actions(role, action_callbacks)
            leaders = build_leaders(
                on_see_all=_show_leaders,
                leaders_data=state.get("leaders") or None,
                page=page,
            )

            donor_row_ctrl = (
                build_donor_row(state.get("donors", []), on_see_all=_show_donors)
                if state.get("donors") else ft.Container()
            )

            news_strip = news_ticker.widget

            _post_action_ref["fn"] = _show_post
            post_update_fab.visible = is_admin(role)

            req_section = []
            main_ctrls: list[ft.Control] = [
                hero,
                news_strip,
                stats_row,
                quick_cta,
                donor_row_ctrl,
                ft.Container(height=8),
                leaders,
                actions,
                *req_section,
                ft.Container(height=56),
            ]
            
            main_scroll_view = ft.Column(
                controls=main_ctrls,
                spacing=0,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )

            _w = page.width or 0
            if _w > 0:
                is_desktop = _w >= 700
                _ui_state["is_desktop"] = is_desktop
            else:
                is_desktop = _ui_state.get("is_desktop")
                if is_desktop is None:
                    is_desktop = False

            sidebar_callbacks = {
                "members": _show_members,
                "donors": _show_donors,
                "requests": _show_requests,
                "updates": _show_updates,
                "nav_request": lambda e: go("/request"),
                "nav_donor": lambda e: go("/donor"),
                "nav_profile": lambda e: go("/profile"),
                "nav_admin": lambda e: go("/admin"),
                "leaderboard": lambda e: go("/leaderboard"),
                "feedback":    lambda e: go("/feedback"),
                "support":     lambda e: show_support_dialog(page, current_user_profile),
                "update_location": lambda e: page.run_task(_handle_update_location),
                "leaders_view":    lambda e: go("/leaders_view"),
                "leaders":         lambda e: go("/leaders_view"),
            }

            if is_desktop:
                sidebar = build_sidebar(current_user_profile, state.get("stats", {}), sidebar_callbacks)
                
                desktop_sidebar_scroll = ft.Column(
                    controls=[sidebar],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                )

                desktop_sidebar_wrapper.content = desktop_sidebar_scroll
                desktop_sidebar_wrapper.visible = _ui_state.get("sidebar_open", True)
                desktop_sidebar_wrapper.width = 250

                new_controls: list[ft.Control] = [ft.Row(
                    [
                        desktop_sidebar_wrapper,
                        ft.VerticalDivider(width=1, color=T["primary_md"]),
                        ft.Container(content=main_scroll_view, expand=True),
                    ],
                    spacing=0, expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )]
            else:
                def _wrap_close(fn):
                    def _inner(e=None):
                        _close_sidebar()
                        if fn:
                            fn(e)
                    return _inner

                mobile_sidebar_callbacks = {k: _wrap_close(v) for k, v in sidebar_callbacks.items()}
                built_sidebar = build_sidebar(
                    current_user_profile, state.get("stats", {}), mobile_sidebar_callbacks
                )
                
                close_row = ft.Container(
                    padding=_ps(h=4, v=2),
                    content=ft.Row(
                        [ft.Container(expand=True), ft.GestureDetector(
                            on_tap=_close_sidebar,
                            mouse_cursor=ft.MouseCursor.CLICK,
                            content=ft.Container(
                                width=32, height=32, border_radius=16,
                                bgcolor=T["surface"], shadow=_shadow(4, "#1A000000"),
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(ft.Icons.CLOSE_ROUNDED, color=T["primary"], size=18),
                            ),
                        )],
                    ),
                )
                
                sidebar_holder.content = ft.Column(
                    [close_row, built_sidebar], 
                    spacing=0, 
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                )
                new_controls = [main_scroll_view]

            with _ui_lock:
                if not _active[0]:
                    return
                content_col.controls = new_controls
                try:
                    page.update()
                except Exception as ex:
                    print(f"[UI] page.update() failed: {ex}")

        except Exception as ex:
            import traceback
            traceback.print_exc()
            error_ctrls = [ft.Container(
                expand=True, padding=_pa(32),
                content=ft.Column(
                    [
                        ft.Icon(I_ERROR, color=T["primary"], size=52),
                        ft.Text(f"Render error: {str(ex)[:80]}", color=T["primary"], text_align=ft.TextAlign.CENTER),
                        ft.FilledButton(
                            "Retry",
                            on_click=lambda e: build_home_ui(),
                            style=ft.ButtonStyle(
                                bgcolor=T["primary"], color="white",
                                shape=ft.RoundedRectangleBorder(radius=16),
                            ),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
            )]
            with _ui_lock:
                if _active[0]:
                    content_col.controls = error_ctrls
                    try:
                        page.update()
                    except Exception:
                        pass

    def _show_reconnecting_ui(attempt: int, wait_s: float) -> None:
        if state.get("_loaded_once") or not _active[0]:
            return
        ctrls = [ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
            content=ft.Column(
                [
                    ft.ProgressRing(width=44, height=44, stroke_width=4, color=T["primary"]),
                    ft.Container(height=14),
                    ft.Text("Connection issue — retrying…", size=14, color=T["primary"], weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                    ft.Text("رابطہ منقطع — دوبارہ کوشش کی جا رہی ہے…", size=12, color=T["text_sub"], text_align=ft.TextAlign.CENTER),
                    ft.Container(height=16),
                    ft.OutlinedButton(
                        "Retry Now | ابھی کوشش کریں",
                        on_click=lambda e: load_data(),
                        style=ft.ButtonStyle(
                            color=T["primary"],
                            shape=ft.RoundedRectangleBorder(radius=16),
                        ),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0, tight=True,
            ),
        )]
        with _ui_lock:
            if not _active[0]:
                return
            content_col.controls = ctrls
        try:
            page.update()
        except Exception:
            pass

    def load_data() -> None:
        def _get_session_val(key: str) -> str:
            try:
                if hasattr(page.session, "_Session__store"):
                    return page.session._Session__store.get(key) or ""
                elif hasattr(page.session, "get_value"):
                    return page.session.get_value(key) or ""
                else:
                    return page.session.get(key) or ""
            except Exception:
                return ""

        def _set_session_val(key: str, val: str) -> None:
            try:
                if hasattr(page.session, "_Session__store"):
                    page.session._Session__store.set(key, val)
                elif hasattr(page.session, "set_value"):
                    page.session.set_value(key, val)
                else:
                    page.session.set(key, val)
            except Exception:
                pass

        async def _work() -> None:
            import asyncio
            if not _active[0]:
                return
            go_login = False

            try:
                access_token  = _get_session_val("access_token")
                refresh_token = _get_session_val("refresh_token")

                if not access_token:
                    go_login = True
                    return

                try:
                    await _to_thread_timeout(
                        user_supabase.auth.set_session,
                        access_token,
                        refresh_token or "",
                        timeout=10,
                    )
                except Exception as ses_ex:
                    if _is_network_error(ses_ex):
                        raise ses_ex

                try:
                    ur = await _to_thread_timeout(user_supabase.auth.get_user, timeout=10)
                    if not ur or not ur.user:
                        if access_token:
                            raise RuntimeError("Supabase returned empty user response due to network congestion.")
                        go_login = True
                        return
                    uid = ur.user.id
                except Exception as gu_ex:
                    if _is_network_error(gu_ex):
                        raise gu_ex
                    else:
                        gu_str = str(gu_ex).lower()
                        if "invalid_jwt" in gu_str or "expired" in gu_str:
                            go_login = True
                            return
                        raise gu_ex

                state["user_id"] = uid
                _notif_bell._user_id = str(uid)

                try:
                    def _fetch_profile():
                        return user_supabase.table("profiles").select("*").eq("id", uid).single().execute()
                    p = await _to_thread_timeout(_fetch_profile, timeout=10)
                    profile_data = p.data or {}

                    _set_session_val("role", str(profile_data.get("role", "member")))
                    _set_session_val("full_name", str(profile_data.get("full_name", "ممبر")))
                    _set_session_val("blood_group", str(profile_data.get("blood_group", "")))
                    _set_session_val("email_verified", str(profile_data.get("email_verified", "False")))
                    _set_session_val("is_approved", str(profile_data.get("is_approved", "False")))
                    _set_session_val("avatar_url", str(profile_data.get("avatar_url", "") or ""))

                except Exception as pex:
                    _set_session_val("role", "member")
                    _set_session_val("full_name", "ممبر")

                try:
                    def _fetch_settings():
                        return user_supabase.table("app_settings").select("key,value").in_("key", ["hero_bg_url", "org_logo_url"]).execute().data or []
                    rows = await _to_thread_timeout(_fetch_settings, timeout=10)
                    for r in rows:
                        if r["key"] == "hero_bg_url":
                            state["bg_url"] = _bust_url(r["value"]) or None
                        elif r["key"] == "org_logo_url":
                            state["logo_url"] = _bust_url(r["value"]) or None
                except Exception as ex:
                    print(f"[DATA] app_settings error: {ex}")

                for tbl, key in [("profiles", "members"), ("donors", "donors")]:
                    try:
                        def _count(t=tbl):
                            return user_supabase.table(t).select("id", count="exact").execute()
                        res = await _to_thread_timeout(_count, timeout=8)
                        state["stats"][key] = res.count or 0
                    except Exception:
                        pass

                try:
                    def _fetch_donors():
                        return user_supabase.table("donors").select("*").order("created_at", desc=True).limit(16).execute().data or []
                    state["donors"] = await _to_thread_timeout(_fetch_donors, timeout=10)
                except Exception:
                    state["donors"] = []

                try:
                    def _fetch_requests():
                        return (
                            user_supabase.table("blood_requests")
                            .select("*")
                            .in_("status", ["pending", "matching", "in_progress"])
                            .order("created_at", desc=True)
                            .limit(10)
                            .execute()
                            .data or []
                        )
                    state["requests"] = await _to_thread_timeout(_fetch_requests, timeout=10)
                    state["stats"]["requests"] = len(state["requests"])
                except Exception:
                    state["requests"] = []

                try:
                    def _fetch_leaders():
                        return (
                            user_supabase.table("leaders")
                            .select("*")
                            .order("display_order", desc=False)
                            .execute()
                            .data or []
                        )
                    state["leaders"] = await _to_thread_timeout(_fetch_leaders, timeout=10)
                except Exception as ex:
                    try:
                        def _fetch_leaders_fallback():
                            return (
                                user_supabase.table("leaders")
                                .select("*")
                                .execute()
                                .data or []
                            )
                        state["leaders"] = await _to_thread_timeout(_fetch_leaders_fallback, timeout=10)
                    except Exception as ex2:
                        state["leaders"] = []

                try:
                    def _fetch_news():
                        return (
                            user_supabase.table("flash_ticker")
                            .select("*")
                            .eq("is_active", True)
                            .order("created_at", desc=True)
                            .limit(8)
                            .execute()
                            .data or []
                        )
                    state["news"] = await _to_thread_timeout(_fetch_news, timeout=8)
                    news_ticker.update_text(state["news"])
                except Exception:
                    state["news"] = []

                if _active[0]:
                    state["_retry_count"] = 0
                    try:
                        await asyncio.wait_for(_notif_bell.refresh(), timeout=10)
                    except Exception as bell_ex:
                        print(f"[BELL] refresh skipped: {bell_ex}")
                    build_home_ui()
                    state["_loaded_once"] = True

            except Exception as err:
                if _is_network_error(err):
                    state["_retry_count"] = state.get("_retry_count", 0) + 1
                    attempt = state["_retry_count"]
                    wait_s = min(3 * (2 ** (attempt - 1)), 20)
                    if attempt >= 2:
                        _show_reconnecting_ui(attempt, wait_s)

                    await asyncio.sleep(wait_s)
                    if _active[0]:
                        try:
                            page.run_task(load_data)
                        except Exception:
                            pass
                    return

                err_ctrls = [ft.Container(
                    expand=True, padding=_pa(32),
                    content=ft.Column([
                        ft.Icon(I_ERROR, color=T["primary"], size=52),
                        ft.Text(f"Load error: {str(err)[:60]}", color=T["primary"], text_align=ft.TextAlign.CENTER),
                        ft.FilledButton(
                            "Retry",
                            on_click=lambda e: load_data(),
                            style=ft.ButtonStyle(
                                bgcolor=T["primary"], color="white",
                                shape=ft.RoundedRectangleBorder(radius=16),
                            ),
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
                )]
                if _active[0]:
                    with _ui_lock:
                        content_col.controls = err_ctrls
                    try:
                        page.update()
                    except Exception:
                        pass

            finally:
                try:
                    active_dlg = _post_update_state.get("dialog")
                    if active_dlg:
                        if hasattr(page, "close"):
                            page.close(active_dlg)
                        else:
                            active_dlg.open = False

                        if _post_update_state.get("title_field"):
                            _post_update_state["title_field"].value = ""
                        if _post_update_state.get("content_field"):
                            _post_update_state["content_field"].value = ""
                        page.update()
                except Exception as dlg_err:
                    print(f"[UI] Dialog safe-close skipped: {dlg_err}")

                if go_login:
                    _active[0] = False
                    try:
                        if hasattr(page, "push_route"):
                            await page.push_route("/login")
                        else:
                            page.go("/login")
                    except Exception as nav_ex:
                        print(f"[DATA] Redirect failed: {nav_ex}")

        try:
            page.run_task(_work)
        except Exception as ex:
            print(f"[DATA] run_task error: {ex}")

    _APPBAR_HEIGHT = 50
    _MENU_BTN_SIZE = 40
    _LOGO_SIZE     = 34
    _SAFE_GAP      = 14

    logo_container = get_logo_control(
        logo_url=state.get("logo_url"), width=_LOGO_SIZE, height=_LOGO_SIZE,
    )

    menu_btn = ft.IconButton(
        ft.Icons.MENU_ROUNDED,
        icon_color="white",
        icon_size=20,
        width=_MENU_BTN_SIZE,
        height=_MENU_BTN_SIZE,
        tooltip="Toggle Menu | مینو دیکھیں/چھپائیں",
        visible=True,
        on_click=_toggle_sidebar,
    )
    menu_btn_ref[0] = menu_btn

    menu_box = ft.Container(
        width=_MENU_BTN_SIZE, height=_MENU_BTN_SIZE,
        alignment=ft.Alignment(0, 0),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=menu_btn,
    )
    logo_box = ft.Container(
        width=_LOGO_SIZE, height=_LOGO_SIZE,
        alignment=ft.Alignment(0, 0),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=logo_container,
    )

    import tomllib
    try:
        with open("pyproject.toml", "rb") as f:
            _toml_data = tomllib.load(f)
            current_version = _toml_data.get("project", {}).get("version", "1.0.0")
    except Exception:
        current_version = "1.0.0"

    app_bar = ft.AppBar(
        toolbar_height=_APPBAR_HEIGHT,
        leading=ft.Row(
            [menu_box, ft.Container(width=_SAFE_GAP), logo_box],
            spacing=5, tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        leading_width=_MENU_BTN_SIZE + _SAFE_GAP + _LOGO_SIZE + 8,
        title=ft.Column(
            [
                ft.Row(
                    controls=[
                        ft.Text("KHATTAK QAOMI ITTEHAD PAKISTAN", size=10, weight=ft.FontWeight.W_800, color="white", no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f" • v{current_version}", size=9, color="#FFCDD2", no_wrap=True),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                ft.Row(
                    [
                        ft.Text("خٹک قومی اتحاد پاکستان", size=9, color="#FFCDD2", no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    spacing=0, tight=True,
                ),
            ],
            spacing=0, tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=T["primary"],
        elevation=0,
        actions=[
            _notif_bell.build(),
            ft.IconButton(I_REFRESH, icon_color="white", icon_size=22, tooltip="Refresh", on_click=lambda e: load_data()),
            ft.IconButton(I_LOGOUT, icon_color="white", icon_size=22, tooltip="Logout", on_click=lambda e: show_logout_confirm(DialogManager(page, safe_update), page, lambda: None, safe_update)),
        ],
    )

    _poller.register(state, build_home_ui, lambda: _active[0], page)

    def _on_disconnect(e=None):
        _active[0] = False
        _poller.unregister(build_home_ui)
        _poller.stop()
        news_ticker.stop()
        media_manager.cleanup()
        media_preview.cleanup()

    page.on_disconnect = _on_disconnect

    with _ui_lock:
        content_col.controls = [ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
            content=ft.Column(
                [
                    ft.ProgressRing(width=48, height=48, stroke_width=4, color=T["primary"]),
                    ft.Container(height=12),
                    ft.Text("Loading…", size=14, color=T["primary"], weight=ft.FontWeight.W_600),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0, tight=True,
            ),
        )]

    load_data()

    return ft.View(
        route="/home",
        appbar=app_bar,
        bgcolor=T["bg"],
        padding=0,
        controls=[ft.Stack(
            [content_col, post_update_fab, sidebar_backdrop, mobile_sidebar_panel],
            expand=True,
        )],
    )