


# ================================================================
#  pages/user/leaders_common.py — Shared Leadership Helpers
#
#  Used by both leaders.py (/leaders, central-only) and
#  leaders_view.py (/leaders_view, full tree). All avatar/card/
#  dialog/delete/fetch logic lives here ONCE so the two route
#  files stay tiny and never drift apart.
#
#  Permissions:
#    - Any admin (is_admin(role) == True)      -> can ADD / EDIT
#    - Only head admin (is_head_admin(role))    -> can DELETE
#      Adjust the role string(s) in is_head_admin() below to match
#      your actual role field if it differs.
# ================================================================
import asyncio
import uuid
import flet as ft
from supabase import create_client

from core.theme import Theme
from services.database.db import SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options
from home_module.home_config import T, is_admin
from core.config import COUNTRIES, get_provinces, get_districts

LEVELS = [
    ("central",    "🏛️ Central",    "مرکزی"),
    ("provincial", "🗺️ Provincial", "صوبائی"),
    ("district",   "📍 District",   "ضلعی"),
    ("overseas",   "🌍 Overseas",   "بیرون ملک"),
]
LEVEL_LABELS = {k: f"{em} | {ur}" for k, em, ur in LEVELS}


def is_head_admin(role: str) -> bool:
    return (role or "").strip().lower() in ("head_admin", "super_admin", "owner")


# ================================================================
#  Session / supabase / snackbar helpers
# ================================================================
def sess_get(page: ft.Page, key, default=""):
    try:
        if hasattr(page.session, "_Session__store"):
            return page.session._Session__store.get(key) or default
        return page.session.get(key) or default
    except Exception:
        return default


def init_common(page: ft.Page):
    """Returns (sb, role, can_edit, can_delete, restore, snack)."""
    sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())
    role = sess_get(page, "role", "member")
    can_edit = is_admin(role)
    can_delete = is_head_admin(role)

    async def restore():
        try:
            at = sess_get(page, "access_token")
            rt = sess_get(page, "refresh_token", "")
            if at:
                await asyncio.to_thread(sb.auth.set_session, at, rt)
        except Exception:
            pass

    def snack(msg, color=None):
        color = color or T.get("primary", ft.Colors.BLUE)

        async def _show():
            try:
                sb_bar = ft.SnackBar(
                    content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD),
                    bgcolor=color, duration=3000,
                )
                page.overlay.append(sb_bar)
                sb_bar.open = True
                page.update()
            except Exception:
                pass
        try:
            page.run_task(_show)
        except Exception:
            pass

    return sb, role, can_edit, can_delete, restore, snack


async def fetch_leaders(sb, restore, query: str = ""):
    await restore()

    def _fetch():
        return (
            sb.table("leaders")
            .select("*")
            .order("display_order", desc=False)
            .execute()
        )

    res = await asyncio.to_thread(_fetch)
    data = res.data or []

    if query.strip():
        q = query.lower().strip()
        data = [
            l for l in data
            if q in (l.get("name") or "").lower()
            or q in (l.get("name_ur") or "").lower()
            or q in (l.get("title") or "").lower()
            or q in (l.get("district") or "").lower()
            or q in (l.get("province") or "").lower()
        ]
    return data


# ================================================================
#  Avatar + leader card
# ================================================================
def _initials(name: str) -> str:
    ps = (name or "?").split()
    return (ps[0][0] + (ps[-1][0] if len(ps) > 1 else "")).upper()


def avatar(ldr: dict, size: int = 44) -> ft.Container:
    name  = ldr.get("name") or ldr.get("name_ur") or "?"
    color = ldr.get("color") or T.get("primary", ft.Colors.BLUE)
    img   = ldr.get("image_url")
    inner: ft.Control = (
        ft.Image(
            src=img, fit="cover", width=size, height=size,
            error_content=ft.Text(_initials(name), size=size * 0.32,
                                   color="white", weight=ft.FontWeight.BOLD),
        )
        if img else
        ft.Text(_initials(name), size=size * 0.32, color="white", weight=ft.FontWeight.BOLD)
    )
    return ft.Container(
        width=size, height=size, border_radius=size // 2,
        bgcolor=color, alignment=ft.Alignment(0, 0),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=inner,
    )


