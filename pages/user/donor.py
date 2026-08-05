# ================================================================
#  pages/user/donor.py  —  Donor Page + Response System
#  Flet 0.84 compatible | Session-safe | Auto-notifications
# ================================================================
import pyperclip
import asyncio
import flet as ft
from typing import Optional
from supabase import create_client
import pages.user.feedback as feedback_page
from services.database.db import supabase, SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options
from core.theme import Theme 
BLOOD_COLORS = {
    "A+":  "#E53935", "A-":  "#C62828",
    "B+":  "#1565C0", "B-":  "#0D47A1",
    "AB+": "#6A1B9A", "AB-": "#4A148C",
    "O+":  "#2E7D32", "O-":  "#1B5E20",
}

PRIMARY    = "#C62828"
PRIMARY_LT = "#FFEBEE"
PRIMARY_MD = "#FFCDD2"
PRIMARY_DK = "#B71C1C"
GREEN      = "#2E7D32"
GREEN_LT   = "#E8F5E9"
BLUE       = "#1565C0"
ORANGE     = "#E65100"
BG         = "#FFF5F5"
TEXT       = "#212121"
TEXT_SUB   = "#757575"
SURFACE    = "#FFFFFF"

# Standard inter-donation gap (days) used to auto-compute availability
# from a donor's last_donation_date — no manual toggle/form needed.
DONATION_COOLDOWN_DAYS = 90


def _compute_availability(last_donation_date) -> bool:
    """A profile is donor-available if they've never donated, or it's
    been >= DONATION_COOLDOWN_DAYS since their last donation."""
    if not last_donation_date:
        return True
    try:
        import datetime as _dt
        d = _dt.date.fromisoformat(str(last_donation_date)[:10])
        return (_dt.date.today() - d).days >= DONATION_COOLDOWN_DAYS
    except Exception:
        return True


