# ================================================================
#  pages/user/request.py  —  Blood Request page (TABBED)
#  Tab 1: Request Blood (form)
#  Tab 2: My Requests (donation-aware status list)
#  Session-safe + Province/Tehsil + Auto-match + Notifications
#  Flet 0.84 compatible
# ================================================================
from core.theme import Theme 
import asyncio
from datetime import datetime as dt_module, timedelta

import flet as ft
from typing import Optional
from supabase import create_client

from services.database.db import supabase, SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options
from core.config import (
    BLOOD_GROUPS, COUNTRIES, URGENCY_LEVELS, URGENCY_LABELS,
    REQUEST_STATUS, get_provinces, get_districts, get_tehsils,
)
from pages.user.feedback import show_feedback_dialog

# ================================================================
#  THEME — light / normal (no dark background)
# ================================================================
PRIMARY    = "#E24B4A"
PRIMARY_DK = "#A32D2D"
PRIMARY_LT = "#FBEAEA"
PRIMARY_MD = "#F3C9C9"
GREEN      = "#1D9E75"
BLUE       = "#378ADD"
ORANGE     = "#EF9F27"
BG         = "#F5F5F7"
TEXT       = "#1C1C1E"
TEXT_SUB   = "#6B6B70"
SURFACE    = "#FFFFFF"
BORDER     = "#E0E0E0"

FS = dict(
    border_radius=14,
    focused_border_color=PRIMARY,
    border_color=BORDER,
    text_size=14,
    color=TEXT,
    label_style=ft.TextStyle(color=TEXT_SUB),
    bgcolor=SURFACE,
)

W = 400


# ================================================================
#  DATE PICKER HELPER
# ================================================================
def build_date_picker(page: ft.Page, needed_by_f: ft.TextField):
    def _on_change(e):
        if date_picker.value:
            needed_by_f.value = date_picker.value.strftime("%Y-%m-%d")
            needed_by_f.data = date_picker.value.isoformat()
            page.update()

    date_picker = ft.DatePicker(
        first_date=dt_module.now(),
        last_date=dt_module.now() + timedelta(days=180),
        on_change=_on_change,
    )
    if date_picker not in page.overlay:
        page.overlay.append(date_picker)

    def _pick(e=None):
        page.open(date_picker)

    return date_picker, _pick


