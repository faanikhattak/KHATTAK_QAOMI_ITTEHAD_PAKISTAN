# ════════════════════════════════════════════════════════════════
#  home_widgets.py  —  Khattak Qomi Etehad Pakistan
#  Flet 0.84 — fully compatible rewrite
#  All ft.Colors.X → hex strings
#  All `str | None` → Optional[str]
#  All list[X] → List[X]
#  ft.AlertDialog close → dlg.open = False + page.update() ONLY
#  ft.Image always has src= arg
#  ft.FilePicker singleton via page.data (overlay pattern, 0.84)
# ════════════════════════════════════════════════════════════════

import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Callable

import flet as ft

from home_module.home_config import (
    T, CARD_COLORS,
    HAS_VIDEO, Video, VideoMedia,
    I_CLOSE, I_PEOPLE, I_HEART, I_BLOOD, I_CAMPAIGN, I_STAR,
    I_APPS, I_ADMIN, I_CHEVRON, I_WALL, I_EDIT, I_GROUP,
    I_ERROR, I_INBOX, I_PLAY, I_PHONE, I_LOCATION, I_NEWS,
    I_DONOR, I_PERSON2, I_CHECK, I_PERSON_ADD, I_LEADER,
    I_ATTACH,
    role_label, is_admin, is_head_admin,
    _p, _pa, _ps, _m, _ms, _border, _shadow, _circle, _divider_line,
)


# ════════════════════════════════════════════════════════════════
#  DIALOG CLOSE HELPER  —  Flet 0.84 correct pattern
#  Just set .open = False and call page.update().
#  NEVER remove from page.overlay — causes errors in 0.84.
# ════════════════════════════════════════════════════════════════

def _close_dialog(dlg: ft.AlertDialog, page: ft.Page) -> None:
    try:
        dlg.open = False
        page.update()
    except Exception as ex:
        print(f"[DLG] close error: {ex}")


def _close_dialog_async(dlg: ft.AlertDialog, page: ft.Page) -> None:
    """Close dialog from sync context via run_task."""
    async def _coro():
        _close_dialog(dlg, page)
    try:
        page.run_task(_coro)
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════
#  URL LAUNCH HELPER
# ════════════════════════════════════════════════════════════════

def _safe_launch_url(page: ft.Page, title: str, media_url: Optional[str]) -> None:
    async def _launch():
        try:
            url = f"whatsapp://send?text={title}%0A{media_url}" if media_url else title
            await page.launch_url(url)
        except Exception as ex:
            print(f"[LAUNCH] error: {ex}")
    try:
        page.run_task(_launch)
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ════════════════════════════════════════════════════════════════