def _next_available_date(last_donation_date):
    """Returns an ISO date string for when this person becomes eligible
    again, or None if they're already available / never donated."""
    if not last_donation_date:
        return None
    try:
        import datetime as _dt
        d = _dt.date.fromisoformat(str(last_donation_date)[:10])
        nxt = d + _dt.timedelta(days=DONATION_COOLDOWN_DAYS)
        return nxt.isoformat() if nxt > _dt.date.today() else None
    except Exception:
        return None


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

    # head_admin sees every district always — the "same district"
    # filter below is only meaningful for regular members/admins.
    role = sess_get("role", "member")
    is_head_admin = role == "head_admin"

    async def _restore_session():
        try:
            at = sess_get("access_token")
            rt = sess_get("refresh_token", "")
            if at:
                await asyncio.to_thread(_sb.auth.set_session, at, rt)
        except Exception as ex:
            print(f"[DONOR] session restore error: {ex}")

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

    # ── State ───────────────────────────────────────────────
    state = {
        "donors":         [],
        "filtered":       [],
        "my_requests":    [],   # requests jahan donor match hai
        "my_responses":   [],   # donor ki past responses
        "is_donor":       False,
        "is_available":   False,
        "my_blood_group": "",
        "my_city":        "",
        "my_member_id":   None, # 🟢 Members table ki primary key ke liye
        "stats": {"total": 0, "available": 0, "cities": 0},
    }

    # ================================================================
    #  TAB SYSTEM
    # ================================================================
    selected_tab = [0]  # 0=All Donors, 1=My Requests (donor view)

    tab_all_btn = ft.Container(
        expand=True, height=40, border_radius=10,
        bgcolor=PRIMARY, alignment=ft.Alignment(0, 0),
        content=ft.Text("All Donors | تمام ڈونرز", size=12,
                        color="white", weight=ft.FontWeight.W_600),
        on_click=lambda e: switch_tab(0),
    )
    tab_req_btn = ft.Container(
        expand=True, height=40, border_radius=10,
        bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
        content=ft.Text("Blood Requests | درخواستیں", size=12,
                        color=PRIMARY, weight=ft.FontWeight.W_600),
        on_click=lambda e: switch_tab(1),
    )

    tab_bar = ft.Container(
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        bgcolor=SURFACE,
        content=ft.Row([tab_all_btn, ft.Container(width=8), tab_req_btn], spacing=0),
    )

    def switch_tab(idx: int):
        selected_tab[0] = idx
        if idx == 0:
            tab_all_btn.bgcolor = PRIMARY
            tab_all_btn.content.color = "white"
            tab_req_btn.bgcolor = PRIMARY_LT
            tab_req_btn.content.color = PRIMARY
            all_donors_col.visible = True
            requests_col.visible = False
        else:
            tab_all_btn.bgcolor = PRIMARY_LT
            tab_all_btn.content.color = PRIMARY
            tab_req_btn.bgcolor = PRIMARY
            tab_req_btn.content.color = "white"
            all_donors_col.visible = False
            requests_col.visible = True
        page.update()

    # ================================================================
    #  STATS BAR
    # ================================================================
    stat_total     = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=PRIMARY)
    stat_available = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=GREEN)
    stat_cities    = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=BLUE)

    def _stat_col(val_ctrl, label, icon, color):
        return ft.Column([
            ft.Row([ft.Icon(icon, color=color, size=14), val_ctrl],
                   spacing=4, alignment=ft.MainAxisAlignment.CENTER),
            ft.Text(label, size=9, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

    stats_bar = ft.Container(
        bgcolor=SURFACE,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        shadow=ft.BoxShadow(blur_radius=6, color=PRIMARY_MD, offset=ft.Offset(0, 2)),
        content=ft.Row([
            _stat_col(stat_total,     "Total\nکل",      ft.Icons.PEOPLE_ROUNDED,  PRIMARY),
            ft.VerticalDivider(width=1, color=PRIMARY_MD),
            _stat_col(stat_available, "Available\nدستیاب", ft.Icons.CHECK_CIRCLE, GREEN),
            ft.VerticalDivider(width=1, color=PRIMARY_MD),
            _stat_col(stat_cities,    "Cities\nشہر",    ft.Icons.LOCATION_CITY,   BLUE),
        ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
    )

    # ================================================================
    #  AVAILABILITY TOGGLE (for donors)
    # ================================================================
    avail_toggle_text = ft.Text("", size=12, color=TEXT_SUB)
    avail_toggle = ft.Switch(
        value=False,
        active_color=GREEN,
        inactive_thumb_color=TEXT_SUB,
        on_change=lambda e: _toggle_availability(e.control.value),
    )
    avail_row = ft.Container(
        visible=False,
        bgcolor=GREEN_LT,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        margin=ft.margin.symmetric(horizontal=14, vertical=4),
        content=ft.Row([
            ft.Icon(ft.Icons.VOLUNTEER_ACTIVISM, color=GREEN, size=20),
            ft.Column([
                ft.Text("My Availability | میری دستیابی", size=13,
                        weight=ft.FontWeight.W_700, color=GREEN),
                avail_toggle_text,
            ], spacing=2, expand=True, tight=True),
            avail_toggle,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    def _toggle_availability(val: bool):
        async def _do():
            try:
                uid = sess_get("user_id")
                if not uid:
                    return
                await _restore_session()

                def _update():
                    _sb.table("members").update(
                        {"is_available": val}
                    ).eq("id", uid).execute()

                await asyncio.to_thread(_update)
                state["is_available"] = val
                avail_toggle_text.value = "دستیاب ہوں ✅" if val else "ابھی دستیاب نہیں ⛔"
                avail_toggle_text.color = GREEN if val else TEXT_SUB
                snack(
                    "✅ You are now available for donation!" if val else "⛔ Marked as unavailable.",
                    GREEN if val else TEXT_SUB,
                )
                page.update()
            except Exception as ex:
                print(f"[DONOR] toggle error: {ex}")
        page.run_task(_do)

    # ================================================================
    #  FILTER FIELDS
    # ================================================================
    blood_filter = ft.Dropdown(
        label="Blood Group",
        width=130, border_radius=12,
        focused_border_color=PRIMARY, border_color="#BDBDBD",
        text_size=12,
        options=[ft.dropdown.Option("All")] +
                [ft.dropdown.Option(g) for g in ["A+","A-","B+","B-","AB+","AB-","O+","O-"]],
        value="All",
        on_select=lambda e: apply_filter(),
    )
    city_filter = ft.TextField(
        label="City | شہر",
        prefix_icon=ft.Icons.SEARCH,
        width=140, border_radius=12,
        focused_border_color=PRIMARY, border_color="#BDBDBD",
        text_size=12,
        on_change=lambda e: apply_filter(),
    )
    avail_filter = ft.Checkbox(
        label="Available\nصرف دستیاب",
        value=False, active_color=PRIMARY,
        label_style=ft.TextStyle(size=10, color="#616161"),
        on_change=lambda e: apply_filter(),
    )
    # Same-district matching for donors/requesters — on by default for
    # everyone except head_admin, who always sees every district (per
    # head_admin's full-access role) so the control is hidden for them.
    same_district_filter = ft.Checkbox(
        label="My District\nصرف میرا ضلع",
        value=not is_head_admin,
        visible=not is_head_admin,
        active_color=PRIMARY,
        label_style=ft.TextStyle(size=10, color="#616161"),
        on_change=lambda e: apply_filter(),
    )

    # ================================================================
    #  ALL DONORS LIST
    # ================================================================
    donor_list_col = ft.Column(spacing=6)
    all_donors_col = ft.Column(
        [
            ft.Container(
                bgcolor=SURFACE,
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                content=ft.Row([blood_filter, city_filter, avail_filter, same_district_filter],
                               alignment=ft.MainAxisAlignment.CENTER, spacing=8, wrap=True,
                               run_spacing=8),
            ),
            donor_list_col,
        ],
        spacing=0,
        visible=True,
    )

    def apply_filter():
        blood = blood_filter.value or "All"
        city_q = (city_filter.value or "").strip().lower()
        avail_only = avail_filter.value
        same_district_only = (not is_head_admin) and bool(same_district_filter.value)
        my_city = (state.get("my_city") or "").strip().lower()
        filtered = [
            d for d in state["donors"]
            if (blood == "All" or d.get("blood_group") == blood)
            and (not city_q or city_q in (d.get("city") or "").lower())
            and (not avail_only or d.get("is_available") is True)
            and (not same_district_only or not my_city or (d.get("city") or "").strip().lower() == my_city)
        ]
        state["filtered"] = filtered
        _build_donor_list(filtered)

    def _build_donor_list(donors: list):
        if not donors:
            donor_list_col.controls = [
                ft.Container(
                    padding=ft.padding.all(40),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column([
                        ft.Icon(ft.Icons.PERSON_SEARCH, size=60, color=PRIMARY_MD),
                        ft.Text("No donors found | کوئی ڈونر نہیں ملا",
                                size=13, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                )
            ]
        else:
            donor_list_col.controls = [_donor_card(d) for d in donors]
        try:
            page.update()
        except Exception:
            pass

    def _donor_card(donor: dict) -> ft.Control:
        name      = donor.get("full_name", "---")
        blood     = donor.get("blood_group", "?")
        city      = donor.get("city", "---")
        available = donor.get("is_available", True)
        donated   = donor.get("total_donations")
        last_don  = donor.get("last_donation")
        next_avail = donor.get("next_available")
        bc        = BLOOD_COLORS.get(blood, PRIMARY)
        initials  = (name[0] + (name.split()[-1][0] if len(name.split()) > 1 else "")).upper()

        if last_don:
            donated_text = f"Last donated: {last_don} | آخری عطیہ"
        else:
            donated_text = "Never donated yet | ابھی تک عطیہ نہیں کیا"

        availability_note = None
        if not available and next_avail:
            availability_note = f"Available again on {next_avail} | اس تاریخ کو دوبارہ دستیاب"

        return ft.Container(
            bgcolor=SURFACE, border_radius=16,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(14),
            shadow=ft.BoxShadow(blur_radius=8, color=PRIMARY_MD if available else "#EEEEEE",
                                offset=ft.Offset(0, 3)),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        width=50, height=50, border_radius=25, bgcolor=bc,
                        opacity=1.0 if available else 0.4,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(initials, size=17, color="white",
                                        weight=ft.FontWeight.BOLD),
                    ),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Row([
                            ft.Text(name, size=14, weight=ft.FontWeight.W_700,
                                    color=TEXT, expand=True,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=7, vertical=3),
                                border_radius=8,
                                bgcolor=GREEN_LT if available else "#FAFAFA",
                                content=ft.Text(
                                    "دستیاب ✅" if available else "مصروف ⛔",
                                    size=9, color=GREEN if available else TEXT_SUB,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                        ]),
                        ft.Row([
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                border_radius=8, bgcolor=f"{bc}22",
                                content=ft.Text(f"🩸 {blood}", size=11, color=bc,
                                                weight=ft.FontWeight.BOLD),
                            ),
                            ft.Row([
                                ft.Icon(ft.Icons.LOCATION_ON, size=12, color=TEXT_SUB),
                                ft.Text(city, size=11, color=TEXT_SUB),
                            ], spacing=2, tight=True),
                            ft.Text(f"💉 {donated}x" if donated else "",
                                    size=10, color=TEXT_SUB),
                        ], spacing=8),
                    ], expand=True, spacing=4),
                ]),
                ft.Container(
                    margin=ft.margin.only(top=8),
                    content=ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_MONTH, size=12, color=TEXT_SUB),
                        ft.Text(donated_text, size=10, color=TEXT_SUB, expand=True),
                    ], spacing=4),
                ),
                ft.Container(
                    visible=availability_note is not None,
                    margin=ft.margin.only(top=2),
                    content=ft.Row([
                        ft.Icon(ft.Icons.SCHEDULE, size=12, color=ORANGE),
                        ft.Text(availability_note or "", size=10, color=ORANGE, expand=True),
                    ], spacing=4),
                ),
                ft.Container(
                    margin=ft.margin.only(top=10),
                    content=ft.Row([
                        ft.OutlinedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.PHONE, size=14, color=PRIMARY),
                                ft.Text("Contact", size=12, color=PRIMARY),
                            ], spacing=6),
                            style=ft.ButtonStyle(
                                side=ft.BorderSide(1, PRIMARY_MD),
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                            expand=True,
                            on_click=lambda _, d=donor: _show_contact(d),
                        ),
                        ft.Container(width=8),
                        ft.OutlinedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.CHAT, size=14, color=GREEN),
                                ft.Text("WhatsApp", size=12, color=GREEN),
                            ], spacing=6),
                            style=ft.ButtonStyle(
                                side=ft.BorderSide(1, "#A5D6A7"),
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                            expand=True,
                            on_click=lambda _, d=donor: _open_whatsapp(d),
                        ),
                    ]),
                ),
            ], spacing=0),
        )

    # ================================================================
    #  BLOOD REQUESTS TAB (Donor Response System)
    # ================================================================
    requests_col = ft.Column(spacing=0, visible=False)
    req_list_col = ft.Column(spacing=10)

    # Active vs History split — same idea as request.py's My Requests
    # tab. "History" = requests that are closed out (fulfilled/
    # cancelled/expired) OR ones this donor already finished acting on
    # (declined, or donated). Everything else still needs attention.
    _donor_req_mode = ["active"]
    DONOR_HISTORY_REQ_STATUSES = ("fulfilled", "cancelled", "expired")
    DONOR_HISTORY_RESPONSE_STATUSES = ("declined", "donated")

    def _is_history_request(req: dict) -> bool:
        if req.get("status") in DONOR_HISTORY_REQ_STATUSES:
            return True
        req_id = req.get("id")
        my_response = next(
            (r for r in state.get("my_responses", []) if r.get("request_id") == req_id),
            None,
        )
        return bool(my_response) and my_response.get("status") in DONOR_HISTORY_RESPONSE_STATUSES

    def _switch_donor_req_mode(mode: str):
        _donor_req_mode[0] = mode
        if mode == "active":
            donor_req_active_btn.bgcolor = PRIMARY
            donor_req_active_btn.content.color = "white"
            donor_req_history_btn.bgcolor = PRIMARY_LT
            donor_req_history_btn.content.color = PRIMARY
        else:
            donor_req_active_btn.bgcolor = PRIMARY_LT
            donor_req_active_btn.content.color = PRIMARY
            donor_req_history_btn.bgcolor = PRIMARY
            donor_req_history_btn.content.color = "white"
        _build_requests_tab()

    donor_req_active_btn = ft.Container(
        expand=True, height=36, border_radius=10,
        bgcolor=PRIMARY, alignment=ft.Alignment(0, 0),
        content=ft.Text("Active | جاری", size=12, color="white", weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_donor_req_mode("active"),
    )
    donor_req_history_btn = ft.Container(
        expand=True, height=36, border_radius=10,
        bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
        content=ft.Text("History | سابقہ", size=12, color=PRIMARY, weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_donor_req_mode("history"),
    )
    donor_req_mode_bar = ft.Container(
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        content=ft.Row([donor_req_active_btn, ft.Container(width=8), donor_req_history_btn], spacing=0),
    )

    def _build_requests_tab():
        mode = _donor_req_mode[0]
        all_reqs = state.get("my_requests", [])
        requests = [r for r in all_reqs if _is_history_request(r) == (mode == "history")]
        req_list_col.controls.clear()

        if not requests:
            empty_msg = (
                "کوئی سابقہ درخواست نہیں\nNo history yet" if mode == "history"
                else "آپ کے علاقے میں کوئی جاری درخواست نہیں\nNo active matching requests"
            )
            req_list_col.controls.append(
                ft.Container(
                    padding=ft.padding.all(40),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column([
                        ft.Text("🗂️" if mode == "history" else "🩸", size=48),
                        ft.Text(empty_msg, size=13, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                )
            )
        else:
            for req in requests:
                req_list_col.controls.append(_request_card(req))

        count_label = (
            f"🗂️ {len(requests)} past request(s)" if mode == "history"
            else f"🩸 {len(requests)} matching request(s) in your area"
        )
        requests_col.controls = [
            donor_req_mode_bar,
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                content=ft.Text(count_label, size=13, color=PRIMARY, weight=ft.FontWeight.W_600),
            ),
            req_list_col,
            ft.Container(height=40),
        ]
        try:
            page.update()
        except Exception:
            pass

    def _request_card(req: dict) -> ft.Control:
        blood    = req.get("required_blood_group") or req.get("blood_group", "?")
        patient  = req.get("patient_name", "Patient")
        hospital = req.get("hospital", "")
        city     = req.get("city", "")
        tehsil   = req.get("tehsil") or ""
        urgency  = req.get("urgency", "medium")
        req_id   = req.get("id")

        urgency_colors = {
            "low":      ("#E8F5E9", GREEN,   "🟢"),
            "medium":   ("#FFF8E1", "#F57F17", "🟡"),
            "high":     ("#FFF3E0", ORANGE,  "🔴"),
            "critical": ("#FFEBEE", PRIMARY, "🚨"),
        }
        bg_u, tc_u, em_u = urgency_colors.get(urgency, ("#FFF8E1", ORANGE, "📌"))

        # Check existing response
        my_response = next(
            (r for r in state.get("my_responses", []) if r.get("request_id") == req_id),
            None,
        )
        response_status = my_response.get("status") if my_response else None
        req_status = req.get("status")
        is_closed_req = req_status in DONOR_HISTORY_REQ_STATUSES

        def _accept(e, r=req):
            _respond_to_request(r, "accepted")

        def _decline(e, r=req):
            _show_decline_dialog(r)

        def _mark_donated(e, r=req):
            _confirm_donation(r)

        if is_closed_req and response_status not in ("donated", "declined"):
            # Request was closed out (fulfilled/cancelled/expired) without
            # this donor ever confirming a donation — e.g. someone else
            # donated, or the requester cancelled/it expired. Show the
            # true outcome instead of a stale Accept/Decline/Mark Donated.
            closed_labels = {
                "fulfilled": ("🎉 Fulfilled by another donor", GREEN, GREEN_LT),
                "cancelled": ("❌ Request was cancelled", TEXT_SUB, "#FAFAFA"),
                "expired":   ("⌛ Request expired", TEXT_SUB, "#FAFAFA"),
            }
            label, fg, bg = closed_labels.get(req_status, (f"Closed: {req_status}", TEXT_SUB, "#FAFAFA"))
            action_row = ft.Container(
                height=36, border_radius=10, bgcolor=bg,
                alignment=ft.Alignment(0, 0),
                content=ft.Text(label, size=11, color=fg, weight=ft.FontWeight.W_600),
            )
        elif response_status == "accepted":
            action_row = ft.Row([
                ft.Container(
                    expand=True, height=40, border_radius=10,
                    bgcolor=GREEN_LT, alignment=ft.Alignment(0, 0),
                    content=ft.Text("✅ Accepted — Contact Requester",
                                    size=11, color=GREEN, weight=ft.FontWeight.W_600),
                ),
                ft.Container(width=8),
                ft.OutlinedButton(
                    "🎉 Donated",
                    style=ft.ButtonStyle(
                        side=ft.BorderSide(1, GREEN),
                        shape=ft.RoundedRectangleBorder(radius=10),
                        color=GREEN,
                    ),
                    on_click=_mark_donated,
                ),
            ])
        elif response_status == "declined":
            action_row = ft.Container(
                height=36, border_radius=10, bgcolor="#FAFAFA",
                alignment=ft.Alignment(0, 0),
                content=ft.Text("❌ You declined this request",
                                size=11, color=TEXT_SUB),
            )
        elif response_status == "donated":
            action_row = ft.Container(
                height=36, border_radius=10, bgcolor=GREEN_LT,
                alignment=ft.Alignment(0, 0),
                content=ft.Text("🎉 Donation Confirmed — JazakAllah!",
                                size=11, color=GREEN, weight=ft.FontWeight.W_600),
            )
        else:
            action_row = ft.Row([
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.FAVORITE, size=14, color="white"),
                        ft.Text("Accept | قبول کریں", size=12, color="white"),
                    ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                    style=ft.ButtonStyle(
                        bgcolor=GREEN,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    expand=True, height=42,
                    on_click=_accept,
                ),
                ft.Container(width=8),
                ft.OutlinedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CLOSE, size=14, color=TEXT_SUB),
                        ft.Text("Decline | انکار", size=12, color=TEXT_SUB),
                    ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                    style=ft.ButtonStyle(
                        side=ft.BorderSide(1, "#BDBDBD"),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    expand=True, height=42,
                    on_click=_decline,
                ),
            ])

        bc = BLOOD_COLORS.get(blood, PRIMARY)

        return ft.Container(
            bgcolor=SURFACE, border_radius=16,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(14),
            shadow=ft.BoxShadow(blur_radius=8, color="#15000000", offset=ft.Offset(0, 2)),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        width=52, height=52, border_radius=26,
                        bgcolor=f"{bc}22", alignment=ft.Alignment(0, 0),
                        content=ft.Text(blood, size=14,
                                        weight=ft.FontWeight.BOLD, color=bc),
                    ),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(f"👤 {patient}", size=14,
                                weight=ft.FontWeight.W_700, color=TEXT),
                        ft.Row([
                            ft.Icon(ft.Icons.LOCAL_HOSPITAL, size=12, color=TEXT_SUB),
                            ft.Text(hospital, size=11, color=TEXT_SUB,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                        ], spacing=4, tight=True),
                        ft.Row([
                            ft.Icon(ft.Icons.LOCATION_ON, size=12, color=TEXT_SUB),
                            ft.Text(f"{city} {tehsil}".strip(), size=11, color=TEXT_SUB),
                        ], spacing=4, tight=True),
                    ], expand=True, spacing=3, tight=True),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=8, bgcolor=bg_u,
                        content=ft.Text(f"{em_u} {urgency.upper()}",
                                        size=9, color=tc_u, weight=ft.FontWeight.BOLD),
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Container(height=10),
                action_row,
            ], spacing=0),
        )

    # ================================================================
    #  RESPOND TO REQUEST
    # ================================================================
    def _respond_to_request(req: dict, response: str, decline_reason: str = ""):
        async def _do():
            try:
                await _restore_session()
                uid       = sess_get("user_id")
                full_name = sess_get("full_name", "Donor")
                blood_grp = state.get("my_blood_group", "")
                
                # 🟢 State se member ki primary key uthaen, agar na ho tu uid backup ho
                final_donor_id = state.get("my_member_id") or uid 

                def _get_phone():
                    r = _sb.table("profiles").select("phone").eq("id", uid).limit(1).execute()
                    return r.data[0].get("phone", "") if r.data else ""

                phone = await asyncio.to_thread(_get_phone)
                req_id = req.get("id")

                def _upsert():
                    from datetime import datetime, timezone
                    payload = {
                        "request_id":       req_id,
                        "donor_id":         final_donor_id,  # 🟢 اب یہاں صحیح ممبر آئی ڈی جائے گی
                        "donor_name":       full_name,
                        "donor_phone":      phone,
                        "donor_blood_group": blood_grp,
                        "status":           response,
                        "responded_at":     datetime.now(timezone.utc).isoformat(),
                    }
                    if decline_reason:
                        payload["decline_reason"] = decline_reason
                    return (
                        _sb.table("donor_responses")
                        .upsert(payload, on_conflict="request_id,donor_id")
                        .execute()
                    )

                await asyncio.to_thread(_upsert)

                if response == "accepted":
                    def _update_req():
                        _sb.table("blood_requests").update(
                            {"status": "in_progress"}
                        ).eq("id", req_id).execute()
                    await asyncio.to_thread(_update_req)

                    requester_id = req.get("requested_by")
                    if requester_id:
                        from services.notifications import notify_requester_donor_accepted
                        await notify_requester_donor_accepted(
                            supabase_client=_sb,
                            requester_id=str(requester_id),
                            donor_name=full_name,
                            donor_phone=phone,
                            request_id=req_id,
                        )
                    snack("✅ Request accepted! Requester has been notified.", GREEN)

                elif response == "declined":
                    snack("Request declined.", TEXT_SUB)

                await _load_my_requests()
                _build_requests_tab()

            except Exception as ex:
                print(f"[DONOR] respond error: {ex}")
                snack(f"Error: {str(ex)[:60]}", PRIMARY)

        page.run_task(_do)

    # ================================================================
    #  DECLINE DIALOG
    # ================================================================
    def _show_decline_dialog(req: dict):
        reason_f = ft.TextField(
            label="Reason (optional) | وجہ",
            multiline=True, min_lines=2, max_lines=3,
            border_radius=12, focused_border_color=PRIMARY,
        )

        def _close(e=None):
            try:
                dlg.open = False
                page.update()
            except Exception:
                pass

        def _submit(e=None):
            _close()
            _respond_to_request(req, "declined", reason_f.value or "")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Decline Request | انکار کریں", weight=ft.FontWeight.BOLD, color=PRIMARY),
            content=ft.Container(
                width=300,
                content=ft.Column([
                    ft.Text("کیا آپ واقعی یہ درخواست رد کرنا چاہتے ہیں؟", size=13, color=TEXT_SUB),
                    ft.Container(height=8),
                    reason_f,
                ], spacing=4, tight=True),
            ),
            actions=[
                ft.TextButton("Cancel | واپس", on_click=_close),
                ft.ElevatedButton(
                    "Decline | انکار",
                    style=ft.ButtonStyle(bgcolor=PRIMARY, color="white", shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=_submit,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ================================================================
    #  CONFIRM DONATION
    # ================================================================
    def _confirm_donation(req: dict):
        async def _do():
            try:
                await _restore_session()
                uid       = sess_get("user_id")
                full_name = sess_get("full_name", "Donor")
                req_id    = req.get("id")
                
                final_donor_id = state.get("my_member_id") or uid

                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()

                def _update_response():
                    _sb.table("donor_responses").update(
                        {"status": "donated", "donated_at": now}
                    ).eq("request_id", req_id).eq("donor_id", final_donor_id).execute()

                await asyncio.to_thread(_update_response)

                def _insert_donation():
                    return _sb.table("donations").insert({
                        "request_id":          req_id,
                        "donor_id":            final_donor_id,
                        "requester_id":        req.get("requested_by"),
                        "donor_name":          full_name,
                        "requester_name":      req.get("requester_name", ""),
                        "blood_group":         req.get("required_blood_group") or req.get("blood_group", ""),
                        "units_donated":       req.get("units", 1),
                        "province":            req.get("province", ""),
                        "city":                req.get("city", ""),
                        "tehsil":              req.get("tehsil"),
                        "hospital_name":       req.get("hospital", ""),
                        "confirmed_by_donor":  True,
                        "donated_at":          now,
                    }).execute()

                donation_res = await asyncio.to_thread(_insert_donation)
                donation_row = donation_res.data[0] if donation_res.data else {}
                donation_id  = donation_row.get("id")

                def _update_req():
                    _sb.table("blood_requests").update(
                        {"status": "fulfilled", "fulfilled_at": now}
                    ).eq("id", req_id).execute()

                await asyncio.to_thread(_update_req)

                # Award badge
                await _check_and_award_badge(uid)

                snack("🎉 Donation Confirmed! JazakAllah.", GREEN)
                await _load_my_requests()
                _build_requests_tab()

                # Pop up the donor's own feedback form right after confirming
                if donation_id:
                    feedback_page.show_feedback_dialog(
                        page=page,
                        donation_id=donation_id,
                        request_id=req_id,
                        donor_id=final_donor_id,
                        requester_id=req.get("requested_by"),
                        blood_group=req.get("required_blood_group") or req.get("blood_group", ""),
                        is_donor=True,
                    )

            except Exception as ex:
                print(f"[DONOR] confirm donation error: {ex}")
                snack(f"Error: {str(ex)[:60]}", PRIMARY)

        page.run_task(_do)

    # ================================================================
    #  BADGE SYSTEM
    # ================================================================
    async def _check_and_award_badge(uid: str):
        try:
            def _get_count():
                from datetime import datetime, timezone
                r = _sb.table("profiles").select("total_donations").eq("id", uid).limit(1).execute()
                count = (r.data[0].get("total_donations") or 0) + 1 if r.data else 1
                _sb.table("profiles").update({
                    "last_donation_date": datetime.now(timezone.utc).isoformat(),
                    "total_donations":    count,
                }).eq("id", uid).execute()
                return count

            count = await asyncio.to_thread(_get_count)

            badges = {
                1:  ("first_drop", "First Drop 🌱",   "پہلا قطرہ 🌱"),
                5:  ("helper",     "Helper 💪",        "مددگار 💪"),
                10: ("hero",       "Hero ⭐",          "ہیرو ⭐"),
                20: ("legend",     "Legend 👑",        "لیجنڈ 👑"),
            }

            if count in badges:
                btype, blabel, blabel_ur = badges[count]

                def _award():
                    _sb.table("donor_badges").upsert({
                        "donor_id":          uid,
                        "badge_type":        btype,
                        "badge_label":       blabel,
                        "badge_label_urdu":  blabel_ur,
                        "donations_at_award": count,
                    }, on_conflict="donor_id,badge_type").execute()

                await asyncio.to_thread(_award)
                snack(f"🏆 Badge earned: {blabel}", GREEN)

        except Exception as ex:
            print(f"[BADGE] error: {ex}")

    # ================================================================
    #  LOAD DATA MATCHING CORE
    # ================================================================
    async def _load_my_requests():
        """Donor ke exact blood group aur city ke mutabiq pending requests load karta hai."""
        try:
            uid = sess_get("user_id")
            if not uid:
                return

            def _get_donor_info():
                return _sb.table("profiles").select("blood_group, city, is_available").eq("id", uid).limit(1).execute()

            donor_res = await asyncio.to_thread(_get_donor_info)
            donor_city = ""
            
            if donor_res.data and len(donor_res.data) > 0:
                d_info = donor_res.data[0]
                state["my_blood_group"] = d_info.get("blood_group", "")
                state["is_available"] = d_info.get("is_available", False)
                donor_city = d_info.get("city", "")
                if donor_city:
                    state["my_city"] = donor_city
                
                avail_toggle.value = state["is_available"]
                avail_toggle_text.value = "دستیاب ہوں ✅" if state["is_available"] else "ابھی دستیاب نہیں ⛔"
                avail_toggle_text.color = GREEN if state["is_available"] else TEXT_SUB

            def _get_responses():
                # 🟢 Response table se fetch karte waqt sahi member_id ya backup uid use karein
                final_donor_id = state.get("my_member_id") or uid
                return _sb.table("donor_responses").select("*").eq("donor_id", final_donor_id).execute()

            resp_res = await asyncio.to_thread(_get_responses)
            state["my_responses"] = resp_res.data or []

            if state["my_blood_group"] and (donor_city or is_head_admin):
                def _get_matching_requests():
                    q = (
                        _sb.table("blood_requests")
                        .select("*")
                        .eq("required_blood_group", state["my_blood_group"])
                        .order("created_at", desc=True)
                        .limit(50)
                    )
                    if not is_head_admin:
                        q = q.ilike("city", donor_city)
                    return q.execute()

                req_res = await asyncio.to_thread(_get_matching_requests)
                state["my_requests"] = req_res.data or []

        except Exception as ex:
            print(f"[DONOR] load requests error: {ex}")

    def load_data(_=None):
        donor_list_col.controls = [
            ft.Container(
                padding=ft.padding.all(40),
                alignment=ft.Alignment(0, 0),
                content=ft.ProgressRing(color=PRIMARY, width=40, height=40, stroke_width=3),
            )
        ]
        try:
            page.update()
        except Exception:
            pass

        async def _work():
            try:
                await _restore_session()
                uid = sess_get("user_id")

                if uid:
                    def _profile():
                        # 🟢 'id' کالم کو بھی سلیکٹ کیا تا کہ ممبر کی اصل کیوری آئی ڈی مل سکے
                        return _sb.table("members").select(
                            "id, blood_group, city, is_available, total_donations"
                        ).eq("id", uid).limit(1).execute()

                    pr = await asyncio.to_thread(_profile)
                    if pr.data and len(pr.data) > 0:
                        pr_data = pr.data[0]
                        state["my_member_id"]   = pr_data.get("id") # 🟢 ممبر کی آئی ڈی اسٹیٹ میں محفوظ کر لی
                        state["is_available"]   = pr_data.get("is_available", False)
                        state["my_blood_group"] = pr_data.get("blood_group", "")
                        state["my_city"]        = pr_data.get("city", "")
                        avail_toggle.value      = state["is_available"]
                        avail_toggle_text.value = "دستیاب ہوں ✅" if state["is_available"] else "ابھی دستیاب نہیں ⛔"
                        avail_toggle_text.color = GREEN if state["is_available"] else TEXT_SUB
                        avail_row.visible = True

                def _fetch_donors():
                    return (
                        _sb.table("profiles")
                        .select(
                            "id,full_name,blood_group,city,phone,email,"
                            "last_donation_date,total_donations,date_of_birth,"
                            "gender,profession,is_eligible_donor,is_active,created_at"
                        )
                        .eq("is_eligible_donor", True)
                        .eq("is_active", True)
                        .not_.is_("blood_group", "null")
                        .order("last_donation_date", desc=False, nullsfirst=True)
                        .execute()
                    )

                res = await asyncio.to_thread(_fetch_donors)
                raw_donors = res.data or []

                # Normalize + auto-compute availability from last_donation_date
                # so no manual "update donor info" form is needed at all.
                donors = []
                for d in raw_donors:
                    last_don = d.get("last_donation_date")
                    donors.append({
                        "full_name":      d.get("full_name"),
                        "blood_group":    d.get("blood_group"),
                        "city":           d.get("city"),
                        "phone_number":   d.get("phone"),
                        "email":          d.get("email"),
                        "gender":         d.get("gender"),
                        "profession":     d.get("profession"),
                        "total_donations": d.get("total_donations"),
                        "last_donation":  last_don,
                        "is_available":   _compute_availability(last_don),
                        "next_available": _next_available_date(last_don),
                        "created_at":     d.get("created_at"),
                    })

                # available donors first, then soonest-eligible
                donors.sort(key=lambda d: (not d["is_available"], d.get("next_available") or ""))

                state["donors"]   = donors
                state["filtered"] = state["donors"]

                total     = len(state["donors"])
                available = sum(1 for d in state["donors"] if d.get("is_available") is True)
                cities    = len({(d.get("city") or "").lower() for d in state["donors"] if d.get("city")})
                stat_total.value     = str(total)
                stat_available.value = str(available)
                stat_cities.value    = str(cities)

                apply_filter()

                await _load_my_requests()
                apply_filter()  # re-apply now that state["my_city"] is confirmed from profiles
                _build_requests_tab()

            except Exception as ex:
                print(f"[DONOR] load error: {ex}")
                donor_list_col.controls = [
                    ft.Container(
                        padding=ft.padding.all(20),
                        content=ft.Column([
                            ft.Icon(ft.Icons.WIFI_OFF, color=PRIMARY_MD, size=48),
                            ft.Text(f"Error: {str(ex)[:60]}", color=PRIMARY, size=12, text_align=ft.TextAlign.CENTER),
                            ft.TextButton("Retry | دوبارہ", on_click=load_data),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    )
                ]
                try:
                    page.update()
                except Exception:
                    pass

        page.run_task(_work)

    # ── Contact sheet ────────────────────────────────────────
    def _show_contact(donor: dict):
        name  = donor.get("full_name", "---")
        phone = donor.get("phone_number") or "Not provided"
        blood = donor.get("blood_group", "?")
        city  = donor.get("city", "---")
        email = donor.get("email") or "---"
        bc    = BLOOD_COLORS.get(blood, PRIMARY)

        def _copy(_):
            if phone and phone != "Not provided":
                pyperclip.copy(phone)
                snack("📋 Phone copied!", BLUE)

        async def _whatsapp(_):
            clean = "".join(c for c in phone if c.isdigit() or c == "+")
            if clean:
                await page.launch_url(f"https://wa.me/{clean}")

        bs = ft.BottomSheet(
            content=ft.Container(
                bgcolor=SURFACE, border_radius=ft.border_radius.only(top_left=20, top_right=20),
                padding=ft.padding.Padding(20, 14, 20, 28),
                content=ft.Column([
                    ft.Container(
                        width=40, height=4, border_radius=2, bgcolor="#BDBDBD",
                        margin=ft.margin.only(bottom=12), alignment=ft.Alignment(0, 0),
                    ),
                    ft.Row([
                        ft.Container(
                            width=52, height=52, border_radius=26, bgcolor=bc,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Text(name[0].upper(), size=20, color="white", weight=ft.FontWeight.BOLD),
                        ),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text(name, size=15, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                ft.Text(f"🩸 {blood}", size=11, color=bc),
                                ft.Text(f"📍 {city}", size=11, color=TEXT_SUB),
                            ], spacing=8),
                        ], spacing=4),
                    ]),
                    ft.Divider(color=PRIMARY_LT, height=20),
                    ft.Container(
                        bgcolor=BG, border_radius=12, padding=ft.padding.all(14),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PHONE, color=PRIMARY, size=16),
                                ft.Text("Phone", size=11, color=TEXT_SUB, width=70),
                                ft.Text(phone, size=13, weight=ft.FontWeight.W_500, expand=True),
                            ], spacing=8),
                            ft.Divider(color=PRIMARY_LT, height=12),
                            ft.Row([
                                ft.Icon(ft.Icons.EMAIL, color=PRIMARY, size=16),
                                ft.Text("Email", size=11, color=TEXT_SUB, width=70),
                                ft.Text(email, size=12, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                            ], spacing=8),
                        ], spacing=0),
                    ),
                    ft.Container(height=12),
                    ft.Row([
                        ft.ElevatedButton(
                            "📋 Copy Number",
                            style=ft.ButtonStyle(bgcolor="#616161", color="white", shape=ft.RoundedRectangleBorder(radius=12)),
                            expand=True, height=46, on_click=_copy,
                        ),
                        ft.Container(width=8),
                        ft.ElevatedButton(
                            "💬 WhatsApp",
                            style=ft.ButtonStyle(bgcolor=GREEN, color="white", shape=ft.RoundedRectangleBorder(radius=12)),
                            expand=True, height=46, on_click=_whatsapp,
                        ),
                    ]),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, tight=True),
            ),
            open=True,
        )
        page.overlay.append(bs)
        page.update()

    def _open_whatsapp(donor: dict):
        phone = donor.get("phone_number", "")
        clean = "".join(c for c in phone if c.isdigit() or c == "+")
        if clean:
            async def _launch():
                await page.launch_url(f"https://wa.me/{clean}")
            page.run_task(_launch)
        else:
            snack("WhatsApp number not available", PRIMARY)

    # Initial load trigger
    load_data()

    # ================================================================
    #  RETURN VIEW
    # ================================================================
    return ft.View(
        route="/donor",
        bgcolor=BG,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW,
                icon_color="white",
                on_click=lambda _: page.go("/"),
            ),
            title=ft.Column([
                ft.Text("Donors | ڈونرز", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("خون کے عطیہ دہندگان", size=11, color=PRIMARY_MD),
            ], spacing=0),
            bgcolor=PRIMARY,
            actions=[
                ft.IconButton(ft.Icons.REFRESH, icon_color="white", on_click=load_data, tooltip="Refresh"),
            ],
        ),
        controls=[
            ft.Column(
                expand=True, spacing=0,
                controls=[
                    stats_bar,
                    tab_bar,
                    avail_row,
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            expand=True,
                            controls=[all_donors_col, requests_col],
                            padding=ft.padding.only(bottom=20),
                        ),
                    ),
                ],
            ),
        ],
    )












