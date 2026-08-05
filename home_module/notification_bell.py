
















# =============================fine but x not ===================================
#  home_module/notification_bell.py
#  Bell Icon + Unread Badge + Notification Panel
#  Flet 0.84 compatible — Modern UI
# ================================================================

import flet as ft
from typing import Callable, Optional
from home_module.home_config import T, _pa, _ps, _shadow, _circle


# ========================
# TIME FORMAT HELPER
# ========================
def _time_ago(created_at: str) -> str:
    try:
        from datetime import datetime, timezone
        if not created_at:
            return ""
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        seconds = int((now - dt).total_seconds())
        if seconds < 60:       return "ابھی"
        elif seconds < 3600:   return f"{seconds // 60} منٹ پہلے"
        elif seconds < 86400:  return f"{seconds // 3600} گھنٹے پہلے"
        elif seconds < 604800: return f"{seconds // 86400} دن پہلے"
        else:                  return dt.strftime("%d %b")
    except Exception:
        return ""


# ========================
# NOTIFICATION TYPE CONFIG
# ========================
_NOTIF_CONFIG = {
    "blood_request":        ("🩸", "#C62828", "#FFEBEE"),
    "donor_accepted":       ("✅", "#2E7D32", "#E8F5E9"),
    "donation_confirmed":   ("🎉", "#1565C0", "#E3F2FD"),
    "new_request_admin":    ("🆕", "#E65100", "#FFF3E0"),
    "eligibility_restored": ("💪", "#6A1B9A", "#F3E5F5"),
    "request_expired":      ("⏰", "#546E7A", "#ECEFF1"),
    "general":              ("📢", "#C62828", "#FFEBEE"),
}

def _notif_config(notif_type: str) -> tuple[str, str, str]:
    """Returns (emoji, accent_color, bg_color)"""
    return _NOTIF_CONFIG.get(notif_type, ("🔔", T["primary"], T["primary_lt"]))


# ========================
# SINGLE NOTIFICATION TILE
# ========================
def build_notif_tile(notif: dict, on_tap: Optional[Callable] = None) -> ft.Control:
    notif_id   = notif.get("id")
    title      = notif.get("title") or notif.get("title_urdu") or "Notification"
    message    = notif.get("message") or notif.get("body_urdu") or ""
    is_read    = notif.get("is_read", False)
    created_at = notif.get("created_at", "")
    notif_type = notif.get("type", "general")

    emoji, accent, icon_bg = _notif_config(notif_type)
    time_str = _time_ago(created_at)

    return ft.Container(
        bgcolor="#FFFFFF" if is_read else "#FFF8F8",
        border=ft.Border(left=ft.BorderSide(3, accent if not is_read else "transparent")),
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        on_click=lambda e: on_tap(notif_id) if on_tap else None,
        ink=True,
        content=ft.Row(
            [
                # ── Icon circle ──────────────────────────────
                ft.Container(
                    width=42, height=42,
                    border_radius=21,
                    bgcolor=icon_bg,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(emoji, size=20, text_align=ft.TextAlign.CENTER),
                ),
                ft.Container(width=12),
                # ── Text content ─────────────────────────────
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    title,
                                    size=13,
                                    weight=ft.FontWeight.W_700 if not is_read else ft.FontWeight.W_500,
                                    color="#1A1A1A",
                                    expand=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    no_wrap=True,
                                ),
                                ft.Text(
                                    time_str,
                                    size=10,
                                    color="#9E9E9E",
                                ),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=2),
                        ft.Text(
                            message,
                            size=11,
                            color="#616161",
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=2,
                        ),
                    ],
                    spacing=0,
                    expand=True,
                    tight=True,
                ),
                ft.Container(width=6),
                # ── Unread dot ───────────────────────────────
                ft.Container(
                    width=8, height=8,
                    border_radius=4,
                    bgcolor=accent if not is_read else "transparent",
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
    )