def leader_card_row(ldr: dict, page: ft.Page, can_edit: bool = False, can_delete: bool = False,
                     on_edit_click=None, on_delete_click=None) -> ft.Container:
    """Reusable leader card: image, name, designation, location, call/whatsapp/edit/delete."""
    name     = ldr.get("name_ur") or ldr.get("name") or "Leader"
    title    = ldr.get("title_ur") or ldr.get("title") or ""
    phone    = ldr.get("phone") or ""
    whatsapp = ldr.get("whatsapp") or ""

    loc_bits = [
        b for b in (ldr.get("district"), ldr.get("province"),
                    ldr.get("country") if ldr.get("level") == "overseas" else None) if b
    ]
    location = " — ".join(loc_bits)

    def _call(e=None):
        if phone:
            page.launch_url(f"tel:{phone}")

    def _chat(e=None):
        if whatsapp:
            clean_wa = "".join(filter(str.isdigit, whatsapp))
            page.launch_url(f"https://wa.me/{clean_wa}")

    right: list[ft.Control] = []
    if phone:
        right.append(ft.IconButton(
            icon=ft.Icons.PHONE, icon_color=T.get("green", ft.Colors.GREEN), icon_size=18,
            tooltip="Call", on_click=_call,
        ))
    if whatsapp:
        right.append(ft.IconButton(
            icon=ft.Icons.CHAT_OUTLINED, icon_color=T.get("teal", ft.Colors.TEAL), icon_size=18,
            tooltip="WhatsApp", on_click=_chat,
        ))
    if can_edit and on_edit_click:
        right.append(ft.IconButton(
            icon=ft.Icons.EDIT_OUTLINED, icon_color=T.get("text_sub", ft.Colors.GREY), icon_size=18,
            tooltip="Edit", on_click=lambda e: on_edit_click(ldr),
        ))
    if can_delete and on_delete_click:
        right.append(ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE, icon_color=T.get("primary", ft.Colors.RED), icon_size=18,
            tooltip="Delete", on_click=lambda e: on_delete_click(ldr),
        ))

    return ft.Container(
        bgcolor=T.get("surface", ft.Colors.WHITE), border_radius=14,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        content=ft.Row(
            [
                avatar(ldr),
                ft.Container(width=10),
                ft.Column(
                    [
                        ft.Text(name, size=13, weight=ft.FontWeight.W_700, color=T.get("text", ft.Colors.BLACK)),
                        ft.Text(title, size=11, color=T.get("primary", ft.Colors.BLUE)) if title else ft.Container(),
                        ft.Text(location, size=10, color=T.get("text_sub", ft.Colors.GREY)) if location else ft.Container(),
                    ],
                    spacing=2, expand=True, tight=True,
                ),
                *right,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


# ================================================================
#  Delete confirmation
# ================================================================
def make_delete_handler(page: ft.Page, sb, restore, snack, on_deleted):
    """Returns a function(ldr) that shows a confirm dialog, then deletes on confirm."""
    def _delete(ldr: dict):
        def _confirm(e=None):
            async def _do():
                try:
                    await restore()
                    await asyncio.to_thread(
                        lambda: sb.table("leaders").delete().eq("id", ldr["id"]).execute()
                    )
                    page.close(confirm_dlg)
                    snack("🗑️ Deleted | حذف کر دیا گیا", T.get("green", ft.Colors.GREEN))
                    await on_deleted()
                except Exception as ex:
                    snack(f"Error: {str(ex)[:80]}", T.get("primary", ft.Colors.RED))
            page.run_task(_do)

        def _cancel(e=None):
            page.close(confirm_dlg)

        confirm_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Leader? | لیڈر حذف کریں؟", weight=ft.FontWeight.BOLD,
                           color=T.get("primary", ft.Colors.RED)),
            content=ft.Text(
                f"Are you sure you want to permanently remove "
                f"{ldr.get('name') or ldr.get('name_ur') or 'this leader'}? "
                f"This cannot be undone."
            ),
            actions=[
                ft.TextButton("Cancel | منسوخ", on_click=_cancel),
                ft.ElevatedButton(
                    "Delete | حذف کریں",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color="white",
                                          shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=_confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if confirm_dlg not in page.overlay:
            page.overlay.append(confirm_dlg)
        confirm_dlg.open = True
        page.update()

    return _delete


# ================================================================
#  Add / edit dialog
# ================================================================
def make_edit_dialog_opener(page: ft.Page, sb, restore, snack, on_saved, default_level: str = "central"):
    """
    Returns a function(ldr | None) that opens the Add/Edit dialog.
    Pass ldr=None to add a new leader (pre-filled with default_level).
    on_saved: async-callable invoked after a successful insert/update.
    """
    def _open_edit_dialog(ldr: dict | None):
        is_new = ldr is None
        ldr = ldr or {"level": default_level}
        selected_file = {"bytes": None, "name": None}

        name_f = ft.TextField(label="Name | نام", value=ldr.get("name", ""),
                               border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE))
        name_ur_f = ft.TextField(label="Name (Urdu) | نام اردو", value=ldr.get("name_ur", ""),
                                  border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE))
        title_f = ft.TextField(label="Designation | عہدہ", value=ldr.get("title", ""),
                                border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE))
        title_ur_f = ft.TextField(label="Designation (Urdu)", value=ldr.get("title_ur", ""),
                                   border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE))
        phone_f = ft.TextField(label="Phone | فون", value=ldr.get("phone", ""),
                                keyboard_type=ft.KeyboardType.PHONE,
                                border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE))
        whatsapp_f = ft.TextField(label="WhatsApp", value=ldr.get("whatsapp", ""),
                                   keyboard_type=ft.KeyboardType.PHONE,
                                   border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE))
        image_f = ft.TextField(label="Image URL | تصویر کا لنک", value=ldr.get("image_url", ""),
                                hint_text="Paste an image link",
                                border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE))

        level_f = ft.Dropdown(
            label="Level | سطح",
            value=ldr.get("level", default_level),
            options=[ft.dropdown.Option(k, lbl) for k, lbl in LEVEL_LABELS.items()],
            border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE),
        )

        country_f = ft.Dropdown(
            label="Country | ملک",
            value=ldr.get("country", "Pakistan"),
            options=[ft.dropdown.Option(c) for c in COUNTRIES],
            border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE),
            visible=False,
        )

        province_f = ft.Dropdown(
            label="Province | صوبہ",
            value=ldr.get("province"),
            options=[ft.dropdown.Option(p) for p in get_provinces("Pakistan")],
            border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE),
            visible=False,
        )
        province_slot = ft.Container(content=province_f)

        district_f = ft.Dropdown(
            label="District | ضلع",
            value=ldr.get("district"),
            options=(
                [ft.dropdown.Option(d) for d in get_districts("Pakistan", ldr.get("province"))]
                if ldr.get("province") else []
            ),
            border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE),
            visible=False,
        )
        district_slot = ft.Container(content=district_f)

        def _update_visibility(lvl_val):
            country_f.visible = (lvl_val == "overseas")
            province_f.visible = lvl_val in ("provincial", "district")
            district_f.visible = (lvl_val == "district")

        def _rebuild_district(province_val):
            nonlocal district_f
            districts = get_districts("Pakistan", province_val) if province_val else []
            district_f = ft.Dropdown(
                label="District | ضلع",
                options=[ft.dropdown.Option(d) for d in districts],
                border_radius=12, focused_border_color=T.get("primary", ft.Colors.BLUE),
                visible=level_f.value == "district",
            )
            district_slot.content = district_f
            district_slot.update()

        def _on_province_change(e=None):
            if level_f.value == "district":
                _rebuild_district(province_f.value)
            page.update()

        province_f.on_select = _on_province_change
        province_f.on_change = _on_province_change

        def _on_level_change(e=None):
            _update_visibility(level_f.value)
            if level_f.value == "district" and province_f.value:
                _rebuild_district(province_f.value)
            page.update()

        level_f.on_select = _on_level_change
        level_f.on_change = _on_level_change

        _update_visibility(level_f.value)

        def _on_file_result(e):
            if e.files and len(e.files) > 0:
                pf = e.files[0]
                if pf.path:
                    with open(pf.path, "rb") as f:
                        selected_file["bytes"] = f.read()
                selected_file["name"] = f"{uuid.uuid4().hex}_{pf.name or 'leader.jpg'}"
                image_f.value = f"[Selected File: {pf.name}]"
                image_f.update()
        file_picker = ft.FilePicker()
        file_picker.on_result = _on_file_result 
        
        if file_picker in page.overlay:
            page.overlay.append(file_picker)
        

        def _pick_files(e=None):
            page.run_task(
                file_picker.pick_files,
                allow_multiple=False,
                allowed_extensions=["jpg", "png", "jpeg"],
            )

        upload_btn = ft.OutlinedButton(
            "Upload Photo | تصویر اپلوڈ کریں",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=_pick_files,
        )

        def _close(e=None):
            try:
                if file_picker in page.overlay:
                    page.overlay.remove(file_picker)
                dlg.open = False
                page.close(dlg)
                page.update()
            except Exception:
                pass

        def _save(e=None):
            if not name_f.value or not name_f.value.strip():
                snack("⚠ Name is required", T.get("primary", ft.Colors.RED))
                return

            async def _do():
                try:
                    await restore()

                    img_url = image_f.value.strip() or None
                    if selected_file["bytes"] and selected_file["name"]:
                        def _upload():
                            sb.storage.from_("leaders").upload(
                                file=selected_file["bytes"],
                                path=selected_file["name"],
                                file_options={"content-type": "image/jpeg"},
                            )
                            return sb.storage.from_("leaders").get_public_url(selected_file["name"])

                        img_url = await asyncio.to_thread(_upload)

                    payload = {
                        "name":      name_f.value.strip(),
                        "name_ur":   name_ur_f.value.strip() or None,
                        "title":     title_f.value.strip() or None,
                        "title_ur":  title_ur_f.value.strip() or None,
                        "phone":     phone_f.value.strip() or None,
                        "whatsapp":  whatsapp_f.value.strip() or None,
                        "image_url": img_url,
                        "level":     level_f.value or default_level,
                        "country":   country_f.value if level_f.value == "overseas" else "Pakistan",
                        "province":  province_f.value if level_f.value in ("provincial", "district") else None,
                        "district":  district_f.value if level_f.value == "district" else None,
                    }

                    def _write():
                        if is_new:
                            return sb.table("leaders").insert(payload).execute()
                        return sb.table("leaders").update(payload).eq("id", ldr["id"]).execute()

                    await asyncio.to_thread(_write)
                    _close()
                    snack("✅ Saved | محفوظ ہو گیا", T.get("green", ft.Colors.GREEN))
                    await on_saved()
                except Exception as ex:
                    snack(f"Error: {str(ex)[:80]}", T.get("primary", ft.Colors.RED))

            page.run_task(_do)

        actions = [
            ft.TextButton("Cancel | منسوخ", on_click=_close),
            ft.ElevatedButton(
                "Save | محفوظ کریں",
                style=ft.ButtonStyle(bgcolor=T.get("primary", ft.Colors.RED), color="white",
                                      shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=_save,
            ),
        ]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add Leader | لیڈر شامل کریں" if is_new else "Edit Leader | لیڈر میں ترمیم",
                           weight=ft.FontWeight.BOLD, size=18, color=T.get("primary", ft.Colors.RED)),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    [
                        name_ur_f, name_f, title_ur_f, title_f,
                        phone_f, whatsapp_f, level_f, country_f,
                        province_slot, district_slot,
                        ft.Row([upload_btn], alignment=ft.MainAxisAlignment.CENTER),
                        image_f,
                    ],
                    spacing=10, tight=True, scroll=ft.ScrollMode.AUTO, height=450,
                ),
            ),
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    return _open_edit_dialog