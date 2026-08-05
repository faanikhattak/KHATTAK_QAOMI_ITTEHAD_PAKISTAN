# ================================================================
#  pages/user/profile.py  —  User Profile
#  members table | donor toggle | badges | config provinces
#  Flet 0.84 compatible | Session-safe
# ================================================================
from core.theme import Theme 
import flet as ft
import asyncio
import threading
import time
from supabase import create_client
from services.database.db import SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options
from home_module.media_picker import MediaPickerManager, PickedFile
from core.config import BLOOD_GROUPS, PROVINCES, COUNTRIES, get_provinces, get_districts, get_tehsils

PRIMARY    = "#C62828"
PRIMARY_LT = "#FFEBEE"
PRIMARY_MD = "#FFCDD2"
PRIMARY_DK = "#B71C1C"
GREEN      = "#2E7D32"
GREEN_LT   = "#E8F5E9"
BLUE       = "#1565C0"
ORANGE     = "#E65100"
BG         = "#FFF8F8"
TEXT       = "#212121"
TEXT_SUB   = "#757575"
SURFACE    = "#FFFFFF"

BADGES = {
    "first_drop": ("🌱", "First Drop",  GREEN),
    "helper":     ("💪", "Helper",      BLUE),
    "hero":       ("⭐", "Hero",        PRIMARY),
    "legend":     ("👑", "Legend",      "#6A1B9A"),
}


def _read_session(page: ft.Page) -> dict:
    try:
        if hasattr(page.session, "_Session__store"):
            store = page.session._Session__store
            return {
                "user_id":      store.get("user_id")      or "",
                "access_token": store.get("access_token") or "",
                "refresh_token":store.get("refresh_token") or "",
                "email":        store.get("email")        or "",
                "role":         store.get("role")         or "member",
                "full_name":    store.get("full_name")    or "",
                "blood_group":  store.get("blood_group")  or "",
            }
    except Exception as ex:
        print(f"[PROFILE] session read error: {ex}")
    return {}