def spinner(label: str = "Loading…") -> ft.Container:
    return ft.Container(
        width=360, height=200,
        content=ft.Column(
            [
                ft.ProgressRing(color=T["primary"], width=42, height=42, stroke_width=3),
                ft.Text(label, size=12, color=T["text_sub"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=14,
        ),
    )


def empty_state(icon, msg: str) -> ft.Column:
    return ft.Column(
        [
            ft.Icon(icon, color=T["primary_md"], size=52),
            ft.Text(msg, color=T["text_hint"], size=13,
                    text_align=ft.TextAlign.CENTER),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
        height=160,
    )


def section_header(icon, en: str, ur: str,
                   color: Optional[str] = None, see_all=None) -> ft.Container:
    color = color or T["primary_dk"]
    row: List[ft.Control] = [
        _circle(30, T["primary_lt"], ft.Icon(icon, color=color, size=15)),
        ft.Container(width=8),
        ft.Text(en, size=15, weight=ft.FontWeight.W_700, color=T["primary_dk"]),
        ft.Text(f"| {ur}", size=11, color="#E57373"),
        ft.Container(expand=True),
    ]
    if see_all:
        row.append(ft.TextButton(
            "See All →",
            style=ft.ButtonStyle(color=T["primary"]),
            on_click=see_all,
        ))
    return ft.Container(
        padding=_p(l=16, t=16, r=10, b=8),
        content=ft.Row(row, spacing=4),
    )


def dlg_title_row(text: str, close_fn) -> ft.Row:
    return ft.Row([
        ft.Text(text, weight=ft.FontWeight.W_700, color=T["primary_dk"],
                size=15, expand=True),
        ft.IconButton(I_CLOSE, icon_color=T["text_sub"],
                      icon_size=18, on_click=lambda e: close_fn()),
    ])


def close_btn(close_fn) -> ft.FilledButton:
    return ft.FilledButton(
        "Close", icon=I_CLOSE,
        style=ft.ButtonStyle(
            bgcolor=T["primary"], color="white",
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
        on_click=lambda e: close_fn(),
    )


def dlg_text_field(label: str, multiline: bool = False,
                   min_lines: int = 1) -> ft.TextField:
    return ft.TextField(
        label=label,
        multiline=multiline,
        min_lines=min_lines,
        border_radius=12,
        bgcolor=T["bg"],
        border_color=T["primary_md"],
        focused_border_color=T["primary"],
        label_style=ft.TextStyle(color=T["text_sub"]),
    )


# ════════════════════════════════════════════════════════════════
#  TIME AGO HELPER
# ════════════════════════════════════════════════════════════════

def _time_ago(created_at: str) -> str:
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            return f"{int(diff.seconds / 60)}m ago"
        elif diff < timedelta(days=1):
            return f"{int(diff.seconds / 3600)}h ago"
        elif diff < timedelta(days=7):
            return f"{diff.days}d ago"
        elif diff < timedelta(days=30):
            return f"{int(diff.days / 7)}w ago"
        else:
            return f"{int(diff.days / 30)}mo ago"
    except Exception:
        return created_at[:10] if created_at else ""


# ════════════════════════════════════════════════════════════════
#  DELETE POST DIALOG (REAL SUCCESS FLOW)
# ════════════════════════════════════════════════════════════════

def _delete_post_dialog(
    page: ft.Page,
    post_id: str,
    supabase_client,
    on_deleted: Callable,
    safe_update,
) -> None:
    """Confirm + delete post from community_updates table."""

    dlg_ref: List[Optional[ft.AlertDialog]] = [None]

    def _close():
        if dlg_ref[0]:
            _close_dialog_async(dlg_ref[0], page)

    async def _confirm_delete(e):
        import asyncio  
        p_id = e.control.data if e and e.control.data else None
        
        if not p_id:
            print("[DELETE POST] Error: post_id نہیں مل سکی!")
            return

        try:
            if p_id is not None:
                p_id = int(p_id) if isinstance(p_id, str) or isinstance(p_id, int) else p_id

            try:
                supabase_client.table("post_likes").delete().eq("post_id", p_id).execute()
            except Exception as like_ex:
                print(f"[DB] Error deleting likes: {like_ex}")

            try:
                supabase_client.table("post_comments").delete().eq("post_id", p_id).execute()
            except Exception as comment_ex:
                print(f"[DB] Error deleting comments: {comment_ex}")

            response = supabase_client.table("community_updates").delete().eq("id", p_id).execute()
            
            if response and hasattr(response, 'data') and response.data:
                print("[SUCCESS] پوسٹ واقعی ڈیٹا بیس سے ڈیلیٹ ہو گئی!")
                
                if dlg_ref[0]:
                    dlg_ref[0].icon = ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=48, color="#4CAF50")
                    dlg_ref[0].title = ft.Text("Deleted Successfully!", weight=ft.FontWeight.BOLD, color=T["text"])
                    dlg_ref[0].content = ft.Column([
                        ft.Text("The post has been permanently removed from database.", size=13, color=T["text_sub"]),
                    ], tight=True, spacing=4)
                    dlg_ref[0].actions = []
                    page.update()
                
                await asyncio.sleep(2)
            else:
                print("[DELETE POST] ڈیٹا بیس سے ڈیلیٹ نہیں ہو سکی یا پوسٹ نہیں ملی!")

        except Exception as ex:
            print(f"[DELETE POST] Main Error: {ex}")
        finally:
            _close()
            try:
                page.update()
            except Exception:
                pass
            if on_deleted:
                on_deleted()

    dlg = ft.AlertDialog(
        modal=True,
        icon=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=48, color="#EF5350"),
        title=ft.Text("Delete Post?", weight=ft.FontWeight.BOLD, color=T["text"]),
        content=ft.Column([
            ft.Text("This will permanently remove the post and all its likes and comments.",
                    size=13, color=T["text_sub"]),
        ], tight=True, spacing=4),
        actions=[
            ft.TextButton(
                "Cancel",
                on_click=lambda e: _close(),
                style=ft.ButtonStyle(color=T["text_sub"]),
            ),
            ft.FilledButton(
                "Delete",
                data=post_id,  
                on_click=lambda e: page.run_task(_confirm_delete, e),  
                style=ft.ButtonStyle(
                    bgcolor="#E53935",
                    color="white",
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=T.get("surface", "#FFFFFF"),
        shape=ft.RoundedRectangleBorder(radius=16),
    )
    dlg_ref[0] = dlg

    if dlg not in page.overlay:
        page.overlay.append(dlg)
    dlg.open = True
    try:
        page.update()
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════
#  LIKE TOGGLE
# ════════════════════════════════════════════════════════════════

def _toggle_like(
    page: ft.Page,
    post_id: str,
    user_id: str,
    like_btn: ft.IconButton,
    likes_text: ft.Text,
    supabase_client,
) -> None:
    async def _do_like():
        try:
            existing = (
                supabase_client.table("post_likes")
                .select("id")
                .eq("post_id", post_id)
                .eq("user_id", user_id)
                .execute()
            )
            is_liked = len(existing.data or []) > 0

            if is_liked:
                supabase_client.table("post_likes").delete().eq("post_id", post_id).eq("user_id", user_id).execute()
                like_btn.icon = ft.Icons.FAVORITE_BORDER
                like_btn.icon_color = T["text"]
            else:
                supabase_client.table("post_likes").insert({"post_id": post_id, "user_id": user_id}).execute()
                like_btn.icon = ft.Icons.FAVORITE
                like_btn.icon_color = "#E91E63"

            count_res = supabase_client.table("post_likes").select("id", count="exact").eq("post_id", post_id).execute()
            count = count_res.count or 0
            likes_text.value = f"{count} likes"
            page.update()
        except Exception as ex:
            print(f"[LIKE] error: {ex}")

    page.run_task(_do_like)


# ════════════════════════════════════════════════════════════════
#  COMMENTS DIALOG
# ════════════════════════════════════════════════════════════════

def _show_comments_dialog(
    page: ft.Page,
    post_id: str,
    supabase_client,
    safe_update,
) -> None:

    dlg_ref: List[Optional[ft.AlertDialog]] = [None]

    def _close():
        if dlg_ref[0]:
            _close_dialog(dlg_ref[0], page)

    async def _open():
        try:
            comments_raw = (
                supabase_client.table("post_comments")
                .select("*")
                .eq("post_id", post_id)
                .order("created_at", desc=False)
                .execute().data or []
            )

            commenter_ids = list({c.get("user_id") for c in comments_raw if c.get("user_id")})
            profiles_by_id = {}
            if commenter_ids:
                try:
                    prof_res = (
                        supabase_client.table("profiles")
                        .select("id, full_name, avatar_url")
                        .in_("id", commenter_ids)
                        .execute()
                    )
                    for p in (prof_res.data or []):
                        profiles_by_id[p.get("id")] = p
                except Exception as ex:
                    print(f"[COMMENTS] profile lookup error: {ex}")

            comments = []
            for c in comments_raw:
                c["profile"] = profiles_by_id.get(c.get("user_id"), {})
                comments.append(c)

            comment_controls: List[ft.Control] = []
            
            for c in comments:
                profile = c.get("profile") or {}
                name = profile.get("full_name") or profile.get("email") or "User"
                avatar = profile.get("avatar_url", "")
                
                comment_text = c.get("comment_text", "")
                ts = _time_ago(c.get("created_at", ""))

                comment_controls.append(ft.Container(
                    padding=ft.padding.all(10),
                    border_radius=12,
                    bgcolor=T["bg"],
                    content=ft.Row([
                        ft.CircleAvatar(
                            foreground_image_src=avatar if avatar else None,
                            content=ft.Text(name[0].upper() if name else "?"),
                            radius=16,
                        ),
                        ft.Container(width=10),
                        ft.Column([
                            ft.Row([
                                ft.Text(name, size=12, weight=ft.FontWeight.BOLD, color=T["text"]),
                                ft.Container(width=6),
                                ft.Text(ts, size=10, color=T["text_hint"]),
                            ], spacing=0),
                            ft.Text(comment_text, size=12, color=T["text"]),
                        ], spacing=2, expand=True),
                    ], vertical_alignment=ft.CrossAxisAlignment.START),
                ))

            comment_field = ft.TextField(
                hint_text="Write a comment…",
                expand=True,
                border_radius=20,
                filled=True,
                bgcolor=T["bg"],
                border_color=T["primary_md"],
                focused_border_color=T["primary"],
                content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )

            def _add_comment(e):
                text = comment_field.value.strip() if comment_field.value else ""
                if not text:
                    return

                async def _post():
                    try:
                        user_res = supabase_client.auth.get_user()
                        uid = user_res.user.id if user_res and user_res.user else None
                        
                        if not uid:
                            return

                        supabase_client.table("post_comments").insert({
                            "post_id": post_id,
                            "user_id": uid,
                            "comment_text": text,
                        }).execute()
                        
                        comment_field.value = ""
                        
                        if dlg_ref[0]:
                            dlg_ref[0].open = False
                        
                        if safe_update:
                            safe_update()
                        else:
                            page.update()
                        
                    except Exception as ex:
                        print(f"[COMMENT] error: {ex}")
                        if dlg_ref[0]:
                            dlg_ref[0].open = False
                            page.update()

                page.run_task(_post)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Text("Comments", weight=ft.FontWeight.BOLD, size=16, color=T["primary_dk"], expand=True),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_color=T["text_sub"],
                        icon_size=18,
                        on_click=lambda e: _close(),
                    ),
                ]),
                content=ft.Container(
                    width=400,
                    height=480,
                    content=ft.Column(
                        [
                            ft.Column(
                                comment_controls if comment_controls else [
                                    ft.Container(
                                        padding=ft.padding.all(32),
                                        content=ft.Column([
                                            ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, color=T["text_hint"], size=40),
                                            ft.Text("No comments yet", size=13, color=T["text_hint"],
                                                    text_align=ft.TextAlign.CENTER),
                                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                                    )
                                ],
                                scroll=ft.ScrollMode.AUTO,
                                expand=True,
                                spacing=6,
                            ),
                            ft.Divider(color=T["primary_md"], height=1),
                            ft.Container(height=6),
                            ft.Row([
                                comment_field,
                                ft.Container(width=6),
                                ft.IconButton(
                                    ft.Icons.SEND_ROUNDED,
                                    icon_color=T["primary"],
                                    icon_size=24,
                                    on_click=lambda e: _add_comment(e),
                                ),
                            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ],
                        spacing=6,
                        expand=True,
                    ),
                ),
                bgcolor=T.get("surface", "#FFFFFF"),
                shape=ft.RoundedRectangleBorder(radius=20),
                content_padding=ft.padding.all(16),
            )
            dlg_ref[0] = dlg

            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            page.update()

        except Exception as ex:
            print(f"[COMMENTS] open error: {ex}")

    page.run_task(_open)


# ════════════════════════════════════════════════════════════════
#  LEADERS (UPDATED WITH "See All →")
# ════════════════════════════════════════════════════════════════

def build_leaders(on_see_all, leaders_data: Optional[List[dict]] = None,
                   page: Optional[ft.Page] = None) -> ft.Container:
    source = leaders_data or []
    display_leaders = [
        l for l in source if (l.get("level") or "central") == "central"
    ]

    if not display_leaders:
        return ft.Container(
            padding=_pa(22),
            content=empty_state(I_GROUP, "No leaders added yet | ابھی کوئی رہنما شامل نہیں"),
        )

    def _show_leader_detail(ldr: dict):
        if not page:
            return

        name    = ldr.get("name_ur") or ldr.get("ur") or ldr.get("name", "?")
        title   = ldr.get("title_ur") or ldr.get("title", "")
        color   = ldr.get("color", T["primary"])
        img_url = ldr.get("image_url", "")
        phone   = ldr.get("phone") or ldr.get("contact") or ""
        bio     = ldr.get("bio") or ldr.get("about") or ""

        ps  = name.split()
        ini = (ps[0][0] + (ps[-1][0] if len(ps) > 1 else "")).upper()

        avatar_big: ft.Control = (
            ft.Image(src=img_url, fit=ft.BoxFit.COVER, width=84, height=84,
                     error_content=ft.Text(ini, size=26, color="white",
                                            weight=ft.FontWeight.BOLD,
                                            text_align=ft.TextAlign.CENTER))
            if img_url else
            ft.Text(ini, size=26, color="white", weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER)
        )

        info_rows: List[ft.Control] = [
            ft.Container(
                alignment=ft.Alignment(0, 0),
                content=ft.Container(
                    width=90, height=90, border_radius=45,
                    border=_border(2, f"{color}55"), padding=3,
                    content=_circle(84, color, avatar_big),
                ),
            ),
            ft.Container(height=10),
            ft.Text(name, size=17, weight=ft.FontWeight.BOLD, color=T["text"],
                     text_align=ft.TextAlign.CENTER),
            ft.Container(
                margin=_m(t=6), padding=_ps(h=10, v=4),
                border_radius=10, bgcolor=f"{color}14",
                border=_border(1, f"{color}33"),
                content=ft.Text(title, size=12, color=color,
                                 weight=ft.FontWeight.W_600,
                                 text_align=ft.TextAlign.CENTER),
            ),
        ]

        if phone:
            info_rows.append(ft.Container(height=12))
            info_rows.append(ft.Row(
                [
                    ft.Icon(ft.Icons.PHONE_ROUNDED, size=14, color=T["text_sub"]),
                    ft.Text(phone, size=12, color=T["text_sub"]),
                ],
                spacing=6, alignment=ft.MainAxisAlignment.CENTER,
            ))

        if bio:
            info_rows.append(ft.Container(height=10))
            info_rows.append(ft.Text(bio, size=12, color=T["text_sub"],
                                       text_align=ft.TextAlign.CENTER))

        def _close(e=None):
            try:
                dlg.open = False
                page.update()
            except Exception:
                pass

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=T["surface"],
            content=ft.Container(
                width=280,
                content=ft.Column(
                    info_rows, tight=True, spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
            actions=[ft.TextButton("Close | بند کریں", on_click=_close)],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()


    def _card(ldr: dict) -> ft.GestureDetector:
        name    = ldr.get("name_ur") or ldr.get("ur") or ldr.get("name", "?")
        title   = ldr.get("title_ur") or ldr.get("title", "")
        color   = ldr.get("color", T["primary"])
        img_url = ldr.get("image_url", "")

        ps  = name.split()
        ini = (ps[0][0] + (ps[-1][0] if len(ps) > 1 else "")).upper()

        avatar: ft.Control = (
            ft.Image(src=img_url, fit="cover", width=54, height=54,
                     error_content=ft.Text(ini, size=18, color="white",
                                           weight=ft.FontWeight.BOLD,
                                           text_align=ft.TextAlign.CENTER))
            if img_url else
            ft.Text(ini, size=18, color="white",
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER)
        )

        return ft.GestureDetector(
            on_tap=lambda e, l=ldr: _show_leader_detail(l),
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Container(
                width=110, 
                height=170,  # 👈 تمام کارڈز کو ایک یکساں (Equal) ہائٹ دی گئی ہے
                border_radius=20,
                bgcolor=T["surface"],
                shadow=_shadow(8, "#1A000000"),
                padding=_pa(10),
                content=ft.Column([
                    ft.Container(
                        width=56, height=56, border_radius=28,
                        border=_border(2, f"{color}55"),
                        padding=2,
                        content=_circle(50, color, avatar),
                    ),
                    ft.Container(height=4),
                    # نام کا سائز اور لائنز کو برابر جگہ دینے کے لیے Height
                    ft.Container(
                        height=28,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(name, size=9, weight=ft.FontWeight.W_700,
                                        color=T["text"], text_align=ft.TextAlign.CENTER, 
                                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ),
                    ft.Container(expand=True),  # 👈 یہ بیج کو بالکل نیچے الائن رکھے گا
                    # ٹائٹل بیج
                    ft.Container(
                        padding=_ps(h=6, v=3),
                        border_radius=8, bgcolor=f"{color}14",
                        border=_border(1, f"{color}33"),
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(title, size=7, color=color,
                                        weight=ft.FontWeight.W_600,
                                        text_align=ft.TextAlign.CENTER,
                                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            ),
        )
    if not display_leaders:
        return ft.Container()

    cards = [
        ft.Container(margin=_m(l=16 if i == 0 else 0, r=8), content=_card(ldr))
        for i, ldr in enumerate(display_leaders)
    ]

    # UPDATED: Added "See All →" TextButton explicitly
    leaders_header = ft.Container(
        padding=_p(l=16, t=16, r=10, b=8),
        content=ft.Row(
            [
                ft.Container(
                    width=38, height=38, border_radius=12,
                    bgcolor=f"{T['primary']}14",
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(I_STAR, color=T["primary"], size=18),
                ),
                ft.Container(width=8),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Central Leadership", size=15, weight=ft.FontWeight.W_700, color=T["primary_dk"]),
                                ft.Text("| مرکزی قیادت", size=11, color="#E57373"),
                            ], spacing=4,
                        ),
                        ft.Text(f"{len(display_leaders)} leaders | {len(display_leaders)} رہنما",
                                size=10, color=T["text_hint"]),
                    ],
                    spacing=1, tight=True,
                ),
                ft.Container(expand=True),
                ft.TextButton(
                    "See All →",
                    style=ft.ButtonStyle(color=T["primary"]),
                    on_click=on_see_all,
                ),
            ],
            spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    return ft.Container(content=ft.Column([
        leaders_header,
        ft.Row(controls=cards, scroll=ft.ScrollMode.AUTO, spacing=0),
    ]))


# ════════════════════════════════════════════════════════════════
#  QUICK CTA — Request blood / Become a donor
# ════════════════════════════════════════════════════════════════

def build_quick_cta(callbacks: dict) -> ft.Container:
    def _btn(icon, label_en, label_ur, color, tap) -> ft.Container:
        return ft.Container(
            expand=True,
            content=ft.GestureDetector(
                on_tap=tap,
                mouse_cursor=ft.MouseCursor.CLICK,
                content=ft.Container(
                    height=86,
                    border_radius=18,
                    bgcolor=color,
                    shadow=_shadow(14, "#50000000"),
                    padding=_pa(14),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column(
                        [
                            ft.Icon(icon, color="white", size=24),
                            ft.Container(height=8),
                            ft.Text(
                                label_en,
                                size=12,
                                weight=ft.FontWeight.W_700,
                                color="white",
                                no_wrap=True,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                label_ur,
                                size=10,
                                color="#FFFFFFCC",
                                no_wrap=True,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=0,
                        tight=True,
                    ),
                ),
            ),
        )

    return ft.Container(
        margin=_ms(h=14, v=4),
        content=ft.Row(
            controls=[
                _btn(I_BLOOD, "Request Blood", "خون مانگیں", T["primary"], callbacks.get("request")),
                _btn(I_DONOR, "Donate Blood", "ڈونر بنیں", T["teal"], callbacks.get("donor")),
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )


# ════════════════════════════════════════════════════════════════
#  QUICK ACTIONS GRID (WITH LEADERS VIEW BUTTON)
# ════════════════════════════════════════════════════════════════

def build_actions(role: str, callbacks: dict) -> ft.Container:
    actions: List[tuple] = [
        (I_INBOX,   "My Requests",    "درخواستیں",    T["blue"],       callbacks.get("requests_popup")),
        (I_PERSON2, "Profile",        "پروفائل",      T["primary"],    callbacks.get("profile")),
        (I_LEADER,  "Leaders View",   "رہنما کا ویو", T["teal"],       callbacks.get("leaders_view")),
        (I_STAR,    "Leaderboard",    "لیڈر بورڈ",    T["orange"],     callbacks.get("leaderboard")),
        (I_HEART,   "Feedback",       "تاثرات",       T["green"],      callbacks.get("feedback")),
        (I_NEWS,    "Updates",        "خبریں",        T["purple"],     callbacks.get("updates")),
        (ft.Icons.SUPPORT_AGENT_ROUNDED, "Contact Support", "رابطہ کریں", "#00897B", callbacks.get("support")),
        (ft.Icons.MY_LOCATION_ROUNDED, "Update Location", "لوکیشن اپڈیٹ کریں", T["blue"], callbacks.get("update_location")),
    ]
    if is_admin(role):
        actions.append(
            (I_ADMIN, "Admin Panel", "ایڈمن پینل", T["blue"], callbacks.get("admin"))
        )

    def _grid_btn(icon, en, ur, color, tap) -> ft.GestureDetector:
        return ft.GestureDetector(
            on_tap=tap,
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Container(
                expand=True, height=84, border_radius=18,
                bgcolor=T["surface"],
                border=_border(1, "#0D000000"),
                shadow=_shadow(8, "#14000000"),
                padding=_pa(10),
                content=ft.Column([
                    ft.Container(
                        width=40, height=40, border_radius=14,
                        bgcolor=f"{color}14",
                        border=_border(1, f"{color}33"),
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon, color=color, size=19),
                    ),
                    ft.Container(height=6),
                    ft.Text(en, size=10, weight=ft.FontWeight.W_700,
                            color=T["text"], text_align=ft.TextAlign.CENTER,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(ur, size=8, color=T["text_hint"],
                            text_align=ft.TextAlign.CENTER,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0),
            ),
        )

    grid_rows: List[ft.Control] = []
    for i in range(0, len(actions), 4):
        chunk = actions[i:i+4]
        row_items = [_grid_btn(*a) for a in chunk]
        while len(row_items) < 4:
            row_items.append(ft.Container(expand=True))
        grid_rows.append(
            ft.Row(row_items, spacing=8, expand=True)
        )

    return ft.Container(
        margin=_ms(h=14, v=4),
        content=ft.Column([
            section_header(I_APPS, "Quick Actions", "فوری اقدامات"),
            ft.Column(controls=grid_rows, spacing=8),
        ]),
    )


# ════════════════════════════════════════════════════════════════
#  INLINE VIDEO PLAYER
# ════════════════════════════════════════════════════════════════

def _build_video_player(page: ft.Page, media_url: str, card_height: int = 300) -> ft.Control:
    if not HAS_VIDEO or Video is None or VideoMedia is None:
        return ft.Container(
            height=card_height,
            bgcolor="#000000",
            alignment=ft.Alignment(0, 0),
            content=ft.Icon(ft.Icons.VIDEOCAM, color="white", size=40),
        )

    width = page.width or 400
    import uuid
    instance_id = uuid.uuid4().hex[:8]

    placeholder = ft.Container(
        width=width,
        height=card_height,
        bgcolor="#111111",
        alignment=ft.Alignment(0, 0),
        content=ft.Icon(ft.Icons.VIDEOCAM, color="white", size=40),
    )

    player = Video(
        key=f"vid_player_{instance_id}",
        title=f"post_video_{instance_id}",
        playlist=[VideoMedia(resource=media_url)],
        width=width,
        height=card_height,
        fit=ft.BoxFit.COVER,
        autoplay=False,
        visible=False,
    )

    state = {"started": False}

    def _start(e=None):
        if state["started"]:
            return
        state["started"] = True

        placeholder.visible = False
        overlay_box.visible = False
        player.visible = True
        try:
            page.update()
        except Exception as ex:
            print(f"[VIDEO] page.update() error: {ex}")

        async def _force_play():
            try:
                await player.play()
            except Exception as ex:
                print(f"[VIDEO] player.play() error: {ex}")
        try:
            page.run_task(_force_play)
        except Exception as ex:
            print(f"[VIDEO] run_task error: {ex}")

    play_icon = ft.Container(
        width=64, height=64, border_radius=32,
        bgcolor="#99000000",
        alignment=ft.Alignment(0, 0),
        content=ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, color="white", size=36),
    )

    overlay_box = ft.Container(
        width=width, height=card_height,
        alignment=ft.Alignment(0, 0),
        content=play_icon,
        on_click=_start,
    )

    stack = ft.Stack(
        [player, placeholder, overlay_box],
        width=width,
        height=card_height,
        key=f"vid_stack_{instance_id}",
    )

    return ft.Container(
        key=f"vid_card_{instance_id}",
        height=card_height,
        bgcolor="#000000",
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=stack,
    )


# ════════════════════════════════════════════════════════════════
#  INSTAGRAM-STYLE POST CARD
# ════════════════════════════════════════════════════════════════

def build_instagram_post(
    page: ft.Page,
    item: dict,
    user_id: str,
    supabase_client,
    safe_update,
    on_media_tap=None,
    on_deleted=None,
    user_role: str = "member",
) -> ft.Control:

    post_id    = item.get("id", "")
    title      = item.get("title", "")
    body       = item.get("content", "") or item.get("body", "")
    media_url  = item.get("media_url", "") or ""
    media_type = item.get("media_type", "") or ""
    created_at = item.get("created_at", "")
    admin_id   = item.get("admin_id", "")

    admin_name   = "Admin"
    admin_avatar = ""
    try:
        res = (
            supabase_client.table("profiles")
            .select("full_name, avatar_url")
            .eq("id", admin_id)
            .limit(1)
            .execute()
        )
        p = res.data[0] if res.data else {}
        if not res.data:
            print(f"[FEED] admin_name lookup returned no rows for admin_id={admin_id} — check profiles table RLS policy")
        admin_name   = p.get("full_name") or "Admin"
        admin_avatar = p.get("avatar_url", "")
    except Exception as ex:
        print(f"[FEED] admin_name fetch error for admin_id={admin_id}: {ex}")

    time_ago_str = _time_ago(created_at)

    is_liked       = False
    likes_count    = 0
    comments_count = 0
    try:
        lr = supabase_client.table("post_likes").select("id", count="exact").eq("post_id", post_id).execute()
        likes_count = lr.count or 0
        ul = supabase_client.table("post_likes").select("id").eq("post_id", post_id).eq("user_id", user_id).execute()
        is_liked = len(ul.data or []) > 0
        cr = supabase_client.table("post_comments").select("id", count="exact").eq("post_id", post_id).execute()
        comments_count = cr.count or 0
    except Exception:
        pass

    is_vid = (
        media_type.startswith("video")
        or any(media_url.lower().endswith(x) for x in (".mp4", ".mov", ".avi", ".mkv", ".webm"))
    )

    if media_url and is_vid:
        media_widget = _build_video_player(page, media_url, card_height=300)
    elif media_url:
        media_widget = ft.Container(
            height=300,
            bgcolor=T.get("surface_2", T["bg"]),
            alignment=ft.Alignment(0, 0),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Image(
                src=media_url,
                fit=ft.BoxFit.CONTAIN,
                width=page.width or 400,
                height=300,
                error_content=ft.Container(
                    bgcolor=T["primary_lt"],
                    content=ft.Icon(ft.Icons.BROKEN_IMAGE_OUTLINED, color=T["primary"], size=40),
                    alignment=ft.Alignment(0, 0),
                ),
            ),
            on_click=lambda e: on_media_tap(item) if on_media_tap else None,
        )
    else:
        media_widget = ft.Container()

    likes_text = ft.Text(
        f"{likes_count} likes",
        size=13,
        weight=ft.FontWeight.W_700,
        color=T["text"],
    )

    like_btn = ft.IconButton(
        icon=ft.Icons.FAVORITE if is_liked else ft.Icons.FAVORITE_BORDER,
        icon_color="#E91E63" if is_liked else T["text"],
        icon_size=26,
        tooltip="Like",
        on_click=lambda e: _toggle_like(page, post_id, user_id, like_btn, likes_text, supabase_client),
    )

    comment_btn = ft.IconButton(
        icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
        icon_color=T["text"],
        icon_size=24,
        tooltip="Comment",
        on_click=lambda e: _show_comments_dialog(page, post_id, supabase_client, safe_update),
    )

    share_btn = ft.IconButton(
        icon=ft.Icons.SEND_OUTLINED,
        icon_color=T["text"],
        icon_size=24,
        tooltip="Share via WhatsApp",
        on_click=lambda e: _safe_launch_url(page, title, media_url or None),
    )

    delete_btn = ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        icon_color="#E53935",
        icon_size=20,
        tooltip="Delete Post",
        on_click=lambda e: _delete_post_dialog(page, post_id, supabase_client, on_deleted, safe_update),
    ) if is_admin(user_role) else ft.Container(width=0)

    return ft.Container(
        margin=ft.margin.only(bottom=12),
        bgcolor=T["surface"],
        border_radius=16,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=10,
            color="#50000000",
            offset=ft.Offset(0, 2),
        ),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Column(
            [
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    content=ft.Row([
                        ft.CircleAvatar(
                            foreground_image_src=admin_avatar if admin_avatar else None,
                            content=ft.Text(admin_name[0].upper() if admin_name else "A"),
                            radius=20,
                        ),
                        ft.Container(width=10),
                        ft.Column([
                            ft.Text(admin_name, size=14, weight=ft.FontWeight.W_700, color=T["text"]),
                            ft.Text(time_ago_str, size=11, color=T["text_hint"]),
                        ], spacing=1, expand=True),
                        delete_btn,
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=4),
                    visible=bool(title or body),
                    content=ft.Column([
                        ft.Text(title, size=14, weight=ft.FontWeight.W_700, color=T["text"],
                                visible=bool(title)),
                        ft.Text(body, size=13, color=T["text_sub"],
                                visible=bool(body)),
                    ], spacing=2, tight=True),
                ),
                media_widget,
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    content=ft.Row([
                        ft.Row([
                            like_btn,
                            ft.Text(str(likes_count), size=13, color=T["text_sub"],
                                    weight=ft.FontWeight.W_500),
                        ], spacing=2),
                        ft.Container(width=8),
                        ft.Row([
                            comment_btn,
                            ft.Text(str(comments_count), size=13, color=T["text_sub"],
                                    weight=ft.FontWeight.W_500),
                        ], spacing=2),
                        ft.Container(width=8),
                        share_btn,
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.BOOKMARK_BORDER,
                            icon_color=T["text_hint"],
                            icon_size=22,
                        ),
                    ], spacing=0),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=2),
                    content=likes_text,
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    on_click=lambda e: _show_comments_dialog(page, post_id, supabase_client, safe_update),
                    content=ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text("Y", size=11),
                            radius=14,
                            bgcolor=T["primary_lt"],
                        ),
                        ft.Container(width=8),
                        ft.Text(
                            f"View all {comments_count} comments…" if comments_count else "Add a comment…",
                            size=12, color=T["text_hint"],
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ),
            ],
            spacing=0,
            tight=True,
        ),
    )


# ════════════════════════════════════════════════════════════════
#  INSTAGRAM-STYLE FEED
# ════════════════════════════════════════════════════════════════

def build_instagram_feed(
    page: ft.Page,
    news_items: list,
    user_id: str,
    supabase_client,
    safe_update,
    on_media_tap=None,
    on_deleted=None,
    user_role: str = "member",
) -> ft.Control:

    if not news_items:
        return ft.Container(
            padding=ft.padding.all(40),
            content=ft.Column([
                ft.Icon(ft.Icons.PHOTO_ALBUM_OUTLINED, size=64, color=T["text_hint"]),
                ft.Container(height=12),
                ft.Text("No updates yet", size=16, color=T["text_hint"],
                        weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER),
                ft.Text("Be the first to post!", size=12, color=T["text_hint"],
                        text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        )

    posts: List[ft.Control] = []
    for item in news_items:
        try:
            posts.append(build_instagram_post(
                page=page,
                item=item,
                user_id=user_id,
                supabase_client=supabase_client,
                safe_update=safe_update,
                on_media_tap=on_media_tap,
                on_deleted=on_deleted,
                user_role=user_role,
            ))
        except Exception as ex:
            print(f"[FEED] post build error: {ex}")

    return ft.Column(controls=posts, spacing=8, tight=True)


# ════════════════════════════════════════════════════════════════
#  POST UPDATE DIALOG
# ════════════════════════════════════════════════════════════════

def build_post_dialog(
    page: ft.Page,
    dm,
    on_submit,
    pick_media_attach=None,
    pick_media_publish=None,
    post_update_state: Optional[dict] = None,
) -> ft.AlertDialog:

    tf_title = dlg_text_field("Title | عنوان")
    tf_body  = dlg_text_field("Content | متن", multiline=True, min_lines=4)

    lbl_file = ft.Text("No file selected", size=12, color=T["text_hint"], italic=True)
    if post_update_state is not None:
        post_update_state["file_label"] = lbl_file

    preview_img = ft.Image(
        src="",
        visible=False,
        width=340, height=180,
        fit="cover",
        border_radius=10,
    )
    preview_vid = ft.Container(
        visible=False, height=52, border_radius=10,
        bgcolor=T.get("primary_lt", "#FFEBEE"),
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        content=ft.Row([
            ft.Icon(ft.Icons.VIDEOCAM_ROUNDED, color=T["primary"], size=22),
            ft.Container(width=8),
            ft.Text("Video attached", size=13, color=T["primary"], weight=ft.FontWeight.W_600),
        ], spacing=0),
    )

    progress   = ft.ProgressBar(visible=False, color=T["primary"], height=5)
    lbl_status = ft.Text("", size=12, color=T["text_sub"])

    dlg_ref:    List[Optional[ft.AlertDialog]] = [None]
    _busy:      List[bool] = [False]

    def _close():
        dlg = dlg_ref[0]
        if dlg is not None:
            try:
                dlg.open = False
                if hasattr(page, "close"):
                    page.close(dlg)
                page.update()
            except Exception as ex:
                print(f"[POST DLG] close error: {ex}")

    def _reset_state():
        if post_update_state is not None:
            post_update_state["dialog"] = None
            post_update_state["attached_file"] = None
            post_update_state["file_label"] = None
            if post_update_state.get("title_field"):
                post_update_state["title_field"].value = ""
            if post_update_state.get("content_field"):
                post_update_state["content_field"].value = ""

    def _on_attach(e=None):
        if pick_media_attach:
            pick_media_attach()

    async def _on_publish(e=None):
        if _busy[0]:
            return
        
        title = (tf_title.value or "").strip()
        body  = (tf_body.value  or "").strip()
        attached = (post_update_state or {}).get("attached_file")

        if not title:
            lbl_status.value = "⚠️ Title is required."
            try: page.update()
            except Exception: pass
            return

        _busy[0] = True
        _close() 

        async def _start_upload_and_publish():
            try:
                if attached and pick_media_publish:
                    print("[BACKGROUND] Starting media upload...")
                    
                    def _on_upload_done(url, is_vid):
                        async def _save():
                            try:
                                print("[BACKGROUND] Upload done. Submitting post...")
                                await on_submit(title, body, url, is_vid)
                                _reset_state()
                            except Exception as ex:
                                print(f"[BACKGROUND] Submit error: {ex}")
                                _reset_state()
                        try: page.run_task(_save)
                        except Exception: pass

                    pick_media_publish(on_publish_complete=_on_upload_done)
                    
                else:
                    print("[BACKGROUND] No media. Submitting text post...")
                    await on_submit(title, body, None, False)
                    _reset_state()
                    
            except Exception as ex:
                print(f"[BACKGROUND] Process error: {ex}")
                _reset_state()

        try:
            page.run_task(_start_upload_and_publish)
        except Exception:
            pass

    attach_btn = ft.OutlinedButton(
        "📎  Attach Photo ",
        style=ft.ButtonStyle(
            color=T["primary"],
            side=ft.BorderSide(1.5, T["primary"]),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
        on_click=_on_attach,
    )

    publish_btn = ft.FilledButton(
        "Publish",
        icon=ft.Icons.SEND_ROUNDED,
        style=ft.ButtonStyle(
            bgcolor=T["primary"], color="white",
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        on_click=lambda e: page.run_task(_on_publish),
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Container(
                width=34, height=34, border_radius=17,
                bgcolor=T["primary_lt"],
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.CAMPAIGN_ROUNDED, color=T["primary"], size=18),
            ),
            ft.Container(width=10),
            ft.Column([
                ft.Text("Post Update", size=15, weight=ft.FontWeight.W_800, color=T["primary_dk"]),
                ft.Text("اپڈیٹ شائع کریں", size=11, color="#E57373"),
            ], spacing=1, expand=True),
            ft.IconButton(
                ft.Icons.CLOSE_ROUNDED,
                icon_color=T["text_hint"], icon_size=20,
                on_click=lambda e: _close(),
            ),
        ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        content=ft.Container(
            width=440,
            padding=ft.padding.symmetric(vertical=4),
            content=ft.Column(
                [
                    tf_title,
                    ft.Container(height=2),
                    tf_body,
                    ft.Divider(color=T["primary_md"], height=18),
                    attach_btn,
                    ft.Container(height=4),
                    lbl_file,
                    preview_img,
                    preview_vid,
                    ft.Container(height=4),
                    progress,
                    lbl_status,
                ],
                spacing=8, tight=True, scroll=ft.ScrollMode.AUTO,
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _close(),
                          style=ft.ButtonStyle(color=T["text_sub"])),
            publish_btn,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=T.get("surface", "#FFFFFF"),
        shape=ft.RoundedRectangleBorder(radius=20),
    )
    dlg_ref[0] = dlg
    return dlg


# ════════════════════════════════════════════════════════════════
#  HERO WIDGET
# ════════════════════════════════════════════════════════════════

def build_hero(
    *,
    page: ft.Page,
    profile: dict,
    bg_url: Optional[str],
    logo_url: Optional[str],
    on_tap_bg,
    on_tap_logo,
    on_nav_profile,
) -> ft.Container:

    name   = profile.get("full_name", "ممبر")
    role   = profile.get("role", "member")
    av_url = profile.get("avatar_url")
    blood  = profile.get("blood_group", "")

    rl, rc, _ = role_label(role)

    bg_display: ft.Control = (
        ft.Image(src=bg_url, fit="cover", width=float("inf"), height=220)
        if bg_url
        else ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
                colors=["#3C1414", "#1F1030", "#17171A"],
            ),
        )
    )

    admin_row_controls: List[ft.Control] = []
    if is_admin(role):
        admin_row_controls = [
            ft.Container(
                width=34, height=34, border_radius=17,
                bgcolor="#CC000000",
                tooltip="Change Background",
                alignment=ft.Alignment(0, 0),
                on_click=lambda e: on_tap_bg(e),
                content=ft.Icon(ft.Icons.WALLPAPER_ROUNDED, color="white", size=18),
            ),
        ]

    if av_url:
        avatar_ctrl: ft.Control = ft.CircleAvatar(
            radius=15, foreground_image_src=av_url, bgcolor=T["primary_lt"],
        )
    else:
        initial = (name[:1] if name else "؟").upper()
        avatar_ctrl = ft.CircleAvatar(
            radius=15, bgcolor=T["primary_lt"],
            content=ft.Text(initial, color=T["primary"], weight=ft.FontWeight.BOLD, size=13),
        )

    profile_chip_items: List[ft.Control] = [
        avatar_ctrl,
        ft.Container(width=6),
        ft.Text(name, size=11, weight=ft.FontWeight.W_700, color="white",
                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=58),
    ]
    if blood:
        profile_chip_items += [
            ft.Container(width=6),
            ft.Container(
                padding=_ps(h=7, v=2), border_radius=10, bgcolor=T["primary"],
                content=ft.Text(blood, size=10, weight=ft.FontWeight.BOLD, color="white"),
            ),
        ]

    profile_chip_items += [
        ft.Container(width=6),
        ft.Container(
            padding=_ps(h=7, v=2), border_radius=10, bgcolor=rc,
            content=ft.Text(rl, size=10, weight=ft.FontWeight.W_700, color="white"),
        ),
    ]

    return ft.Container(
        height=226,
        border_radius=ft.border_radius.only(bottom_left=28, bottom_right=28),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        shadow=_shadow(16, "#33000000"),
        content=ft.Stack([
            ft.Container(expand=True, height=226,
                         clip_behavior=ft.ClipBehavior.HARD_EDGE,
                         content=bg_display),
            ft.Container(
                expand=True, height=226,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(0, -1), end=ft.Alignment(0, 1),
                    colors=["#33000000", "#66000000", "#99000000"],
                ),
            ),
            ft.Container(
                expand=True, height=226,
                padding=ft.padding.only(left=14, right=14, top=18, bottom=12),
                content=ft.Column([
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Column([
                            ft.Text(
                                "KHATTAK QAOMI ITTEHAD PAKISTAN",
                                size=18, weight=ft.FontWeight.W_800,
                                color="white", no_wrap=True,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "خٹک قومی اتحاد پاکستان",
                                size=16, color="white", no_wrap=True,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "اتحاد ہماری طاقت، خدمت ہمارا عزم",
                                size=10, color="#FFCDD2",
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=0),
                    ),
                    ft.Row([
                        ft.Container(expand=True),
                        ft.Row(
                            controls=admin_row_controls,
                            spacing=0,
                            tight=True,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=0),
            ),
        ]),
    )


# ════════════════════════════════════════════════════════════════
#  NEWS TICKER
# ════════════════════════════════════════════════════════════════

class NewsTicker:
    _STEP          = 1.5
    _DELAY         = 0.03
    _START         = 420
    _END           = -2400
    _DEFAULT_COLOR = "white"
    _SEP_COLOR     = "#FFCDD2"

    def __init__(self, items: Optional[List[str]] = None) -> None:
        self._running = False
        if items:
            self._segments: List[tuple] = [(t, self._DEFAULT_COLOR) for t in items]
        else:
            self._segments = [
                ("Loading updates…  |  اپڈیٹس لوڈ ہو رہی ہیں…", self._DEFAULT_COLOR)
            ]
        self._offset_ref = ft.Ref()
        self.widget = self._build_bar()

    def _build_bar(self) -> ft.Container:
        return ft.Container(
            height=34,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0),
                colors=[T["primary_dk"], T["primary"]],
            ),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Row([
                ft.Container(
                    margin=_m(l=8), padding=_ps(h=10, v=4),
                    border_radius=20, bgcolor="#26FFFFFF",
                    content=ft.Text("Today Stories", size=10, color="white",
                                    weight=ft.FontWeight.W_800, no_wrap=True),
                ),
                ft.Container(width=10),
                ft.Container(
                    expand=True, height=34,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ref=self._offset_ref,
                    content=self._make_row(self._START),
                ),
            ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _segment_controls(self) -> List[ft.Control]:
        controls: List[ft.Control] = []
        for i, (text, color) in enumerate(self._segments):
            if i > 0:
                controls.append(
                    ft.Text("     •     ", size=12, color=self._SEP_COLOR, no_wrap=True)
                )
            controls.append(
                ft.Text(text, size=12, color=color or self._DEFAULT_COLOR,
                         weight=ft.FontWeight.W_500, no_wrap=True)
            )
        return controls

    def _make_row(self, left_offset: float) -> ft.Row:
        return ft.Row([
            ft.Container(
                margin=_m(l=int(left_offset)),
                content=ft.Row(self._segment_controls(), spacing=0, tight=True),
            )
        ], scroll=ft.ScrollMode.HIDDEN)

    def start(self) -> None:
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._running = False

    def update_text(self, news_list: List[dict]) -> None:
        if not news_list:
            return
        segments = []
        for n in news_list[:8]:
            text = f"  {n.get('icon','📢')}  {n.get('title','')} — {n.get('content','')}"
            color = n.get("color") or self._DEFAULT_COLOR
            segments.append((text, color))
        self._segments = segments

    def _run(self) -> None:
        pos = float(self._START)
        while self._running:
            try:
                pos -= self._STEP
                if pos < self._END:
                    pos = float(self._START)
                ref = self._offset_ref.current
                if ref is not None:
                    ref.content = self._make_row(pos)
                    try:
                        ref.update()
                    except Exception:
                        pass
            except Exception as ex:
                print(f"[TICKER] {ex}")
            time.sleep(self._DELAY)


# ════════════════════════════════════════════════════════════════
#  STATS ROW
# ════════════════════════════════════════════════════════════════

def build_stats(stats: dict, on_members, on_donors, on_requests) -> ft.Container:
    def _box(icon, val, en, ur, color, tap) -> ft.GestureDetector:
        return ft.GestureDetector(
            on_tap=tap,
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Container(
                expand=True, height=102, border_radius=20,
                bgcolor=T["surface"],
                shadow=_shadow(10, "#50000000"),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Column([
                    ft.Container(height=3, bgcolor=color),
                    ft.Container(
                        expand=True,
                        padding=_pa(10),
                        content=ft.Column([
                            ft.Container(
                                width=38, height=38, border_radius=12,
                                bgcolor=f"{color}14",
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(icon, color=color, size=18),
                            ),
                            ft.Text(str(val), size=22, weight=ft.FontWeight.W_800, color=color),
                            ft.Text(f"{en}\n{ur}", size=7, color=T["text_hint"],
                                    text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=3),
                    ),
                ], spacing=0),
            ),
        )

    fulfilled = stats.get("fulfilled", 0)
    donations = stats.get("donations", 0)
    lives = donations or fulfilled

    lives_banner = ft.Container(
        margin=_ms(h=14, v=4),
        padding=_ps(h=16, v=12),
        border_radius=18,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
            colors=[T["primary"], "#534AB7"],
        ),
        shadow=_shadow(16, "#60000000"),
        content=ft.Row([
            ft.Container(
                width=44, height=44, border_radius=14,
                bgcolor="#26FFFFFF",
                alignment=ft.Alignment(0, 0),
                content=ft.Text("❤️", size=22),
            ),
            ft.Container(width=12),
            ft.Column([
                ft.Text(
                    f"{lives} Lives Saved | {lives} زندگیاں بچائی گئیں",
                    size=13, weight=ft.FontWeight.W_700, color="white",
                ),
                ft.Text(
                    "Together we make a difference | مل کر فرق ڈالیں",
                    size=10, color="#F0997B",
                ),
            ], spacing=2, expand=True, tight=True),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
    ) if lives > 0 else ft.Container()

    return ft.Container(
        content=ft.Column([
            ft.Container(
                padding=_ps(h=14, v=8),
                content=ft.Row([
                    _box(I_PEOPLE, stats["members"],  "Members",  "ممبران",    T["blue"],   on_members),
                    ft.Container(width=8),
                    _box(I_HEART,  stats["donors"],   "Donors",   "ڈونرز",     T["teal"],   on_donors),
                    ft.Container(width=8),
                    _box(I_BLOOD,  stats["requests"], "Requests", "درخواستیں", T["primary"], on_requests),
                ]),
            ),
            lives_banner,
        ], spacing=0),
    )


# ════════════════════════════════════════════════════════════════
#  DONOR DIRECTORY ROW
# ════════════════════════════════════════════════════════════════

def build_donor_row(donors: List[dict], on_see_all) -> ft.Container:
    def _card(d: dict) -> ft.GestureDetector:
        name  = d.get("full_name", d.get("name", "Donor"))
        blood = d.get("blood_group", "?")
        city  = d.get("city", "")
        av    = d.get("available", True)
        return ft.GestureDetector(
            on_tap=on_see_all,
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Container(
                width=98, border_radius=20,
                bgcolor=T["surface"], shadow=_shadow(8, "#1A000000"),
                padding=_pa(10),
                content=ft.Column([
                    ft.Stack([
                        ft.Container(
                            width=56, height=56, border_radius=28,
                            border=_border(2, f"{T['green'] if av else T['text_hint']}55"),
                            padding=2,
                            content=_circle(50, T["primary_lt"],
                                    ft.Text(blood, size=13, color=T["primary"],
                                            weight=ft.FontWeight.BOLD,
                                            text_align=ft.TextAlign.CENTER)),
                        ),
                        ft.Container(
                            width=56, height=56,
                            alignment=ft.Alignment(1, -1),
                            content=ft.Container(
                                width=14, height=14, border_radius=7,
                                bgcolor=T["green"] if av else T["text_hint"],
                                border=_border(2, "white"),
                            ),
                        ),
                    ]),
                    ft.Container(height=4),
                    ft.Text(name, size=9, color=T["text"], weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.CENTER,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(city, size=8, color=T["text_sub"],
                            text_align=ft.TextAlign.CENTER, max_lines=1),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            ),
        )

    cards = [
        ft.Container(margin=_m(l=16 if i == 0 else 0, r=8), content=_card(d))
        for i, d in enumerate(donors)
    ]
    return ft.Container(content=ft.Column([
        section_header(I_DONOR, "Donors", "ڈونرز", see_all=on_see_all),
        ft.Row(controls=cards, scroll=ft.ScrollMode.AUTO, spacing=0),
    ]))


# ════════════════════════════════════════════════════════════════
#  BLOOD REQUEST CARD
# ════════════════════════════════════════════════════════════════

def build_req_card(r: dict, on_tap=None, donation_active: bool = False) -> ft.GestureDetector:
    STATUS_STYLES = {
        "pending":     ("#FFF3E0", "#B26A00", "⏳ Pending"),
        "matching":    ("#E3F2FD", "#1565C0", "🔍 Matching"),
        "in_progress": ("#EDE7F6", "#5E35B1", "✅ Donor Found"),
        "fulfilled":   ("#E8F5E9", "#2E7D32", "🎉 Done"),
        "cancelled":   ("#F0F0F0", "#757575", "❌ Cancelled"),
    }
    URGENCY_STYLES = {
        "urgent":   ("#E24B4A", "🚨"),
        "high":     ("#EF9F27", "🔴"),
        "normal":   (T["primary"], "📌"),
        "low":      ("#1D9E75", "🟢"),
    }
    st  = r.get("status", "pending")
    urg = r.get("urgency", "normal")
    if donation_active and st != "fulfilled":
        bg, fg, lbl = ("#E8F5E9", "#2E7D32", "🎉 Donated — Confirm")
    else:
        bg, fg, lbl = STATUS_STYLES.get(st, ("#F0F0F0", "#757575", st.capitalize()))
    accent, urg_icon = URGENCY_STYLES.get(urg, (T["primary"], "📌"))
    posted = _time_ago(r.get("created_at", "")) if r.get("created_at") else ""

    return ft.GestureDetector(
        on_tap=on_tap,
        mouse_cursor=ft.MouseCursor.CLICK,
        content=ft.Container(
            margin=_ms(h=14, v=5),
            border_radius=20,
            bgcolor=T["surface"],
            shadow=_shadow(10, "#50000000"),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Row(
                [
                    ft.Container(width=4, bgcolor=accent),
                    ft.Container(
                        padding=_ps(h=14, v=13),
                        expand=True,
                        content=ft.Row(
                            [
                                ft.Container(
                                    width=52, height=52, border_radius=26,
                                    bgcolor=T["primary_lt"],
                                    border=_border(2, accent + "55"),
                                    alignment=ft.Alignment(0, 0),
                                    content=ft.Text(
                                        r.get("blood_group", "?"), size=14,
                                        color=T["primary"], weight=ft.FontWeight.BOLD,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                ),
                                ft.Container(width=12),
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"{urg_icon} {r.get('patient_name', '---')}",
                                            size=14, weight=ft.FontWeight.W_700,
                                            color=T["text"], max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Row(
                                            [
                                                ft.Icon(I_LOCATION, size=12, color=T["text_sub"]),
                                                ft.Text(r.get("city", "--"), size=11, color=T["text_sub"]),
                                            ] + (
                                                [
                                                    ft.Container(width=6),
                                                    ft.Container(width=3, height=3, border_radius=2, bgcolor=T["text_hint"]),
                                                    ft.Container(width=6),
                                                    ft.Text(posted, size=11, color=T["text_sub"]),
                                                ] if posted else []
                                            ),
                                            spacing=2,
                                        ),
                                    ],
                                    spacing=4, expand=True, tight=True,
                                ),
                                ft.Column(
                                    [
                                        ft.Container(
                                            padding=_ps(h=10, v=5), border_radius=12, bgcolor=bg,
                                            content=ft.Text(lbl, size=9, color=fg, weight=ft.FontWeight.BOLD),
                                        ),
                                        ft.Container(height=6),
                                        ft.Icon(I_CHEVRON, size=14, color=T["text_hint"]),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                    spacing=0,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                ],
                spacing=0,
            ),
        ),
    )


def build_member_card(m: dict, on_tap=None) -> ft.GestureDetector:
    rl, rc, _ = role_label(m.get("role", "member"))
    ini = (m.get("full_name") or "?")[0].upper()
    return ft.GestureDetector(
        on_tap=on_tap,
        mouse_cursor=ft.MouseCursor.CLICK,
        content=ft.Container(
            margin=_ms(h=14, v=5), border_radius=18,
            bgcolor=T["surface"], shadow=_shadow(8, "#1A000000"),
            padding=_ps(h=14, v=12),
            content=ft.Row(
                [
                    _circle(46, T["primary_lt"],
                            ft.Text(ini, size=16, color=T["primary"],
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER)),
                    ft.Container(width=12),
                    ft.Column(
                        [
                            ft.Text(m.get("full_name", "---"), size=13,
                                    weight=ft.FontWeight.W_700, color=T["text"],
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                [
                                    ft.Text(m.get("blood_group", "--"), size=10, color=T["primary"]),
                                    ft.Text(" • ", size=10, color=T["text_hint"]),
                                    ft.Icon(I_LOCATION, size=10, color=T["text_sub"]),
                                    ft.Text(m.get("city", "--"), size=10, color=T["text_sub"]),
                                ], spacing=2,
                            ),
                        ], spacing=4, expand=True, tight=True,
                    ),
                    ft.Column(
                        [
                            ft.Container(
                                padding=_ps(h=9, v=4), border_radius=10,
                                bgcolor=f"{rc}1A",
                                content=ft.Text(rl, size=9, color=rc, weight=ft.FontWeight.BOLD),
                            ),
                            ft.Container(height=6),
                            ft.Icon(I_CHEVRON, size=14, color=T["text_hint"]),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.END, spacing=0,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
    )


def build_donor_card(d: dict, on_tap=None) -> ft.GestureDetector:
    av = d.get("available", True)
    bg = d.get("blood_group", "?")
    return ft.GestureDetector(
        on_tap=on_tap,
        mouse_cursor=ft.MouseCursor.CLICK,
        content=ft.Container(
            margin=_ms(h=14, v=5), border_radius=18,
            bgcolor=T["surface"], shadow=_shadow(8, "#1A000000"),
            padding=_ps(h=14, v=12),
            content=ft.Row(
                [
                    ft.Container(width=4, bgcolor=T["green"] if av else T["text_hint"]),
                    ft.Container(width=10),
                    _circle(46, T["primary_lt"],
                            ft.Text(bg, size=14, color=T["primary"],
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER)),
                    ft.Container(width=12),
                    ft.Column(
                        [
                            ft.Text(d.get("full_name", "Donor"), size=13,
                                    weight=ft.FontWeight.W_700, color=T["text"],
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                [
                                    ft.Icon(I_LOCATION, size=11, color=T["text_sub"]),
                                    ft.Text(d.get("city", "--"), size=11, color=T["text_sub"]),
                                ], spacing=2,
                            ),
                        ], spacing=4, expand=True, tight=True,
                    ),
                    ft.Column(
                        [
                            ft.Container(
                                padding=_ps(h=9, v=4), border_radius=10,
                                bgcolor="#E8F5E9" if av else T["surface_2"],
                                content=ft.Text(
                                    "✅ Available" if av else "⛔ Busy", size=9,
                                    color=T["green"] if av else T["text_hint"],
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                            ft.Container(height=6),
                            ft.Icon(I_CHEVRON, size=14, color=T["text_hint"]),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.END, spacing=0,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
    )


def build_leader_card(ldr: dict, on_tap=None) -> ft.GestureDetector:
    ps  = ldr["name"].split()
    ini = (ps[0][0] + (ps[-1][0] if len(ps) > 1 else "")).upper()
    return ft.GestureDetector(
        on_tap=on_tap,
        mouse_cursor=ft.MouseCursor.CLICK,
        content=ft.Container(
            margin=_ms(h=14, v=5), border_radius=18,
            bgcolor=T["surface"], shadow=_shadow(8, "#1A000000"),
            padding=_ps(h=14, v=12),
            content=ft.Row(
                [
                    _circle(48, ldr["color"],
                            ft.Text(ini, size=16, color="white",
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER)),
                    ft.Container(width=12),
                    ft.Column(
                        [
                            ft.Text(ldr["ur"], size=14, weight=ft.FontWeight.W_700, color=T["text"]),
                            ft.Text(ldr["title"], size=10, color=T["text_sub"]),
                            ft.Text(ldr["title_ur"], size=10, color=T["primary"]),
                        ], spacing=2, expand=True, tight=True,
                    ),
                    ft.Icon(I_CHEVRON, size=14, color=T["text_hint"]),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
    )


# ════════════════════════════════════════════════════════════════
#  SIDEBAR (WITH LEADERS VIEW BUTTON)
# ════════════════════════════════════════════════════════════════

def build_sidebar(profile: dict, stats: dict, callbacks: dict) -> ft.Container:
    name   = profile.get("full_name", "ممبر")
    role   = profile.get("role", "member")
    blood  = profile.get("blood_group", "--")
    av_url = profile.get("avatar_url")
    rl, rc, _ = role_label(role)

    role_chip = ft.Container(
        content=ft.Text(rl, size=10, weight=ft.FontWeight.W_700, color="white"),
        bgcolor=rc,
        padding=ft.padding.symmetric(horizontal=10, vertical=3),
        border_radius=10,
    )

    avatar = ft.Container(
        width=76, height=76, border_radius=38,
        border=_border(3, f"{T['primary']}55"),
        padding=3,
        content=ft.CircleAvatar(
            radius=33,
            foreground_image_src=av_url if av_url else None,
            bgcolor=T["primary_lt"],
            content=ft.Text(name[:1], color=T["primary"], weight=ft.FontWeight.BOLD) if not av_url else None,
        ),
    )

    def _stat_row(icon, val, label, color, on_tap) -> ft.GestureDetector:
        return ft.GestureDetector(
            on_tap=on_tap,
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Container(
                width=200,
                padding=_ps(h=10, v=8), border_radius=14, margin=_m(b=6),
                bgcolor=T["surface"], shadow=_shadow(6, "#12000000"),
                content=ft.Row([
                    ft.Row([
                        ft.Container(
                            width=36, height=36, border_radius=12,
                            bgcolor=f"{color}14",
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=color, size=17),
                        ),
                        ft.Container(width=8),
                        ft.Column([
                            ft.Text(str(val), size=18, weight=ft.FontWeight.W_800, color=color),
                            ft.Text(label, size=9, color=T["text_sub"]),
                        ], spacing=1),
                    ]),
                    ft.Icon(I_CHEVRON, color=T["text_hint"], size=14),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
        )

    def _nav_btn(icon, en, ur, color, tap) -> ft.GestureDetector:
        return ft.GestureDetector(
            on_tap=tap,
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Container(
                width=200,
                height=50, border_radius=14, margin=_m(b=6),
                bgcolor=T["surface"], shadow=_shadow(4, "#0D000000"),
                padding=_p(l=10, r=10, t=0, b=0),
                content=ft.Row([
                    ft.Row([
                        ft.Container(
                            width=32, height=32, border_radius=10,
                            bgcolor=f"{color}14",
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=color, size=16),
                        ),
                        ft.Container(width=8),
                        ft.Column([
                            ft.Text(en, size=11, weight=ft.FontWeight.W_700, color=T["text"]),
                            ft.Text(ur, size=9, color=T["text_sub"]),
                        ], spacing=0),
                    ]),
                    ft.Icon(I_CHEVRON, color=T["text_hint"], size=12),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
        )

    col_items: List[ft.Control] = [
        ft.Container(
            width=200,
            content=ft.Row([
                avatar,
                ft.Container(width=8),
                ft.Column([
                    ft.Text(name, size=14, weight=ft.FontWeight.W_800, color="red",
                            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"🩸 {blood}" if blood else "", size=11, color="#FFCDD2"),
                    role_chip,
                ], spacing=3, alignment=ft.MainAxisAlignment.END),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ),
        _divider_line(),
        _stat_row(I_PEOPLE, stats["members"],   "Members",  T["primary"],    callbacks.get("members")),
        _stat_row(I_HEART,  stats["donors"],    "Donors",   "#E53935",       callbacks.get("donors")),
        _stat_row(I_BLOOD,  stats["requests"], "Requests", T["primary_dk"], callbacks.get("requests")),
        _divider_line(),
        _nav_btn(I_BLOOD,   "Request Blood", "خون مانگیں",   T["primary"],    callbacks.get("nav_request")),
        _nav_btn(I_DONOR,   "Donate Blood",  "ڈونر بنیں",   "#E53935",       callbacks.get("nav_donor")),
        _nav_btn(I_LEADER,  "Leaders View",  "رہنما کا ویو", T["teal"],       callbacks.get("leaders_view")),
        _nav_btn(I_NEWS,    "Updates",       "خبریں",       T["purple"],     callbacks.get("updates")),
        _nav_btn(I_PERSON2, "Profile",       "پروفائل",     T["primary_dk"], callbacks.get("nav_profile")),
        _nav_btn(I_STAR,    "Leaderboard",  "لیڈر بورڈ",  "#F57F17",       callbacks.get("leaderboard")),
        _nav_btn(I_HEART,   "Feedback",     "تاثرات",       T["green"],      callbacks.get("feedback")),
        _nav_btn(ft.Icons.SUPPORT_AGENT_ROUNDED, "Contact Support", "رابطہ کریں", "#00897B", callbacks.get("support")),
        _nav_btn(ft.Icons.MY_LOCATION_ROUNDED, "Update Location", "لوکیشن اپڈیٹ کریں", T["blue"], callbacks.get("update_location")),
    ]

    if is_admin(role):
        col_items += [
            _nav_btn(I_ADMIN, "Admin Panel", "ایڈمن پینل", T["blue"], callbacks.get("nav_admin")),
        ]

    return ft.Container(
        width=220,
        padding=_ps(h=10, v=14),
        bgcolor=T["bg"],
        content=ft.Column(
            controls=col_items,
            spacing=0,
            scroll=ft.ScrollMode.ALWAYS,
        ),
    )