# ========================
# NOTIFICATION PANEL
# ========================
def build_notification_panel(
    notifications: list[dict],
    unread_count: int,
    on_mark_all_read: Callable,
    on_tap_notif: Callable,
    on_close: Callable,
) -> ft.Container:

    # ── Empty state ──────────────────────────────────────────
    if not notifications:
        body = ft.Container(
            height=220,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                [
                    ft.Container(
                        width=72, height=72,
                        border_radius=36,
                        bgcolor="#F5F5F5",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text("🔔", size=34, text_align=ft.TextAlign.CENTER),
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "کوئی نوٹیفکیشن نہیں",
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color="#9E9E9E",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=4),
                    ft.Text(
                        "No notifications yet",
                        size=11,
                        color="#BDBDBD",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
                tight=True,
            ),
        )
        tiles_widget = body
    else:
        items = []
        for i, notif in enumerate(notifications):
            items.append(build_notif_tile(notif, on_tap=on_tap_notif))
            if i < len(notifications) - 1:
                items.append(
                    ft.Container(
                        height=1,
                        bgcolor="#F0F0F0",
                        margin=ft.margin.only(left=68),
                    )
                )
        tiles_widget = ft.Container(
            height=min(380, len(notifications) * 76 + 20),
            content=ft.Column(
                controls=items,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    # ── Header ──────────────────────────────────────────────
        # ── Header ──────────────────────────────────────────────
    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        gradient=ft.LinearGradient(
            begin=ft.alignment.Alignment(-1, -1),
            end=ft.alignment.Alignment(1, 1),
            colors=["#C62828", "#B71C1C"],
        ),
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            "🔔  Notifications",
                            size=15,
                            weight=ft.FontWeight.W_800,
                            color="white",
                        ),
                        ft.Text(
                            f"{unread_count} unread" if unread_count > 0 else "All caught up",
                            size=11,
                            color="#FFCDD2",
                        ),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                # Mark all read pill button
                ft.Container(
                    visible=unread_count > 0,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    border_radius=20,
                    bgcolor="#00000033",
                    on_click=lambda e: on_mark_all_read(),
                    ink=True,
                    content=ft.Text(
                        "Mark all read",
                        size=11,
                        color="white",
                        weight=ft.FontWeight.W_600,
                    ),
                ),
                ft.Container(width=8),
                # ✅ Close button — IconButton (reliable inside AlertDialog)
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color="white",
                    icon_size=16,
                    tooltip="Close",
                    on_click=lambda e: on_close(),
                    style=ft.ButtonStyle(
                        bgcolor="#00000033",
                        shape=ft.RoundedRectangleBorder(radius=15),
                        padding=ft.padding.all(6),
                    ),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
    )
    # ── Footer (if notifications exist) ─────────────────────
    footer_items = []
    if notifications:
        footer_items = [
            ft.Divider(height=1, color="#F0F0F0"),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                content=ft.Text(
                    f"Showing {len(notifications)} notifications",
                    size=11,
                    color="#BDBDBD",
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
            ),
        ]

    return ft.Container(
        width=360,
        bgcolor="#FFFFFF",
        border_radius=20,
        shadow=ft.BoxShadow(
            blur_radius=24,
            spread_radius=0,
            color="#44000000",
            offset=ft.Offset(0, 8),
        ),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            [
                header,
                tiles_widget,
                *footer_items,
            ],
            spacing=0,
            tight=True,
        ),
    )


