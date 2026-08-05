# ════════════════════════════════════════════════════════════════
#  home_dialogs.py  —  Modal dialog layer for Khattak Qomi Etehad.
#
#  FIXED for Flet 0.80+ (including 0.84):
#  - page.show_dialog() / page.pop_dialog() are the correct APIs.
#  - Fully compatible with home_widgets.py
# ════════════════════════════════════════════════════════════════

import threading
import time
from typing import Optional, List, Callable

import flet as ft

from home_module.home_config import (
    T, CARD_COLORS,
    HAS_VIDEO, Video, VideoMedia,
    I_CLOSE, I_PEOPLE, I_HEART, I_BLOOD, I_CAMPAIGN,
    I_PLAY, I_PHONE, I_LOCATION, I_ATTACH, I_PERSON_ADD,
    role_label, is_admin, is_head_admin,
    _p, _pa, _ps, _m, _ms, _border, _shadow, _circle, _divider_line,
    upload_to_bucket, set_app_setting, get_current_uid,
    supabase,
)
from home_module.home_widgets import (
    spinner, empty_state,
    dlg_title_row, close_btn, dlg_text_field,
    build_req_card, build_member_card, build_donor_card, build_leader_card,
)


# ════════════════════════════════════════════════════════════════
#  DIALOG MANAGER — Flet 0.80+ (page.show_dialog / page.pop_dialog)
# ════════════════════════════════════════════════════════════════

class DialogManager:
    """
    Dialog manager for Flet 0.80+.

    Open  → page.show_dialog(dlg)
    Close → page.pop_dialog()
    """

    def __init__(self, page: ft.Page, safe_update: Callable) -> None:
        self._page   = page
        self._update = safe_update
        self.busy    = False
        self._stack: list[ft.AlertDialog] = []

    # ── internal helpers ─────────────────────────────────────
    def _show(self, dlg: ft.AlertDialog) -> None:
        """Call the correct page API for this Flet version."""
        if hasattr(self._page, "show_dialog"):          # Flet 0.80+
            self._page.show_dialog(dlg)
        elif hasattr(self._page, "open"):               # Flet 0.23–0.28
            self._page.open(dlg)
        else:                                           # legacy fallback
            if dlg not in self._page.overlay:
                self._page.overlay.append(dlg)
            dlg.open = True
            self._update()

    def _pop(self, dlg: ft.AlertDialog) -> None:
        """Call the correct page API to close."""
        if hasattr(self._page, "pop_dialog"):           # Flet 0.80+
            self._page.pop_dialog()
        elif hasattr(self._page, "close"):              # Flet 0.23–0.28
            self._page.close(dlg)
        else:                                           # legacy fallback
            dlg.open = False
            if dlg in self._page.overlay:
                self._page.overlay.remove(dlg)
            self._update()

    # ── public API ───────────────────────────────────────────
    def open(self, dlg: ft.AlertDialog) -> None:
        if dlg not in self._stack:
            self._stack.append(dlg)
        try:
            self._show(dlg)
        except Exception as ex:
            print(f"[DM] open failed: {ex}")
            self.busy = False

    def close(self, dlg: ft.AlertDialog) -> None:
        self.busy = False                       # always reset
        if dlg is None:
            return
        if dlg in self._stack:
            self._stack.remove(dlg)
        try:
            self._pop(dlg)
        except Exception as ex:
            print(f"[DM] close failed: {ex}")

    def close_all(self) -> None:
        for dlg in list(self._stack):
            self.close(dlg)
        self._stack.clear()


# ════════════════════════════════════════════════════════════════
#  VIDEO DIALOG
# ════════════════════════════════════════════════════════════════