def view(page: ft.Page) -> ft.View:

    session         = _read_session(page)
    current_user_id = session.get("user_id", "").strip()
    access_token    = session.get("access_token", "").strip()

    if not current_user_id or not access_token:
        threading.Thread(
            target=lambda: (time.sleep(0.1),
                            page.run_task(lambda: page.go("/login"))),
            daemon=True,
        ).start()
        return ft.View(
            route="/profile", bgcolor=BG,
            controls=[ft.Text("Session expired...", color=PRIMARY)],
        )

    # ── Per-session Supabase client ──────────────────────────────
    _sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())

    async def _restore():
        try:
            rt = session.get("refresh_token", "")
            await asyncio.to_thread(_sb.auth.set_session, access_token, rt)
        except Exception:
            pass

    media_manager = MediaPickerManager(page, access_token=access_token)

    # ── Snackbar ────────────────────────────────────────────────
    def snack(msg, color=PRIMARY):
        async def _show():
            try:
                sb = ft.SnackBar(
                    content=ft.Text(msg, color="white",
                                    weight=ft.FontWeight.BOLD, size=13),
                    bgcolor=color, duration=4000,
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

    # ── Content column ───────────────────────────────────────────
    content_col = ft.Column(
        [ft.Container(
            expand=True, alignment=ft.Alignment(0, 0),
            content=ft.ProgressRing(color=PRIMARY, width=40, height=40),
        )],
        expand=True,
    )

    # ── Section header ───────────────────────────────────────────
    def _section(icon, en, ur):
        return ft.Container(
            padding=ft.padding.only(top=16, bottom=4),
            content=ft.Row([
                ft.Icon(icon, color=PRIMARY, size=18),
                ft.Text(f"{en} | {ur}", size=14,
                        weight=ft.FontWeight.BOLD, color=PRIMARY_DK),
            ], spacing=6),
        )

    # ── Avatar refs ──────────────────────────────────────────────
    avatar_img_ref = ft.Ref[ft.Container]()
    avatar_url_ref = [None]

    def update_avatar(url):
        avatar_url_ref[0] = url
        if avatar_img_ref.current:
            avatar_img_ref.current.content = (
                ft.Image(src=url, fit="cover", width=90, height=90)
                if url else
                ft.Icon(ft.Icons.PERSON_ROUNDED, size=50, color=PRIMARY)
            )
            try:
                avatar_img_ref.current.update()
            except Exception:
                pass

    def on_photo_upload(e=None):
        async def _upload():
            def on_picked(picked: PickedFile):
                async def _do():
                    def on_done(url: str, is_vid: bool):
                        try:
                            _sb.table("profiles").update(
                                {"avatar_url": url}
                            ).eq("id", current_user_id).execute()
                            update_avatar(url)
                            snack("✅ Photo updated!", GREEN)
                        except Exception as ex:
                            snack(f"❌ {str(ex)[:50]}")
                    await media_manager.upload_attached_async(
                        bucket_path="profiles/avatars",
                        on_complete=on_done,
                    )
                page.run_task(_do)

            await media_manager.attach_media_async(
                allowed_extensions=["jpg", "jpeg", "png", "webp"],
                on_picked=on_picked,
            )
        page.run_task(_upload)

    # ================================================================
    #  LOAD PROFILE
    # ================================================================
    def load_profile():
        async def _work():
            try:
                await _restore()

                # Fetch from members table
                def _fetch():
                    return (
                        _sb.table("profiles")
                        .select("*")
                        .eq("id", current_user_id)
                        .limit(1)
                        .execute()
                    )

                res = await asyncio.to_thread(_fetch)
                p = res.data[0] if res.data else {}

                # Fetch badges
                def _badges():
                    return (
                        _sb.table("donor_badges")
                        .select("*")
                        .eq("id", current_user_id) # آپ کا اصل کالم (اگر کالم 'donor_id' ہے تو آپ بدل سکتے ہیں)
                        .execute()
                    )
                br = await asyncio.to_thread(_badges)
                my_badges = {b.get("badge_type"): b for b in (br.data or [])}

                # Fetch donation stats
                def _don_count():
                    return (
                        _sb.table("donations")
                        .select("id", count="exact")
                        .eq("donor_id", current_user_id)
                        .execute()
                    )
                dr = await asyncio.to_thread(_don_count)
                don_count = dr.count or 0

                avatar_url_ref[0] = p.get("avatar_url")

                # ── Build UI ────────────────────────────────────────
                FS = dict(
                    border_radius=14, focused_border_color=PRIMARY,
                    border_color="#BDBDBD", text_size=14,
                    label_style=ft.TextStyle(color=TEXT_SUB),
                )
                DD = dict(border_radius=14, focused_border_color=PRIMARY,
                          border_color="#BDBDBD")
                W, HW = 390, 187

                def gv(key, default=""):
                    val = p.get(key, default)
                    return str(val) if val is not None else default

                # ── Donor availability toggle ────────────────────────
                is_available   = p.get("is_available", False)
                is_eligible    = p.get("is_eligible_donor", True)
                last_donation  = gv("last_donation_date")

                avail_text = ft.Text(
                    "دستیاب ہوں ✅" if is_available else "ابھی دستیاب نہیں ⛔",
                    size=12,
                    color=GREEN if is_available else TEXT_SUB,
                )
                avail_switch = ft.Switch(
                    value=is_available,
                    active_color=GREEN,
                    disabled=not is_eligible,
                )

                def _on_toggle(e):
                    async def _do():
                        try:
                            val = avail_switch.value
                            def _upd():
                                _sb.table("profiles").update(
                                    {"is_available": val}
                                ).eq("id", current_user_id).execute()
                            await asyncio.to_thread(_upd)
                            avail_text.value = "دستیاب ہوں ✅" if val else "ابھی دستیاب نہیں ⛔"
                            avail_text.color = GREEN if val else TEXT_SUB
                            snack("✅ Availability updated!", GREEN if val else TEXT_SUB)
                            page.update()
                        except Exception as ex:
                            snack(f"❌ {str(ex)[:50]}")
                    page.run_task(_do)

                avail_switch.on_change = _on_toggle

                donor_card = ft.Container(
                    margin=ft.margin.symmetric(vertical=8),
                    padding=ft.padding.all(14),
                    border_radius=16,
                    bgcolor=GREEN_LT if is_available else PRIMARY_LT,
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.VOLUNTEER_ACTIVISM,
                                    color=GREEN if is_available else PRIMARY, size=22),
                            ft.Container(width=8),
                            ft.Column([
                                ft.Text("Donor Availability | دستیابی", size=13,
                                        weight=ft.FontWeight.W_700,
                                        color=GREEN if is_available else PRIMARY),
                                avail_text,
                            ], spacing=2, expand=True, tight=True),
                            avail_switch,
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Container(
                            visible=not is_eligible,
                            margin=ft.margin.only(top=6),
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            border_radius=8, bgcolor=PRIMARY_LT,
                            content=ft.Text(
                                f"⏳ 3 mahine ka gap — Last donation: {last_donation}",
                                size=10, color=PRIMARY,
                            ),
                        ),
                    ], spacing=0, tight=True),
                )

                # ── Badges section ───────────────────────────────────
                badge_chips = []
                for btype, (bem, ben, bc) in BADGES.items():
                    earned = btype in my_badges
                    badge_chips.append(
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=12, vertical=6),
                            border_radius=20,
                            bgcolor=f"{bc}22" if earned else "#F5F5F5",
                            opacity=1.0 if earned else 0.4,
                            content=ft.Row([
                                ft.Text(bem if earned else "🔒", size=16),
                                ft.Container(width=4),
                                ft.Text(ben, size=11, color=bc if earned else TEXT_SUB,
                                        weight=ft.FontWeight.W_600),
                            ], spacing=0, tight=True),
                        )
                    )

                stats_card = ft.Container(
                    margin=ft.margin.symmetric(vertical=4),
                    padding=ft.padding.all(14),
                    border_radius=16,
                    bgcolor=SURFACE,
                    shadow=ft.BoxShadow(blur_radius=6, color="#10000000",
                                        offset=ft.Offset(0, 2)),
                    content=ft.Column([
                        ft.Row([
                            ft.Column([
                                ft.Text(str(don_count), size=28,
                                        weight=ft.FontWeight.BOLD, color=PRIMARY),
                                ft.Text("Total Donations\nکل عطیات", size=10,
                                        color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                               spacing=2),
                            ft.VerticalDivider(width=1, color=PRIMARY_MD),
                            ft.Column([
                                ft.Text(
                                    last_donation[:10] if last_donation else "---",
                                    size=14, weight=ft.FontWeight.BOLD, color=PRIMARY,
                                ),
                                ft.Text("Last Donation\nآخری عطیہ", size=10,
                                        color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                               spacing=2),
                            ft.VerticalDivider(width=1, color=PRIMARY_MD),
                            ft.Column([
                                ft.Text(str(len(my_badges)), size=28,
                                        weight=ft.FontWeight.BOLD, color=PRIMARY),
                                ft.Text("Badges\nبیجز", size=10,
                                        color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                               spacing=2),
                        ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                        ft.Container(height=10),
                        ft.Text("My Badges | میرے بیجز", size=12,
                                color=TEXT_SUB, weight=ft.FontWeight.W_600),
                        ft.Container(height=4),
                        ft.Row(badge_chips, wrap=True, spacing=8),
                    ], spacing=4, tight=True),
                )

                # ── Form fields ──────────────────────────────────────
                full_name_f   = ft.TextField(label="Full Name | پورا نام",
                    prefix_icon=ft.Icons.PERSON_OUTLINE, value=gv("full_name"),
                    width=W, **FS)
                father_name_f = ft.TextField(label="Father Name | والد کا نام",
                    prefix_icon=ft.Icons.PEOPLE_OUTLINE, value=gv("father_name"),
                    width=W, **FS)
                cnic_f        = ft.TextField(label="CNIC | شناختی کارڈ",
                    prefix_icon=ft.Icons.BADGE_OUTLINED, hint_text="xxxxx-xxxxxxx-x",
                    value=gv("cnic"), width=W, **FS)
                gender_f      = ft.Dropdown(label="Gender | جنس", width=HW, **DD,
                    value=p.get("gender"),
                    options=[ft.dropdown.Option("male","Male | مرد"),
                             ft.dropdown.Option("female","Female | عورت"),
                             ft.dropdown.Option("other","Other | دیگر")])
                dob_f         = ft.TextField(label="Date of Birth | تاریخ پیدائش",
                    prefix_icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                    hint_text="YYYY-MM-DD", value=gv("date_of_birth"),
                    width=HW, **FS)
                marital_f     = ft.Dropdown(label="Marital Status | ازدواجی حیثیت",
                    width=HW, **DD, value=p.get("marital_status"),
                    options=[ft.dropdown.Option("single","Single | غیر شادی شدہ"),
                             ft.dropdown.Option("married","Married | شادی شدہ"),
                             ft.dropdown.Option("divorced","Divorced | طلاق یافتہ"),
                             ft.dropdown.Option("widowed","Widowed | بیوہ")])
                blood_f       = ft.Dropdown(label="Blood Group | خون کا گروپ",
                    width=HW, **DD, value=p.get("blood_group"),
                    options=[ft.dropdown.Option(g) for g in BLOOD_GROUPS])
                religion_f    = ft.Dropdown(label="Religion | مذہب",
                    width=HW, **DD, value=p.get("religion"),
                    options=[ft.dropdown.Option("islam","Islam | اسلام"),
                             ft.dropdown.Option("christianity","Christianity | عیسائیت"),
                             ft.dropdown.Option("hinduism","Hinduism | ہندو مت"),
                             ft.dropdown.Option("other","Other | دیگر")])
                profession_f  = ft.TextField(label="Profession | پیشہ",
                    prefix_icon=ft.Icons.WORK_OUTLINE, value=gv("profession"),
                    width=W, **FS)
                cast_f        = ft.TextField(label="Cast | ذات",
                    prefix_icon=ft.Icons.GROUPS_OUTLINED, value=gv("cast_name"),
                    width=HW, **FS)
                sub_cast_f    = ft.TextField(label="Sub-Cast | ذیلی ذات",
                    prefix_icon=ft.Icons.ACCOUNT_TREE_OUTLINED, value=gv("sub_caste"),
                    width=HW, **FS)
                phone_f       = ft.TextField(label="Mobile | موبائل",
                    prefix_icon=ft.Icons.PHONE_OUTLINED, hint_text="03xxxxxxxxx",
                    value=gv("phone"), keyboard_type=ft.KeyboardType.PHONE,
                    width=W, **FS)
                whatsapp_f    = ft.TextField(label="WhatsApp | واٹس ایپ",
                    prefix_icon=ft.Icons.CHAT_OUTLINED, hint_text="03xxxxxxxxx",
                    value=gv("whatsapp"), keyboard_type=ft.KeyboardType.PHONE,
                    width=W, **FS)
                emergency_f   = ft.TextField(label="Emergency Contact | ہنگامی رابطہ",
                    prefix_icon=ft.Icons.EMERGENCY_OUTLINED, hint_text="03xxxxxxxxx",
                    value=gv("emergency_contact"),
                    keyboard_type=ft.KeyboardType.PHONE, width=W, **FS)

                # ── Location data handling ───────────────────────────
                old_country  = p.get("country") or "Pakistan"
                old_province = p.get("province")
                old_city     = p.get("city")
                old_tehsil   = p.get("tehsil_village")

                # pre-populate cascaded lists from saved values
                old_provinces = get_provinces(old_country)
                old_districts = get_districts(old_country, old_province or "") if old_province else []
                old_tehsils   = get_tehsils(old_country, old_province or "", old_city or "") if (old_province and old_city) else []

                country_f = ft.Dropdown(
                    label="Country | ملک", width=W, **DD,
                    value=old_country,
                    options=[ft.dropdown.Option(c) for c in COUNTRIES],
                )
                province_f = ft.Dropdown(
                    label="Province / State | صوبہ", width=W, **DD,
                    value=old_province,
                    options=[ft.dropdown.Option(pr) for pr in old_provinces],
                )
                city_f = ft.Dropdown(
                    label="City / District | شہر / ضلع", width=W, **DD,
                    value=old_city,
                    options=[ft.dropdown.Option(c) for c in old_districts],
                )
                tehsil_f = ft.Dropdown(
                    label="Tehsil / Area | تحصیل", width=W, **DD,
                    value=old_tehsil,
                    options=[ft.dropdown.Option(t) for t in old_tehsils],
                    visible=bool(old_tehsils),
                )

                # ── Location Events (on_select — Flet 0.84 Dropdown) ──
                def _on_country(e):
                    provinces = get_provinces(country_f.value or "")
                    province_f.options = [ft.dropdown.Option(pr) for pr in provinces]
                    province_f.value = None
                    city_f.options = []
                    city_f.value = None
                    tehsil_f.options = []
                    tehsil_f.value = None
                    tehsil_f.visible = False
                    page.update()

                def _on_province(e):
                    districts = get_districts(country_f.value or "", province_f.value or "")
                    city_f.options = [ft.dropdown.Option(d) for d in districts]
                    city_f.value = None
                    tehsil_f.options = []
                    tehsil_f.value = None
                    tehsil_f.visible = False
                    page.update()

                def _on_city(e):
                    tehsils = get_tehsils(country_f.value or "", province_f.value or "", city_f.value or "")
                    tehsil_f.options = [ft.dropdown.Option(t) for t in tehsils]
                    tehsil_f.value = None
                    tehsil_f.visible = bool(tehsils)
                    page.update()

                country_f.on_select  = _on_country
                province_f.on_select = _on_province
                city_f.on_select     = _on_city

                address_f = ft.TextField(label="Full Address | مکمل پتہ",
                    prefix_icon=ft.Icons.HOME_OUTLINED, multiline=True,
                    min_lines=2, max_lines=3, value=gv("address"), width=W, **FS)

                status_text = ft.Text("", size=13)

                # ── Save ─────────────────────────────────────────────
                def save(e=None):
                    async def _do():
                        try:
                            await _restore()
                            update_data = {
                                "full_name":         full_name_f.value or None,
                                "father_name":       father_name_f.value or None,
                                "cnic":              cnic_f.value or None,
                                "gender":            gender_f.value or None,
                                "date_of_birth":     dob_f.value or None,
                                "marital_status":    marital_f.value or None,
                                "blood_group":       blood_f.value or None,
                                "religion":          religion_f.value or None,
                                "profession":        profession_f.value or None,
                                "cast_name":         cast_f.value or None,
                                "sub_caste":         sub_cast_f.value or None,
                                "phone":             phone_f.value or None,
                                "whatsapp":          whatsapp_f.value or None,
                                "emergency_contact": emergency_f.value or None,
                                "country":           country_f.value or None,
                                "province":          province_f.value or None,
                                "city":              city_f.value or None,
                                "tehsil_village":    tehsil_f.value or None,
                                "address":           address_f.value or None,
                            }
                            def _upd():
                                _sb.table("profiles").update(update_data)\
                                   .eq("id", current_user_id).execute()
                            await asyncio.to_thread(_upd)
                            status_text.value = "✅ Profile saved!"
                            status_text.color = GREEN
                            snack("✅ Profile saved successfully!", GREEN)
                            page.update()
                        except Exception as ex:
                            print(f"[SAVE] {ex}")
                            status_text.value = f"❌ {str(ex)[:60]}"
                            status_text.color = PRIMARY
                            page.update()
                    page.run_task(_do)

                # ── Avatar widget ─────────────────────────────────────
                avatar_url = avatar_url_ref[0]
                avatar_img = ft.Container(
                    ref=avatar_img_ref,
                    width=90, height=90, border_radius=45,
                    bgcolor=PRIMARY_MD,
                    border=ft.border.all(3, PRIMARY),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    on_click=on_photo_upload,
                    content=(
                        ft.Image(src=avatar_url, fit="cover", width=90, height=90)
                        if avatar_url else
                        ft.Icon(ft.Icons.PERSON_ROUNDED, size=50, color=PRIMARY)
                    ),
                )

                # ── Assemble ─────────────────────────────────────────
                content_col.controls.clear()
                content_col.controls.append(
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=480,
                                content=ft.ListView(
                                    expand=True,
                                    padding=ft.padding.all(16),
                                    spacing=10,
                                    controls=[
                                        # Avatar
                                        ft.Row([avatar_img],
                                               alignment=ft.MainAxisAlignment.CENTER),
                                        ft.Row([
                                            ft.TextButton(
                                                "📷 Change Photo | تصویر بدلیں",
                                                style=ft.ButtonStyle(color=PRIMARY),
                                                on_click=on_photo_upload,
                                            )
                                        ], alignment=ft.MainAxisAlignment.CENTER),
                                        ft.Row([
                                            ft.Text(gv("full_name") or "Member",
                                                    size=17, weight=ft.FontWeight.BOLD,
                                                    color=PRIMARY_DK),
                                        ], alignment=ft.MainAxisAlignment.CENTER),
                                        ft.Row([
                                            ft.Container(
                                                padding=ft.padding.symmetric(horizontal=12, vertical=4),
                                                border_radius=20, bgcolor=PRIMARY_MD,
                                                content=ft.Text(
                                                    gv("role","member").upper(),
                                                    size=11, color=PRIMARY_DK,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                            ),
                                        ], alignment=ft.MainAxisAlignment.CENTER),

                                        ft.Divider(color=PRIMARY_MD),

                                        # Donor card
                                        donor_card,

                                        # Stats + badges
                                        stats_card,

                                        ft.Divider(color=PRIMARY_MD),

                                        # Personal Info
                                        _section(ft.Icons.PERSON_OUTLINE,
                                                 "Personal Info", "ذاتی معلومات"),
                                        full_name_f, father_name_f, cnic_f,
                                        ft.Row([gender_f, dob_f], spacing=10),
                                        ft.Row([marital_f, blood_f], spacing=10),
                                        ft.Row([religion_f, cast_f], spacing=10),
                                        sub_cast_f, profession_f,

                                        # Contact
                                        _section(ft.Icons.PHONE_OUTLINED,
                                                 "Contact", "رابطہ"),
                                        phone_f, whatsapp_f, emergency_f,

                                        # Location
                                        _section(ft.Icons.LOCATION_ON_OUTLINED,
                                                 "Location", "مقام"),
                                        country_f, province_f, city_f, tehsil_f, address_f,

                                        ft.Divider(color=PRIMARY_MD),
                                        status_text,

                                        ft.ElevatedButton(
                                            "Save Changes | تبدیلیاں محفوظ کریں",
                                            icon=ft.Icons.SAVE_ROUNDED,
                                            style=ft.ButtonStyle(
                                                bgcolor=PRIMARY, color="white",
                                                shape=ft.RoundedRectangleBorder(radius=12),
                                            ),
                                            width=float("inf"),
                                            on_click=save,
                                        ),
                                        ft.Container(height=40),
                                    ],
                                ),
                            ),
                        ],
                    )
                )
                page.update()

            except Exception as ex:
                print(f"[PROFILE] load error: {ex}")
                import traceback
                traceback.print_exc()
                snack(f"❌ Error: {str(ex)[:60]}")

        page.run_task(_work)

    load_profile()

    return ft.View(
        route="/profile",
        bgcolor=BG,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/home"),
            ),
            title=ft.Column([
                ft.Text("My Profile | میری پروفائل", size=15,
                        weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("تفصیلات اور ترجیحات", size=10, color=PRIMARY_MD),
            ], spacing=0),
            bgcolor=PRIMARY,
            actions=[
                ft.IconButton(
                    ft.Icons.LEADERBOARD_ROUNDED,
                    icon_color="white",
                    tooltip="Leaderboard",
                    on_click=lambda _: page.go("/leaderboard"),
                ),
            ],
        ),
        controls=[content_col],
    )