# ========================
# BELL ICON WITH BADGE
# ========================
class NotificationBell:
    """
    AppBar mein bell icon + red unread badge.
    Usage:
        bell = NotificationBell(page, supabase_client, user_id, safe_update)
        appbar.actions = [bell.build(), ...]
        await bell.refresh()   # periodic ya after load_data
    """

    def __init__(
        self,
        page: ft.Page,
        supabase_client,
        user_id: str,
        safe_update: Callable,
    ):
        self._page        = page
        self._supabase    = supabase_client
        self._user_id     = user_id
        self._safe_update = safe_update
        self._unread      = 0
        self._notifications: list[dict] = []
        self._panel_open  = False
        self._active_dlg: Optional[ft.AlertDialog] = None

        self._badge_ref      = ft.Ref[ft.Container]()
        self._badge_text_ref = ft.Ref[ft.Text]()

    # ── Public refresh ────────────────────────────────────
    async def refresh(self) -> None:
        from services.notifications import fetch_notifications, fetch_unread_count
        try:
            self._unread        = await fetch_unread_count(self._supabase, self._user_id)
            self._notifications = await fetch_notifications(self._supabase, self._user_id)
            self._update_badge()
        except Exception as ex:
            print(f"[BELL] refresh error: {ex}")

    def _update_badge(self) -> None:
        try:
            badge      = self._badge_ref.current
            badge_text = self._badge_text_ref.current
            if badge and badge_text:
                badge.visible    = self._unread > 0
                badge_text.value = str(self._unread) if self._unread < 100 else "99+"
                self._safe_update()
        except Exception as ex:
            print(f"[BELL] badge update error: {ex}")

    # ── Build bell icon ───────────────────────────────────
    def build(self) -> ft.Control:
        badge = ft.Container(
            ref=self._badge_ref,
            visible=False,
            width=17, height=17,
            border_radius=9,
            bgcolor="#FF1744",
            border=ft.Border(
                top=ft.BorderSide(1.5, "white"),
                bottom=ft.BorderSide(1.5, "white"),
                left=ft.BorderSide(1.5, "white"),
                right=ft.BorderSide(1.5, "white"),
            ),
            alignment=ft.Alignment.CENTER,
            content=ft.Text(
                ref=self._badge_text_ref,
                value="0",
                size=8,
                color="white",
                weight=ft.FontWeight.W_900,
                text_align=ft.TextAlign.CENTER,
            ),
        )

        return ft.Stack(
            [
                ft.IconButton(
                    ft.Icons.NOTIFICATIONS_NONE_ROUNDED,
                    icon_color="white",
                    icon_size=24,
                    tooltip="Notifications",
                    on_click=self._on_bell_click,
                ),
                ft.Container(right=5, top=5, content=badge),
            ],
            width=48,
            height=48,
        )

    # ── Click handler (sync → async) ─────────────────────
    def _on_bell_click(self, e) -> None:
        async def _task():
            if self._panel_open:
                self._close_panel()
            else:
                await self._open_panel()
        self._page.run_task(_task)

    # ── Close panel ───────────────────────────────────────
        # ── Close panel ───────────────────────────────────────
    def _close_panel(self) -> None:
        try:
            if self._active_dlg:
                # Use page.close() for Flet 0.23+ (recommended)
                try:
                    self._page.close(self._active_dlg)
                except Exception:
                    # Fallback: manual close for older Flet
                    self._active_dlg.open = False
                    self._page.update()
                
                self._active_dlg = None
            self._panel_open = False
        except Exception as ex:
            print(f"[BELL] close error: {ex}")

    # ── Open panel ────────────────────────────────────────
    async def _open_panel(self) -> None:
        from services.notifications import mark_all_read, mark_notification_read

        await self.refresh()

        def _on_mark_all():
            async def _do():
                await mark_all_read(self._supabase, self._user_id)
                self._close_panel()
                await self.refresh()
            self._page.run_task(_do)

        def _on_tap(notif_id: int):
            async def _do():
                await mark_notification_read(self._supabase, notif_id)
                self._close_panel()
                await self.refresh()
            self._page.run_task(_do)

        panel = build_notification_panel(
            notifications=self._notifications,
            unread_count=self._unread,
            on_mark_all_read=_on_mark_all,
            on_tap_notif=_on_tap,
            on_close=self._close_panel,
        )

        dlg = ft.AlertDialog(
            modal=False,
            bgcolor=ft.Colors.TRANSPARENT,
            shadow_color=ft.Colors.TRANSPARENT,
            content_padding=ft.padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=20),
            content=panel,
        )

        self._active_dlg = dlg
        self._panel_open = True

        if dlg not in self._page.overlay:
            self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()