def show_video_dialog(page: ft.Page, safe_update: Callable, url: str,
                      title: str = "") -> None:
    vw = min(480, int((page.width or 400) * 0.90))
    vh = min(320, int((page.height or 600) * 0.48))

    def _close(e=None):
        try:
            if hasattr(page, "pop_dialog"):
                page.pop_dialog()
            else:
                dlg.open = False
                if dlg in page.overlay:
                    page.overlay.remove(dlg)
                safe_update()
        except Exception as ex:
            print(f"[VIDEO] close error: {ex}")

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor="#000000",
        barrier_color="#CC000000",
        shape=ft.RoundedRectangleBorder(radius=16),
        content_padding=ft.padding.all(0),
        content=ft.Container(
            width=vw,
            padding=ft.padding.only(top=4, bottom=8, left=4, right=4),
            bgcolor="#000000",
            border_radius=16,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                title or "Video",
                                size=13, weight=ft.FontWeight.W_600,
                                color="white", expand=True,
                                overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True,
                            ),
                            ft.IconButton(
                                ft.Icons.CLOSE, icon_color="white",
                                icon_size=20, tooltip="Close", on_click=_close,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        content=ft.Video(
                            playlist=[ft.VideoMedia(url)],
                            playlist_mode=ft.PlaylistMode.NONE,
                            show_controls=True, autoplay=True,
                            expand=False, width=vw, height=vh,
                            fit="contain",
                            filter_quality=ft.FilterQuality.HIGH,
                        ),
                        width=vw, height=vh,
                        bgcolor="#000000", border_radius=12,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                ],
                spacing=4, tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
    )

    try:
        if hasattr(page, "show_dialog"):
            page.show_dialog(dlg)
        else:
            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            safe_update()
    except Exception as ex:
        print(f"[VIDEO] open error: {ex}")


# ════════════════════════════════════════════════════════════════
#  IMAGE PREVIEW DIALOG
# ════════════════════════════════════════════════════════════════