# ================================================================
#  VIEW
# ================================================================
def view(page: ft.Page) -> ft.View:

    # ── Session helpers ─────────────────────────────────────
    def sess_get(key: str, default="") -> str:
        try:
            if hasattr(page.session, "_Session__store"):
                return page.session._Session__store.get(key) or default
            return page.session.get(key) or default
        except Exception:
            return default

    # ── Per-session Supabase client ──────────────────────────
    _sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())

    async def _restore_session():
        try:
            at = sess_get("access_token")
            rt = sess_get("refresh_token", "")
            if at:
                await asyncio.to_thread(_sb.auth.set_session, at, rt)
        except Exception as ex:
            print(f"[REQ] session restore error: {ex}")

    # ── Snackbar ────────────────────────────────────────────
    def snack(msg: str, color: str = PRIMARY):
        async def _show():
            try:
                sb = ft.SnackBar(
                    content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD, size=13),
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

    # ── Tab switching (Flet 0.84/0.85: selected_index lives on the
    # parent ft.Tabs control, not on TabBar/TabBarView themselves) ──
    def _go_tab(idx: int):
        tabs_ctrl.selected_index = idx
        if idx == 1:
            load_my_requests()
        page.update()

    # ================================================================
    #  TAB 1 — FORM FIELDS
    # ================================================================
    patient_name_f = ft.TextField(
        label="Patient Name | مریض کا نام *",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        width=W, **FS,
    )

    blood_group_f = ft.Dropdown(
        label="Blood Group | خون گروپ *", width=W,
        border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
        color=TEXT, bgcolor=SURFACE,
        options=[ft.dropdown.Option(g) for g in BLOOD_GROUPS],
    )

    units_f = ft.TextField(
        label="Units Required | یونٹ *",
        prefix_icon=ft.Icons.BLOODTYPE_OUTLINED,
        hint_text="e.g. 2",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=W, **FS,
    )

    hospital_f = ft.TextField(
        label="Hospital | ہسپتال *",
        prefix_icon=ft.Icons.LOCAL_HOSPITAL_OUTLINED,
        width=W, **FS,
    )

    urgency_f = ft.Dropdown(
        label="Urgency | فوریت *", width=W,
        border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
        color=TEXT, bgcolor=SURFACE,
        options=[
            ft.dropdown.Option("low",      "🟢 کم ضروری (3-7 دن)"),
            ft.dropdown.Option("medium",   "🟡 درمیانہ (1-2 دن)"),
            ft.dropdown.Option("high",     "🔴 ضروری (آج)"),
            ft.dropdown.Option("critical", "🚨 ہنگامی (ابھی)"),
        ],
        value="medium",
    )

    contact_f = ft.TextField(
        label="Contact Number | رابطہ نمبر *",
        prefix_icon=ft.Icons.PHONE_OUTLINED,
        hint_text="03xxxxxxxxx",
        keyboard_type=ft.KeyboardType.PHONE,
        width=W, **FS,
    )

    notes_f = ft.TextField(
        label="Additional Notes | اضافی معلومات",
        prefix_icon=ft.Icons.NOTE_OUTLINED,
        multiline=True, min_lines=2, max_lines=4,
        width=W, **FS,
    )

    needed_by_f = ft.TextField(
        label="Needed By Date | کب تک چاہیے (optional)",
        prefix_icon=ft.Icons.CALENDAR_TODAY,
        hint_text="e.g. 2026-06-20",
        read_only=True,
        width=W, **FS,
    )

    date_picker, pick_date_click = build_date_picker(page, needed_by_f)
    needed_by_f.on_focus = pick_date_click

    dob_btn = ft.IconButton(
        icon=ft.Icons.EDIT_CALENDAR_ROUNDED,
        icon_color=PRIMARY,
        icon_size=20,
        tooltip="Pick date | تاریخ منتخب کریں",
        on_click=pick_date_click,
    )

    # ── Location dropdowns ──────────────────────────────────
    country_f = ft.Dropdown(
        label="Country | ملک *", width=W,
        border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
        color=TEXT, bgcolor=SURFACE,
        options=[ft.dropdown.Option(c) for c in COUNTRIES],
        value="Pakistan",
    )

    province_f = ft.Dropdown(
        label="Province / State | صوبہ *", width=W,
        border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
        color=TEXT, bgcolor=SURFACE,
        options=[ft.dropdown.Option(p) for p in get_provinces("Pakistan")],
    )

    city_f = ft.Dropdown(
        label="City / District | شہر / ضلع *", width=W,
        border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
        color=TEXT, bgcolor=SURFACE,
        options=[],
    )
    city_slot = ft.Container(content=city_f, width=W)

    tehsil_f = ft.Dropdown(
        label="Tehsil / Area | تحصیل (optional)", width=W,
        border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
        color=TEXT, bgcolor=SURFACE,
        options=[],
        visible=False,
    )
    tehsil_slot = ft.Container(content=tehsil_f, width=W)

    def on_city_change(e):
        selected_country  = country_f.value or "Pakistan"
        selected_province = province_f.value
        selected_city     = city_f.value
        if not selected_province or not selected_city:
            return
        tehsils = get_tehsils(selected_country, selected_province, selected_city)
        _rebuild_tehsil_dropdown(tehsils, visible=bool(tehsils))
        page.update()

    def _rebuild_city_dropdown(districts):
        nonlocal city_f
        city_f = ft.Dropdown(
            key=f"city_dd_{province_f.value}_{len(districts)}",
            label="City / District | شہر / ضلع *", width=W,
            border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
            color=TEXT, bgcolor=SURFACE,
            options=[ft.dropdown.Option(d) for d in districts],
            on_select=on_city_change,
            menu_height=320,
        )
        city_slot.content = city_f
        city_slot.update()

    def _rebuild_tehsil_dropdown(tehsils, visible: bool):
        nonlocal tehsil_f
        tehsil_f = ft.Dropdown(
            key=f"tehsil_dd_{city_f.value}_{len(tehsils)}",
            label="Tehsil / Area | تحصیل (optional)", width=W,
            border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
            color=TEXT, bgcolor=SURFACE,
            options=[ft.dropdown.Option(t) for t in tehsils],
            visible=visible,
            menu_height=320,
        )
        tehsil_slot.content = tehsil_f
        tehsil_slot.update()

    def _rebuild_province_dropdown(provinces):
        nonlocal province_f
        province_f = ft.Dropdown(
            key=f"province_dd_{country_f.value}_{len(provinces)}",
            label="Province / State | صوبہ *", width=W,
            border_radius=14, focused_border_color=PRIMARY, border_color=BORDER,
            color=TEXT, bgcolor=SURFACE,
            options=[ft.dropdown.Option(p) for p in provinces],
            on_select=on_province_change,
            menu_height=320,
        )
        province_slot.content = province_f
        province_slot.update()

    province_slot = ft.Container(content=province_f, width=W)

    def on_country_change(e):
        selected = country_f.value
        if not selected:
            return
        provinces = get_provinces(selected)
        _rebuild_province_dropdown(provinces)
        _rebuild_city_dropdown([])
        _rebuild_tehsil_dropdown([], visible=False)
        page.update()

    def on_province_change(e):
        selected_country  = country_f.value or "Pakistan"
        selected_province = province_f.value
        if not selected_province:
            return
        districts = get_districts(selected_country, selected_province)
        _rebuild_city_dropdown(districts)
        _rebuild_tehsil_dropdown([], visible=False)
        page.update()

    country_f.on_select  = on_country_change
    province_f.on_select = on_province_change
    city_f.on_select     = on_city_change

    # ── Lock request location to the requester's own profile ──
    # A request's country/province/city/tehsil used to be whatever
    # the requester happened to pick by hand in these dropdowns —
    # a wrong or stray selection meant the request showed up in
    # donor matching for a totally different district (or even a
    # different country). Now it's always auto-filled from their
    # own registered profile and locked (disabled) so it can't be
    # altered here — to change it, they update their profile.
    location_hint = ft.Text(
        "", size=11, color=TEXT_SUB, visible=False,
    )

    async def _load_requester_location():
        try:
            uid = sess_get("user_id")
            if not uid:
                return
            await _restore_session()

            def _fetch():
                return _sb.table("profiles").select("*").eq("id", uid).limit(1).execute()

            res = await asyncio.to_thread(_fetch)
            if not res.data:
                return
            p = res.data[0]

            p_country  = p.get("country") or "Pakistan"
            p_province = p.get("province") or p.get("state") or ""
            p_city     = p.get("city") or p.get("district") or ""
            p_tehsil   = p.get("tehsil") or p.get("area") or ""

            country_f.value = p_country

            if p_province:
                _rebuild_province_dropdown(get_provinces(p_country))
                province_f.value = p_province
                province_f.disabled = True
                province_slot.update()

                if p_city:
                    _rebuild_city_dropdown(get_districts(p_country, p_province))
                    city_f.value = p_city
                    city_f.disabled = True
                    city_slot.update()

                    tehsils = get_tehsils(p_country, p_province, p_city)
                    _rebuild_tehsil_dropdown(tehsils, visible=bool(tehsils))
                    if p_tehsil and tehsils:
                        tehsil_f.value = p_tehsil
                    if tehsils:
                        tehsil_f.disabled = True
                        tehsil_slot.update()

            if p_province or p_city:
                country_f.disabled = True
                location_hint.value = (
                    "📍 Location locked to your registered profile — "
                    "update your profile to change it | "
                    "مقام آپ کی پروفائل سے لیا گیا ہے"
                )
                location_hint.visible = True

            page.update()
        except Exception as ex:
            print(f"[REQ] location lock error: {ex}")

    page.run_task(_load_requester_location)

    submit_btn = ft.ElevatedButton(
        content=ft.Text("Submit Request | درخواست بھیجیں", weight=ft.FontWeight.BOLD, size=15),
        style=ft.ButtonStyle(
            color="white", bgcolor=PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=13),
            elevation=4,
        ),
        width=W, height=52,
    )

    def on_submit(e):
        async def _work():
            try:
                missing = []
                if not patient_name_f.value or not patient_name_f.value.strip():
                    missing.append("Patient Name")
                if not blood_group_f.value:
                    missing.append("Blood Group")
                if not units_f.value or not units_f.value.strip():
                    missing.append("Units")
                if not hospital_f.value or not hospital_f.value.strip():
                    missing.append("Hospital")
                if not province_f.value:
                    missing.append("Province")
                if not city_f.value:
                    missing.append("City")
                if not contact_f.value or not contact_f.value.strip():
                    missing.append("Contact")

                if missing:
                    snack(f"⚠ Please fill: {', '.join(missing)}", ORANGE)
                    return

                submit_btn.disabled = True
                submit_btn.content = ft.Row(
                    [ft.ProgressRing(width=16, height=16, color="white", stroke_width=2),
                     ft.Text("Submitting...", color="white", size=14)],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=8,
                )
                page.update()

                await _restore_session()
                uid = sess_get("user_id")
                full_name = sess_get("full_name", "Unknown")

                payload = {
                    "requested_by":         uid,
                    "patient_name":         patient_name_f.value.strip(),
                    "required_blood_group": blood_group_f.value,
                    "units_required":       int(units_f.value.strip()),
                    "hospital":             hospital_f.value.strip(),
                    "country":              country_f.value,
                    "province":             province_f.value,
                    "city":                 city_f.value,
                    "tehsil":               tehsil_f.value or None,
                    "contact":              contact_f.value.strip(),
                    "urgency":              urgency_f.value,
                    "notes":                notes_f.value.strip() or None,
                    "status":               "pending",
                }

                if needed_by_f.data:
                    payload["needed_by"] = needed_by_f.data
                elif needed_by_f.value and needed_by_f.value.strip():
                    payload["needed_by"] = needed_by_f.value.strip()

                def _insert():
                    return _sb.table("blood_requests").insert(payload).execute()

                res = await asyncio.to_thread(_insert)
                request_id = res.data[0]["id"] if res.data else None

                snack("✅ Request submitted! Donors being notified...", GREEN)

                if request_id:
                    from services.notifications import (
                        notify_matching_donors,
                        notify_area_admins,
                    )
                    donor_count = await notify_matching_donors(
                        supabase_client=_sb,
                        blood_group=blood_group_f.value,
                        province=province_f.value,
                        city=city_f.value,
                        request_id=request_id,
                        requester_name=full_name,
                        hospital=hospital_f.value.strip(),
                        urgency=urgency_f.value,
                    )
                    await notify_area_admins(
                        supabase_client=_sb,
                        province=province_f.value,
                        city=city_f.value,
                        blood_group=blood_group_f.value,
                        requester_name=full_name,
                        request_id=request_id,
                    )

                    if donor_count > 0:
                        snack(f"🩸 {donor_count} matching donors notified!", GREEN)
                    else:
                        snack("⚠ No matching donors found nearby. Admin notified.", ORANGE)

                    def _update_status():
                        _sb.table("blood_requests").update(
                            {"status": "matching"}
                        ).eq("id", request_id).execute()
                    await asyncio.to_thread(_update_status)

                # Clear form
                patient_name_f.value = ""
                blood_group_f.value = None
                units_f.value = ""
                hospital_f.value = ""
                page.run_task(_load_requester_location)
                contact_f.value = ""
                notes_f.value = ""
                needed_by_f.value = ""
                needed_by_f.data = None
                urgency_f.value = "medium"

                # Jump to "My Requests" tab so the user sees it land.
                _go_tab(1)

            except Exception as ex:
                print(f"[REQ] submit error: {ex}")
                snack(f"⚠ Error: {str(ex)[:60]}", PRIMARY)
            finally:
                submit_btn.disabled = False
                submit_btn.content = ft.Text(
                    "Submit Request | درخواست بھیجیں",
                    weight=ft.FontWeight.BOLD, size=15,
                )
                page.update()

        page.run_task(_work)

    submit_btn.on_click = on_submit

    request_form_tab = ft.Container(
        padding=ft.padding.symmetric(horizontal=20, vertical=16),
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            controls=[
                ft.Container(height=12),
                ft.Container(
                    width=64, height=64, border_radius=32,
                    bgcolor=PRIMARY_LT,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.BLOODTYPE_ROUNDED, size=36, color=PRIMARY),
                ),
                ft.Container(height=8),
                ft.Text("Request Blood", size=20, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text("خون کی درخواست کریں", size=13, color=PRIMARY),
                ft.Container(height=20),

                ft.Card(
                    elevation=4,
                    shape=ft.RoundedRectangleBorder(radius=18),
                    content=ft.Container(
                        bgcolor=SURFACE,
                        border_radius=18,
                        padding=ft.padding.symmetric(horizontal=20, vertical=18),
                        width=434,
                        content=ft.Column(
                            [
                                ft.Row([
                                    ft.Icon(ft.Icons.MEDICAL_SERVICES_OUTLINED, color=PRIMARY, size=18),
                                    ft.Text("Patient Info | مریض کی معلومات", size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                                ], spacing=8),
                                ft.Container(height=4),
                                patient_name_f,
                                blood_group_f,
                                units_f,
                                urgency_f,
                                ft.Row(
                                    [needed_by_f, dob_btn],
                                    spacing=6,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),

                                ft.Divider(color=PRIMARY_MD, height=20),

                                ft.Row([
                                    ft.Icon(ft.Icons.LOCAL_HOSPITAL_OUTLINED, color=PRIMARY, size=18),
                                    ft.Text("Hospital & Location | ہسپتال اور مقام", size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                                ], spacing=8),
                                ft.Container(height=4),
                                hospital_f,
                                country_f,
                                province_slot,
                                city_slot,
                                tehsil_slot,
                                location_hint,
                                contact_f,
                                notes_f,
                            ],
                            spacing=12,
                        ),
                    ),
                ),

                ft.Container(height=20),
                submit_btn,
                ft.Container(height=40),
            ],
        ),
    )

    # ================================================================
    #  TAB 2 — MY REQUESTS
    # ================================================================
    requests_col = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # Cache of request_id -> latest donation row. Populated by
    # load_my_requests() and consulted by both the card and the
    # detail dialog so the UI never has to trust blood_requests.status
    # alone to know whether a donation already happened.
    donations_by_request: dict = {}

    # Requests fetched from the DB are cached here so switching between
    # the Active/History pills below just re-filters in memory instead
    # of re-querying Supabase every tap.
    _my_requests_cache: list = []
    _my_req_mode = ["active"]  # "active" | "history"

    HISTORY_STATUSES = ("fulfilled", "cancelled", "expired")

    def _is_history_req(req: dict) -> bool:
        # A request only counts as "history" once it's actually closed
        # out (fulfilled/cancelled/expired). A donation being active but
        # not yet marked fulfilled has status "in_progress" and stays
        # in Active — it still needs the requester's attention.
        return req.get("status") in HISTORY_STATUSES

    def _switch_my_req_mode(mode: str):
        _my_req_mode[0] = mode
        if mode == "active":
            my_req_active_btn.bgcolor = PRIMARY
            my_req_active_btn.content.color = "white"
            my_req_history_btn.bgcolor = PRIMARY_LT
            my_req_history_btn.content.color = PRIMARY
        else:
            my_req_active_btn.bgcolor = PRIMARY_LT
            my_req_active_btn.content.color = PRIMARY
            my_req_history_btn.bgcolor = PRIMARY
            my_req_history_btn.content.color = "white"
        _render_my_requests()
        page.update()

    my_req_active_btn = ft.Container(
        expand=True, height=36, border_radius=10,
        bgcolor=PRIMARY, alignment=ft.Alignment(0, 0),
        content=ft.Text("Active | جاری", size=12, color="white", weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_my_req_mode("active"),
    )
    my_req_history_btn = ft.Container(
        expand=True, height=36, border_radius=10,
        bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
        content=ft.Text("History | سابقہ", size=12, color=PRIMARY, weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_my_req_mode("history"),
    )
    my_req_mode_bar = ft.Container(
        padding=ft.padding.only(bottom=10),
        content=ft.Row([my_req_active_btn, ft.Container(width=8), my_req_history_btn], spacing=0),
    )

    def load_my_requests():
        async def _work():
            try:
                await _restore_session()
                uid = sess_get("user_id")
                if not uid:
                    return

                def _fetch():
                    return (
                        _sb.table("blood_requests")
                        .select("*")
                        .eq("requested_by", uid)
                        .order("created_at", desc=True)
                        .limit(20)
                        .execute()
                    )

                res = await asyncio.to_thread(_fetch)
                data = res.data or []
                _my_requests_cache[:] = data

                req_ids = [r.get("id") for r in data if r.get("id") is not None]
                donations_by_request.clear()
                if req_ids:
                    def _fetch_donations():
                        return (
                            _sb.table("donations")
                            .select("*")
                            .in_("request_id", req_ids)
                            .order("donated_at", desc=True)
                            .execute()
                        )
                    don_res = await asyncio.to_thread(_fetch_donations)
                    for d in (don_res.data or []):
                        rid = d.get("request_id")
                        if rid not in donations_by_request:
                            donations_by_request[rid] = d

                _render_my_requests()

            except Exception as ex:
                print(f"[REQ] load error: {ex}")

        page.run_task(_work)

    def _render_my_requests():
        """Filters the cached requests into Active vs History (fulfilled/
        cancelled/expired) based on the currently selected pill, and
        rebuilds requests_col. Pure in-memory — no DB round-trip."""
        mode = _my_req_mode[0]
        data = [
            r for r in _my_requests_cache
            if _is_history_req(r) == (mode == "history")
        ]

        requests_col.controls.clear()

        if not data:
            empty_msg = (
                ("🗂️", "کوئی سابقہ درخواست نہیں\nNo history yet")
                if mode == "history" else
                ("🩸", "کوئی جاری درخواست نہیں\nNo active requests")
            )
            empty_children = [
                ft.Text(empty_msg[0], size=36),
                ft.Text(empty_msg[1], size=13, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
            ]
            if mode == "active":
                empty_children += [
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "🩸 Request Blood | درخواست دیں",
                        style=ft.ButtonStyle(
                            bgcolor=PRIMARY, color="white",
                            shape=ft.RoundedRectangleBorder(radius=12),
                        ),
                        on_click=lambda e: _go_tab(0),
                    ),
                ]
            requests_col.controls.append(
                ft.Container(
                    padding=ft.padding.all(24),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column(
                        empty_children,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                )
            )
        else:
            for req in data:
                requests_col.controls.append(_build_request_card(req))

        try:
            page.update()
        except Exception:
            pass

    def _donation_active(req: dict) -> bool:
        """True when a donation row exists for this request and the
        request hasn't already been closed out (fulfilled/cancelled/
        expired). This is the source of truth for 'should the requester
        see Mark Fulfilled', independent of a possibly-stale status."""
        if req.get("status") in ("fulfilled", "cancelled", "expired"):
            return False
        return req.get("id") in donations_by_request

    def _build_request_card(req: dict) -> ft.Control:
        status = req.get("status", "pending")
        urgency = req.get("urgency", "medium")
        donation_active = _donation_active(req)

        status_colors = {
            "pending":     ("#FFF3E0", "#B26A00"),
            "matching":    ("#E3F2FD", "#1565C0"),
            "in_progress": ("#EDE7F6", "#5E35B1"),
            "fulfilled":   ("#E8F5E9", "#2E7D32"),
            "cancelled":   ("#F0F0F0", "#757575"),
            "expired":     ("#F0F0F0", "#757575"),
        }
        status_labels = {
            "pending":     "⏳ Pending",
            "matching":    "🔍 Matching",
            "in_progress": "✅ Donor Found",
            "fulfilled":   "🎉 Fulfilled",
            "cancelled":   "❌ Cancelled",
            "expired":     "⌛ Expired",
        }

        if donation_active and status != "fulfilled":
            bg, tc = "#E8F5E9", "#2E7D32"
            status_label = "🎉 Donated — Confirm"
        else:
            bg, tc = status_colors.get(status, ("#412402", "#FAC775"))
            status_label = status_labels.get(status, status.capitalize())

        urgency_emoji = {
            "low": "🟢", "medium": "🟡",
            "high": "🔴", "critical": "🚨",
        }.get(urgency, "📌")

        def _on_tap(e, r=req):
            _show_request_detail(r)

        return ft.Container(
            width=W,
            bgcolor=SURFACE,
            padding=ft.padding.all(14),
            border_radius=16,
            shadow=ft.BoxShadow(blur_radius=10, color="#50000000", offset=ft.Offset(0, 2)),
            on_click=_on_tap,
            content=ft.Row(
                [
                    ft.Container(
                        width=48, height=48,
                        border_radius=24,
                        bgcolor=PRIMARY_LT,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            req.get("required_blood_group") or req.get("blood_group", "?"),
                            size=14, weight=ft.FontWeight.BOLD, color=PRIMARY,
                        ),
                    ),
                    ft.Container(width=10),
                    ft.Column(
                        [
                            ft.Text(
                                f"{urgency_emoji} {req.get('patient_name', 'Patient')}",
                                size=14, weight=ft.FontWeight.W_700, color=TEXT,
                            ),
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.LOCATION_ON_ROUNDED, size=12, color=TEXT_SUB),
                                    ft.Text(
                                        f"{req.get('city', '')} {req.get('tehsil') or ''}".strip(),
                                        size=12, color=TEXT_SUB,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=3, expand=True, tight=True,
                    ),
                    ft.Container(
                        content=ft.Text(status_label, size=10, weight=ft.FontWeight.W_700, color=tc),
                        bgcolor=bg,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=8,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _show_request_detail(req: dict):
        async def _open():
            status = req.get("status", "pending")
            donation_active = _donation_active(req)
            donation_row = donations_by_request.get(req.get("id"))

            def _close(e=None):
                try:
                    dlg.open = False
                    page.close(dlg)
                    page.update()
                except Exception:
                    pass

            def _mark_fulfilled(e=None):
                async def _do():
                    try:
                        def _update():
                            _sb.table("blood_requests").update(
                                {"status": "fulfilled"}
                            ).eq("id", req["id"]).execute()
                        await asyncio.to_thread(_update)
                        snack("✅ Request marked as fulfilled!", GREEN)
                        _close()
                        load_my_requests()

                        d = donation_row
                        if not d:
                            def _fetch_donation():
                                return (
                                    _sb.table("donations")
                                    .select("*")
                                    .eq("request_id", req["id"])
                                    .order("donated_at", desc=True)
                                    .limit(1)
                                    .execute()
                                )
                            don_res = await asyncio.to_thread(_fetch_donation)
                            don_rows = don_res.data or []
                            d = don_rows[0] if don_rows else None

                        if d:
                            show_feedback_dialog(
                                page=page,
                                donation_id=d.get("id"),
                                request_id=req["id"],
                                donor_id=d.get("donor_id", ""),
                                requester_id=d.get("requester_id", ""),
                                blood_group=req.get("required_blood_group") or req.get("blood_group", "?"),
                                is_donor=False,
                                on_done=load_my_requests,
                            )
                        else:
                            print(f"[REQ] no donation row found for request_id={req['id']}, skipping feedback dialog")
                    except Exception as ex:
                        snack(f"Error: {ex}")
                page.run_task(_do)

            def _cancel_request(e=None):
                async def _do():
                    try:
                        def _update():
                            _sb.table("blood_requests").update(
                                {"status": "cancelled"}
                            ).eq("id", req["id"]).execute()
                        await asyncio.to_thread(_update)
                        snack("Request cancelled.", TEXT_SUB)
                        _close()
                        load_my_requests()
                    except Exception as ex:
                        snack(f"Error: {ex}")
                page.run_task(_do)

            display_status = "fulfilled" if (donation_active and status != "fulfilled") else status

            rows = [
                ("🩸 Blood Group", req.get("required_blood_group") or req.get("blood_group", "-")),
                ("👤 Patient",     req.get("patient_name", "-")),
                ("🏥 Hospital",    req.get("hospital", "-")),
                ("📍 Location",    f"{req.get('city', '')} — {req.get('tehsil') or req.get('province', '')}"),
                ("📞 Contact",     req.get("contact", "-")),
                ("⚡ Urgency",     URGENCY_LABELS.get(req.get("urgency", "medium"), "-")),
                ("📊 Status",      display_status.upper()),
            ]

            content_rows = []
            for label, value in rows:
                content_rows.append(
                    ft.Row(
                        [
                            ft.Text(label, size=12, color=TEXT_SUB, width=110),
                            ft.Text(str(value), size=13, weight=ft.FontWeight.W_600, color=TEXT, expand=True),
                        ],
                        spacing=8,
                    )
                )
                content_rows.append(ft.Divider(height=1, color=PRIMARY_MD))

            if donation_active and status != "fulfilled":
                content_rows.append(
                    ft.Container(
                        bgcolor="#E8F5E9",
                        padding=ft.padding.all(10),
                        border_radius=8,
                        content=ft.Text(
                            "🎉 A donor has already donated for this request. "
                            "Tap Mark Fulfilled below to close it out.",
                            size=12, color="#2E7D32",
                        ),
                    )
                )

            if req.get("notes"):
                content_rows.append(
                    ft.Container(
                        bgcolor=PRIMARY_LT,
                        padding=ft.padding.all(10),
                        border_radius=8,
                        content=ft.Text(
                            f"📝 {req['notes']}", size=12, color=PRIMARY_DK,
                        ),
                    )
                )

            actions = [ft.TextButton("Close | بند کریں", on_click=_close)]

            if status == "in_progress" or donation_active:
                actions.insert(0, ft.ElevatedButton(
                    "🎉 Mark Fulfilled | مکمل ہوا",
                    style=ft.ButtonStyle(bgcolor=GREEN, color="white",
                                          shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=_mark_fulfilled,
                ))

            if status == "pending" and not donation_active:
                actions.insert(0, ft.TextButton(
                    "❌ Cancel",
                    style=ft.ButtonStyle(color=TEXT_SUB),
                    on_click=_cancel_request,
                ))

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Request Details | تفصیلات", weight=ft.FontWeight.BOLD, size=15, color=PRIMARY),
                content=ft.Container(
                    width=320,
                    content=ft.Column(content_rows, spacing=6, tight=True, scroll=ft.ScrollMode.AUTO),
                ),
                actions=actions,
                actions_alignment=ft.MainAxisAlignment.END,
            )

            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            page.update()

        page.run_task(_open)

    my_requests_tab = ft.Container(
        padding=ft.padding.symmetric(horizontal=20, vertical=16),
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            controls=[
                ft.Container(height=12),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.HISTORY_ROUNDED, color=PRIMARY, size=20),
                        ft.Text(
                            "My Requests | میری درخواستیں",
                            size=16, weight=ft.FontWeight.BOLD, color=TEXT,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=10),
                my_req_mode_bar,
                requests_col,
                ft.Container(height=40),
            ],
        ),
    )

    # ================================================================
    #  TAB BAR + TAB VIEW
    #  Flet 0.84/0.85: TabBar and TabBarView are children of a single
    #  parent ft.Tabs control. selected_index / length / on_change all
    #  live on ft.Tabs — NOT on TabBar or TabBarView individually.
    # ================================================================
    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label=ft.Text("🩸 Request Blood")),
            ft.Tab(label=ft.Text("📋 My Requests")),
        ],
        indicator_color=PRIMARY,
        label_color=PRIMARY,
        unselected_label_color=TEXT_SUB,
    )

    tab_view = ft.TabBarView(
        controls=[request_form_tab, my_requests_tab],
        expand=True,
    )

    def _on_tabs_change(e):
        idx = e.control.selected_index
        if idx == 1:
            load_my_requests()
        page.update()

    tabs_ctrl = ft.Tabs(
        length=2,
        selected_index=0,
        on_change=_on_tabs_change,
        expand=True,
        content=ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(bgcolor=SURFACE, content=tab_bar),
                ft.Container(expand=True, content=tab_view),
            ],
        ),
    )

    # Initial load so "My Requests" isn't empty if the user swipes
    # straight to it without tapping the tab header first.
    load_my_requests()

    # ================================================================
    #  BUILD UI
    # ================================================================
    return ft.View(
        route="/request",
        bgcolor=BG,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/"),
            ),
            title=ft.Column(
                [
                    ft.Text("Blood Request", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("خون کی درخواست", size=11, color=PRIMARY_MD),
                ],
                spacing=0,
            ),
            bgcolor=PRIMARY,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.REFRESH_ROUNDED,
                    icon_color="white",
                    tooltip="Refresh | تازہ کریں",
                    on_click=lambda e: load_my_requests(),
                ),
            ],
        ),
        controls=[
            tabs_ctrl,
        ],
    )