def _open_image_preview(page: ft.Page, safe_update: Callable, url: str) -> None:
    vw = min(560, int((page.width or 500) * 0.88))
    vh = min(400, int((page.height or 700) * 0.60))

    def _close(e=None):
        try:
            if hasattr(page, "pop_dialog"):
                page.pop_dialog()
            else:
                dlg.open = False
                if dlg in page.overlay:
                    page.overlay.remove(dlg)
                safe_update()
        except Exception:
            pass

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor="#000000",
        barrier_color="#CC000000",
        shape=ft.RoundedRectangleBorder(radius=18),
        content_padding=ft.padding.all(0),
        content=ft.Container(
            width=vw,
            padding=ft.padding.only(top=4, bottom=12, left=8, right=8),
            bgcolor="#000000", border_radius=18,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Preview", size=13, weight=ft.FontWeight.W_600,
                                    color="white", expand=True,
                                    overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
                            ft.IconButton(ft.Icons.CLOSE_ROUNDED,
                                          icon_color="white", icon_size=20,
                                          tooltip="Close", on_click=_close),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Image(
                        src=url, width=vw, height=vh,
                        fit="cover",
                        error_content=ft.Text("Image failed to load",
                                              color="white", size=12),
                    ),
                ],
                spacing=4, tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
        actions=[
            ft.TextButton("Close", on_click=_close,
                          style=ft.ButtonStyle(color="#AAAAAA")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    try:
        if hasattr(page, "show_dialog"):
            page.show_dialog(dlg)
        else:
            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            safe_update()
    except Exception as ex:
        print(f"[IMAGE] open error: {ex}")


# ════════════════════════════════════════════════════════════════
#  POST UPDATE POPUP  (Admin only)
# ════════════════════════════════════════════════════════════════

def show_post_update(
    dm: DialogManager,
    page: ft.Page,
    state: dict,
    pick_media_attach,
    pick_media_publish,
    on_reload: Callable,
    snack: Callable,
    safe_update: Callable,
    media_manager=None,
    post_update_state: Optional[dict] = None,
) -> None:
    role = state["profile"].get("role", "member")
    if not is_admin(role):
        snack("⛔ Admins only can post updates", T["primary"])
        return
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]

    tf_title = dlg_text_field("Title | عنوان *")
    tf_body  = dlg_text_field("Content | تفصیل", multiline=True, min_lines=3)

    lbl_status = ft.Text("", size=12)
    progress   = ft.ProgressBar(visible=False, color=T["primary"],
                                 bgcolor=T["primary_md"])

    _attached: list[dict] = []

    status_text = ft.Text(
        "No file selected",
        size=12, color="#9E9E9E", italic=True,
        visible=True,
    )

    attachment_row = ft.Row(
        wrap=True, spacing=8, run_spacing=8,
        controls=[], visible=False,
    )

    if post_update_state is not None:
        post_update_state["file_label"] = status_text

    def _close(ev=None) -> None:
        if dlg_ref[0]:
            dm.close(dlg_ref[0])
        _attached.clear()
        if post_update_state is not None:
            post_update_state["attached_file"] = None

    def _build_chip(item: dict) -> ft.Control:
        is_vid = item["is_vid"]
        name   = item["name"]
        url    = item["url"]
        short  = name if len(name) <= 10 else name[:9] + "…"

        if is_vid:
            thumb = ft.Icon(ft.Icons.VIDEOCAM_ROUNDED, color="#EF5350", size=32)
        else:
            thumb = ft.Image(
                src=url, width=52, height=52,
                fit="cover",
                border_radius=ft.border_radius.all(8),
                error_content=ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED_ROUNDED,
                                      color="#AAAAAA", size=28),
            )

        center_content = ft.Container(
            width=80, height=80, alignment=ft.Alignment(0, 0),
            content=ft.Column([
                thumb,
                ft.Container(height=3),
                ft.Text(short, size=9, color="#444444",
                        text_align=ft.TextAlign.CENTER, no_wrap=True),
            ], spacing=0,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               tight=True),
        )

        remove_btn = ft.Container(
            width=80, height=80,
            alignment=ft.Alignment(0.92, -0.92),
            content=ft.GestureDetector(
                on_tap=lambda e, i=item: _remove_attachment(i),
                content=ft.Container(
                    width=18, height=18, border_radius=9,
                    bgcolor="#EF5350", alignment=ft.Alignment(0, 0),
                    content=ft.Text("×", color="white", size=13,
                                    weight=ft.FontWeight.W_800),
                ),
            ),
        )

        return ft.Container(
            width=80, height=80,
            border_radius=10, bgcolor="#F5F5F5",
            border=ft.border.all(1, "#E0E0E0"),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            tooltip=name,
            content=ft.Stack([center_content, remove_btn]),
            on_click=lambda e, u=url, v=is_vid, n=name: (
                show_video_dialog(page, safe_update, u, n)
                if v else
                _open_image_preview(page, safe_update, u)
            ),
        )

    def _refresh_attachments() -> None:
        attachment_row.controls = [_build_chip(i) for i in _attached]
        has_files = len(_attached) > 0
        status_text.visible    = not has_files
        attachment_row.visible = has_files
        try:
            page.update()
        except Exception as ex:
            print(f"[DIALOG] _refresh_attachments error: {ex}")

    def _remove_attachment(item: dict) -> None:
        if item in _attached:
            _attached.remove(item)
        _refresh_attachments()
        if post_update_state is not None:
            post_update_state["attached_file"] = None
            status_text.value  = "No file selected"
            status_text.color  = "#9E9E9E"
            status_text.italic = True
            try:
                status_text.update()
            except Exception:
                pass

    def _attach_media(e) -> None:
        if media_manager is None:
            snack("Media manager not available", T["primary"])
            return
        pick_media_attach()

    attach_btn = ft.FilledButton(
        "📎 Attach Media",
        style=ft.ButtonStyle(
            bgcolor=T["purple"], color="white",
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
        on_click=_attach_media,
    )

    def _submit(ev) -> None:
        uid = state.get("user_id") or get_current_uid()
        if not uid:
            lbl_status.value = "❌ Not authenticated — please re-login"
            lbl_status.color = T["primary"]
            safe_update()
            return

        title_val = (tf_title.value or "").strip()
        if not title_val:
            lbl_status.value = "❌ Title is required"
            lbl_status.color = T["primary"]
            safe_update()
            return

        has_media = len(_attached) > 0
        progress.visible = True
        lbl_status.value = "🚀 Publishing…"
        lbl_status.color = T["blue"]
        safe_update()

        if has_media:
            def on_media_uploaded(url: str, is_vid: bool) -> None:
                _create_post(title_val, url, is_vid)
            pick_media_publish(on_media_uploaded)
        else:
            _create_post(title_val, None, False)

    def _create_post(title_val: str, media_url: str | None, is_vid: bool) -> None:
        def _post() -> None:
            try:
                media_type = "video" if is_vid else ("image" if media_url else None)
                supabase.table("community_updates").insert({
                    "title":      title_val,
                    "content":    (tf_body.value or "").strip(),
                    "admin_id":   state.get("user_id") or get_current_uid(),
                    "media_url":  media_url,
                    "media_type": media_type,
                }).execute()
                progress.visible = False
                lbl_status.value = "🎉 Published successfully!"
                lbl_status.color = T["green"]
                safe_update()
                time.sleep(1.2)
                _close()
                on_reload()
            except Exception as ex:
                print(f"[DIALOG] _post FAILED: {ex}")
                progress.visible = False
                lbl_status.value = f"❌ {str(ex)[:60]}"
                lbl_status.color = T["primary"]
                safe_update()
        threading.Thread(target=_post, daemon=True).start()

    def on_file_picked(name: str, is_vid: bool) -> None:
        _attached.clear()
        _attached.append({"name": name, "url": "", "is_vid": is_vid})
        status_text.value  = f"📎 {name}"
        status_text.color  = T["primary"]
        status_text.italic = False
        status_text.visible = True
        attachment_row.visible = False
        try:
            page.update()
        except Exception as ex:
            print(f"[DIALOG] on_file_picked update error: {ex}")

    if post_update_state is not None:
        post_update_state["on_file_picked"] = on_file_picked

    dlg = ft.AlertDialog(
        modal=True,
        title=dlg_title_row("📣 Post Update | اپڈیٹ شائع کریں", _close),
        content=ft.Container(
            width=420,
            content=ft.Column(
                [
                    tf_title,
                    tf_body,
                    ft.Divider(color=T["primary_md"], height=16),
                    ft.Row([
                        attach_btn,
                        ft.Container(width=8),
                        status_text,
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(height=4),
                    attachment_row,
                    progress,
                    lbl_status,
                ],
                spacing=12, tight=True, scroll=ft.ScrollMode.AUTO,
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close,
                          style=ft.ButtonStyle(color=T["text_sub"])),
            ft.FilledButton(
                "Publish",
                style=ft.ButtonStyle(bgcolor=T["primary"], color="white"),
                on_click=_submit,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)


# ════════════════════════════════════════════════════════════════
#  MEMBERS POPUP
# ════════════════════════════════════════════════════════════════

def show_members(dm: DialogManager, page: ft.Page, safe_update: Callable) -> None:
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]

    def _close(ev=None):
        if dlg_ref[0]:
            dm.close(dlg_ref[0])

    dlg = ft.AlertDialog(
        modal=True,
        title=dlg_title_row("👥 Members | ممبران", _close),
        content=spinner("Loading members…"),
        actions=[close_btn(_close)],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)

    def _open_detail(m: dict):
        detail_ref: list = [None]

        def _close_detail(ev=None):
            if detail_ref[0]:
                dm.close(detail_ref[0])

        rl, _, _ = role_label(m.get("role", "member"))
        rows = [
            ("👤 Name",        m.get("full_name", "-")),
            ("🩸 Blood Group", m.get("blood_group", "-")),
            ("📍 City",        m.get("city", "-")),
            ("🏷️ Role",        rl),
        ]
        content_rows = [
            ft.Row(
                [
                    ft.Text(label, size=12, color=T["text_sub"], width=100),
                    ft.Text(str(value), size=13, weight=ft.FontWeight.W_600, color=T["text"], expand=True),
                ], spacing=8,
            )
            for label, value in rows
        ]
        detail = ft.AlertDialog(
            modal=True,
            title=dlg_title_row("📋 Member Details | تفصیلات", _close_detail),
            content=ft.Container(width=320, content=ft.Column(content_rows, spacing=10, tight=True)),
            actions=[close_btn(_close_detail)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        detail_ref[0] = detail
        dm.open(detail)

    def _fetch() -> None:
        try:
            data = (
                supabase.table("profiles")
                .select("full_name,role,blood_group,city")
                .order("full_name")
                .limit(60)
                .execute()
                .data or []
            )
            rows = [
                build_member_card(m, on_tap=lambda e, mm=m: _open_detail(mm))
                for m in data
            ]
            ctrl: ft.Control = (
                ft.Column(controls=rows, scroll=ft.ScrollMode.AUTO,
                          height=340, spacing=0)
                if rows else empty_state(I_PEOPLE, "No members found")
            )
        except Exception as ex:
            ctrl = ft.Text(f"Error: {str(ex)[:80]}", color=T["primary"], size=11)

        dlg.content = ft.Container(content=ctrl, width=360)
        safe_update()

    threading.Thread(target=_fetch, daemon=True).start()


# ════════════════════════════════════════════════════════════════
#  DONORS POPUP
# ════════════════════════════════════════════════════════════════

def show_donors(dm: DialogManager, page: ft.Page, safe_update: Callable) -> None:
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]

    def _close(ev=None):
        if dlg_ref[0]:
            dm.close(dlg_ref[0])

    dlg = ft.AlertDialog(
        modal=True,
        title=dlg_title_row("❤️ Donors | ڈونرز", _close),
        content=spinner("Loading donors…"),
        actions=[close_btn(_close)],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)

    def _open_detail(d: dict):
        detail_ref: list = [None]
        phone = d.get("phone_number", "")
        av    = d.get("available", True)

        def _close_detail(ev=None):
            if detail_ref[0]:
                dm.close(detail_ref[0])

        async def _make_call(ev, p=phone):
            try:
                await page.launch_url(f"tel:{p}")
            except Exception as ex:
                print(f"[CALL] launch error: {ex}")

        rows = [
            ("🩸 Blood Group", d.get("blood_group", "-")),
            ("👤 Name",        d.get("full_name", "Donor")),
            ("📍 City",        d.get("city", "-")),
            ("📊 Status",      "✅ Available" if av else "⛔ Busy"),
            ("📞 Phone",       phone or "-"),
        ]
        content_rows = [
            ft.Row(
                [
                    ft.Text(label, size=12, color=T["text_sub"], width=100),
                    ft.Text(str(value), size=13, weight=ft.FontWeight.W_600, color=T["text"], expand=True),
                ], spacing=8,
            )
            for label, value in rows
        ]
        actions = [close_btn(_close_detail)]
        if phone:
            actions.insert(0, ft.FilledButton(
                "📞 Call", bgcolor=T["blue"], color="white",
                on_click=lambda e: page.run_task(_make_call, e),
            ))
        detail = ft.AlertDialog(
            modal=True,
            title=dlg_title_row("📋 Donor Details | تفصیلات", _close_detail),
            content=ft.Container(width=320, content=ft.Column(content_rows, spacing=10, tight=True)),
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        detail_ref[0] = detail
        dm.open(detail)

    def _fetch() -> None:
        try:
            data = (
                supabase.table("donors")
                .select("full_name,blood_group,city,available,phone_number")
                .order("created_at", desc=True)
                .limit(60)
                .execute()
                .data or []
            )
            rows = [
                build_donor_card(d, on_tap=lambda e, dd=d: _open_detail(dd))
                for d in data
            ]
            ctrl: ft.Control = (
                ft.Column(controls=rows, scroll=ft.ScrollMode.AUTO,
                          height=340, spacing=0)
                if rows else empty_state(I_HEART, "No donors found")
            )
        except Exception as ex:
            ctrl = ft.Text(f"Error: {str(ex)[:80]}", color=T["primary"], size=11)

        dlg.content = ft.Container(content=ctrl, width=360)
        safe_update()

    threading.Thread(target=_fetch, daemon=True).start()


# ════════════════════════════════════════════════════════════════
#  BLOOD REQUESTS POPUP
# ════════════════════════════════════════════════════════════════

def show_requests(dm: DialogManager, safe_update: Callable) -> None:
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]

    def _close(ev=None):
        if dlg_ref[0]:
            dm.close(dlg_ref[0])

    dlg = ft.AlertDialog(
        modal=True,
        title=dlg_title_row("🩸 Blood Requests | درخواستیں", _close),
        content=spinner("Loading requests…"),
        actions=[close_btn(_close)],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)

    def _open_detail(r: dict, donation_active: bool = False):
        """Tap-to-detail popup for a single request — shows full info."""
        detail_ref: list = [None]

        def _close_detail(ev=None):
            if detail_ref[0]:
                dm.close(detail_ref[0])

        status = r.get("status", "pending")
        display_status = "Fulfilled" if (donation_active and status != "fulfilled") else status.capitalize()

        rows = [
            ("🩸 Blood Group", r.get("blood_group", "-")),
            ("👤 Patient",     r.get("patient_name", "-")),
            ("📍 City",        r.get("city", "-")),
            ("⚡ Urgency",     r.get("urgency", "normal").capitalize()),
            ("📊 Status",      display_status),
        ]
        content_rows = [
            ft.Row(
                [
                    ft.Text(label, size=12, color=T["text_sub"], width=100),
                    ft.Text(str(value), size=13, weight=ft.FontWeight.W_600, color=T["text"], expand=True),
                ],
                spacing=8,
            )
            for label, value in rows
        ]
        if donation_active and status != "fulfilled":
            content_rows.append(
                ft.Container(
                    bgcolor="#E8F5E9",
                    border_radius=8,
                    padding=ft.padding.all(10),
                    margin=ft.margin.only(top=4),
                    content=ft.Text(
                        "🎉 A donor has already donated for this request; "
                        "the requester just hasn't confirmed it yet.",
                        size=12, color=T["green"],
                    ),
                )
            )

        detail = ft.AlertDialog(
            modal=True,
            title=dlg_title_row("📋 Request Details | تفصیلات", _close_detail),
            content=ft.Container(width=320, content=ft.Column(content_rows, spacing=10, tight=True)),
            actions=[close_btn(_close_detail)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        detail_ref[0] = detail
        dm.open(detail)

    def _fetch() -> None:
        try:
            data = (
                supabase.table("blood_requests")
                .select("id,patient_name,blood_group,city,status,urgency,created_at")
                .order("created_at", desc=True)
                .limit(60)
                .execute()
                .data or []
            )

            active_donation_ids: set = set()
            req_ids = [r.get("id") for r in data if r.get("id") is not None]
            if req_ids:
                try:
                    don_data = (
                        supabase.table("donations")
                        .select("request_id")
                        .in_("request_id", req_ids)
                        .execute()
                        .data or []
                    )
                    active_donation_ids = {d.get("request_id") for d in don_data}
                except Exception as don_ex:
                    print(f"[REQUESTS] donations lookup failed: {don_ex}")

            def _is_active(r: dict) -> bool:
                if r.get("status") in ("fulfilled", "cancelled", "expired"):
                    return False
                return r.get("id") in active_donation_ids

            rows = [
                build_req_card(
                    r,
                    on_tap=lambda e, req=r, da=_is_active(r): _open_detail(req, da),
                    donation_active=_is_active(r),
                )
                for r in data
            ]
            ctrl: ft.Control = (
                ft.Column(controls=rows, scroll=ft.ScrollMode.AUTO,
                          height=340, spacing=0)
                if rows else empty_state(I_BLOOD, "No requests found")
            )
        except Exception as ex:
            ctrl = ft.Text(f"Error: {str(ex)[:80]}", color=T["primary"], size=11)

        dlg.content = ft.Container(content=ctrl, width=360)
        safe_update()

    threading.Thread(target=_fetch, daemon=True).start()


# ════════════════════════════════════════════════════════════════
#  UPDATE DETAIL POPUP
# ════════════════════════════════════════════════════════════════

def show_update_detail(
    item: dict, dm: DialogManager, page: ft.Page, safe_update: Callable,
    role: str = "member", supabase_client=None,
    on_deleted: Optional[Callable] = None):
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]

    def _close(ev=None):
        if dlg_ref[0]:
            dm.close(dlg_ref[0])

    media  = item.get("media_url", "")
    m_type = item.get("media_type", "")
    title  = item.get("title", "Update")
    body   = item.get("content", item.get("body", ""))
    ts     = (item.get("created_at", "") or "")[:10]

    parts: list[ft.Control] = []

    try:
        if media and m_type == "image":
            parts.append(ft.Container(
                border_radius=14, clip_behavior=ft.ClipBehavior.HARD_EDGE,
                shadow=_shadow(8),
                content=ft.Image(src=media, width=380, height=210, fit="cover"),
            ))
        elif media and m_type == "video":
            if HAS_VIDEO:
                parts.append(ft.Container(
                    width=380, height=200, border_radius=14,
                    bgcolor="#000", clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Video(
                        playlist=[ft.VideoMedia(media)],
                        expand=True, autoplay=True,
                        show_controls=True, aspect_ratio=16 / 9,
                    ),
                ))
            parts.append(ft.OutlinedButton(
                "▶  Open Video", icon=I_PLAY,
                on_click=lambda ev, m=media: page.launch_url(m),
            ))
    except Exception:
        pass

    parts += [
        ft.Divider(color=T["primary_md"], height=16),
        ft.Text(body, size=13, color=T["text"]),
    ]
    if ts:
        parts.append(ft.Text(f"🕐  {ts}", size=10, color=T["text_hint"]))

    async def _on_delete(it):
        _close()
        if supabase_client and on_deleted:
            from home_module.home import _delete_post
            await _delete_post(supabase_client, it, on_done=on_deleted)

    dlg = ft.AlertDialog(
        modal=True,
        title=dlg_title_row(title, _close),
        content=ft.Container(
            width=400,
            content=ft.Column(parts, spacing=10, tight=True,
                              scroll=ft.ScrollMode.AUTO),
        ),
        actions=[
            *(
                [ft.TextButton(
                    "🗑️ Delete Post",
                    style=ft.ButtonStyle(color="#E53935"),
                    on_click=lambda e, it=item: page.run_task(_on_delete, it),
                )]
                if is_admin(role) else []
            ),
            ft.TextButton("Close", on_click=_close),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)


# ════════════════════════════════════════════════════════════════
#  ALL UPDATES LIST POPUP
# ════════════════════════════════════════════════════════════════

def show_updates_list(dm: DialogManager, page: ft.Page, safe_update: Callable) -> None:
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]

    def _close(ev=None):
        if dlg_ref[0]:
            dm.close(dlg_ref[0])

    dlg = ft.AlertDialog(
        modal=True,
        title=dlg_title_row("📢 All Updates | تمام خبریں", _close),
        content=spinner("Loading updates…"),
        actions=[close_btn(_close)],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)

    def _fetch() -> None:
        try:
            data = (
                supabase.table("community_updates")
                .select("title,content,created_at,media_url,media_type")
                .order("created_at", desc=True)
                .limit(50)
                .execute()
                .data or []
            )
            rows = []
            for i, itm in enumerate(data):
                clr   = CARD_COLORS[i % len(CARD_COLORS)]
                mt    = itm.get("media_type", "")
                badge = "🖼" if mt == "image" else ("▶" if mt == "video" else "")
                ts    = (itm.get("created_at", "") or "")[:10]
                rows.append(ft.GestureDetector(
                    on_tap=lambda ev, it=itm: (
                        _close(),
                        show_update_detail(it, dm, page, safe_update),
                    ),
                    content=ft.Container(
                        padding=_ps(h=14, v=12), border_radius=14,
                        bgcolor=clr, margin=_m(b=8),
                        shadow=_shadow(6, "#22000000"),
                        content=ft.Column([
                            ft.Row([
                                ft.Text(itm.get("title", "Update"), size=13,
                                        color="white",
                                        weight=ft.FontWeight.W_700, expand=True),
                                ft.Text(badge, size=14),
                            ]),
                            ft.Text(itm.get("content", ""), size=10,
                                    color="#FFFFFFCC", max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"🕐 {ts}", size=9, color="#FFFFFF88") if ts
                            else ft.Container(),
                        ], spacing=4),
                    ),
                ))
            ctrl: ft.Control = (
                ft.Column(controls=rows, scroll=ft.ScrollMode.AUTO,
                          height=380, spacing=0)
                if rows else empty_state(I_CAMPAIGN, "No updates yet")
            )
        except Exception as ex:
            ctrl = ft.Text(f"Error: {str(ex)[:80]}", color=T["primary"], size=11)

        dlg.content = ft.Container(content=ctrl, width=360)
        safe_update()

    threading.Thread(target=_fetch, daemon=True).start()


# ════════════════════════════════════════════════════════════════
#  LEADERSHIP POPUP
# ════════════════════════════════════════════════════════════════

def show_leaders_popup(dm: DialogManager, safe_update: Callable,
                       leaders_data: Optional[Callable[[], List[dict]] | List[dict]] = None) -> None:
    """
    leaders_data: accepts either a list of leader dicts or a callable returning a list.
    """
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]

    def _close(ev=None):
        if dlg_ref[0]:
            dm.close(dlg_ref[0])

    def _open_detail(ldr: dict):
        detail_ref: list = [None]

        def _close_detail(ev=None):
            if detail_ref[0]:
                dm.close(detail_ref[0])

        rows = [
            ("👤 Name (English)", ldr.get("name_en") or ldr.get("name", "-")),
            ("👤 نام (اردو)",       ldr.get("name_ur") or ldr.get("ur", "-")),
            ("🏷️ Title (English)", ldr.get("title_en") or ldr.get("title", "-")),
            ("🏷️ عہدہ (اردو)",     ldr.get("title_ur", "-")),
            ("📍 Area / علاقہ",    ldr.get("area_of_leadership", "-")),
            ("📞 Contact / رابطہ",  ldr.get("phone") or ldr.get("contact", "-")),
        ]
        content_rows = [
            ft.Row(
                [
                    ft.Text(label, size=12, color=T["text_sub"], width=100),
                    ft.Text(str(value), size=13, weight=ft.FontWeight.W_600, color=T["text"], expand=True),
                ], spacing=8,
            )
            for label, value in rows
        ]
        detail = ft.AlertDialog(
            modal=True,
            title=dlg_title_row("📋 Leader Details | تفصیلات", _close_detail),
            content=ft.Container(width=320, content=ft.Column(content_rows, spacing=10, tight=True)),
            actions=[close_btn(_close_detail)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        detail_ref[0] = detail
        dm.open(detail)

    if callable(leaders_data):
        source = leaders_data() or []
    else:
        source = leaders_data or []

    rows = [
        build_leader_card(ldr, on_tap=lambda e, l=ldr: _open_detail(l))
        for ldr in source
    ]

    body: ft.Control = (
        ft.Column(controls=rows, scroll=ft.ScrollMode.AUTO, height=360, spacing=0)
        if rows else
        empty_state(I_PEOPLE, "No leaders added yet | ابھی کوئی رہنما شامل نہیں")
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=dlg_title_row("⭐ Community Leaders | قیادت", _close),
        content=ft.Container(width=360, content=body),
        actions=[close_btn(_close)],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)


# ════════════════════════════════════════════════════════════════
#  LOGOUT CONFIRMATION POPUP
# ════════════════════════════════════════════════════════════════

def show_logout_confirm(
    dm: DialogManager,
    page: ft.Page,
    on_ticker_stop: Callable,
    safe_update: Callable,
) -> None:
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]

    def _close(ev=None):
        if dlg_ref[0]:
            dm.close(dlg_ref[0])

    def _do_logout(ev) -> None:
        _close()
        on_ticker_stop()
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        page.go("/login")

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Logout | لاگ آؤٹ",
                      weight=ft.FontWeight.BOLD, color=T["primary_dk"]),
        content=ft.Text(
            "Are you sure you want to logout? کیا آپ لاگ آؤٹ کرنا چاہتے ہیں؟",
            size=13,
        ),
        actions=[
            ft.TextButton(
                "Cancel", on_click=_close,
                style=ft.ButtonStyle(color=T["text_sub"]),
            ),
            ft.FilledButton(
                "Logout",
                style=ft.ButtonStyle(bgcolor=T["primary"], color="white"),
                on_click=_do_logout,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)


# ════════════════════════════════════════════════════════════════
#  ADD DONOR POPUP
# ════════════════════════════════════════════════════════════════

def show_add_donor(
    dm: DialogManager,
    state: dict,
    on_reload: Callable,
    snack: Callable,
    safe_update: Callable,
) -> None:
    if dm.busy:
        return
    dm.busy = True

    dlg_ref: list = [None]
    tf_name  = dlg_text_field("Full Name | نام *")
    tf_city  = dlg_text_field("City | شہر *")
    tf_phone = dlg_text_field("Phone | فون *")

    tf_blood = ft.Dropdown(
        label="Blood Group | بلڈ گروپ *",
        options=[
            ft.dropdown.Option("A+"),
            ft.dropdown.Option("A-"),
            ft.dropdown.Option("B+"),
            ft.dropdown.Option("B-"),
            ft.dropdown.Option("O+"),
            ft.dropdown.Option("O-"),
            ft.dropdown.Option("AB+"),
            ft.dropdown.Option("AB-"),
        ],
        border_color=T["primary_md"],
    )

    lbl_status = ft.Text("", size=12)
    progress   = ft.ProgressBar(visible=False, color=T["primary"],
                                 bgcolor=T["primary_md"])

    def _close(ev=None) -> None:
        if dlg_ref[0]:
            dm.close(dlg_ref[0])

    def _submit(ev) -> None:
        name  = (tf_name.value or "").strip()
        blood = (tf_blood.value or "").strip().upper()
        if not name or not blood:
            lbl_status.value = "❌ Name and blood group are required"
            lbl_status.color = T["primary"]
            safe_update()
            return
        uid = state.get("user_id") or get_current_uid()
        progress.visible = True
        lbl_status.value = "Saving…"
        lbl_status.color = T["blue"]
        safe_update()

        def _save() -> None:
            try:
                supabase.table("donors").insert({
                    "full_name":    name,
                    "blood_group":  blood,
                    "city":         (tf_city.value or "").strip(),
                    "phone_number": (tf_phone.value or "").strip(),
                    "available":    True,
                    "added_by":     uid,
                }).execute()
                progress.visible = False
                lbl_status.value = "✅ Donor added!"
                lbl_status.color = T["green"]
                safe_update()
                time.sleep(1.0)
                _close()
                on_reload()
            except Exception as ex:
                progress.visible = False
                lbl_status.value = f"❌ {str(ex)[:60]}"
                lbl_status.color = T["primary"]
                safe_update()

        threading.Thread(target=_save, daemon=True).start()

    dlg = ft.AlertDialog(
        modal=True,
        title=dlg_title_row("➕ Add Donor | ڈونر شامل کریں", _close),
        content=ft.Container(
            width=400,
            content=ft.Column(
                [tf_name, tf_blood, tf_city, tf_phone, progress, lbl_status],
                spacing=12, tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close,
                          style=ft.ButtonStyle(color=T["text_sub"])),
            ft.FilledButton(
                "Add Donor",
                style=ft.ButtonStyle(bgcolor=T["primary"], color="white"),
                on_click=_submit,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    dm.open(dlg)

