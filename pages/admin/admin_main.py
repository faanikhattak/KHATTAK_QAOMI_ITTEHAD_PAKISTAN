
# ================================================================
#  pages/admin/admin_main.py  —  Admin Panel
#  Blood Coordination + Member Management + Reports
#  Flet 0.84 compatible | Session-safe
# ================================================================

from core.theme import Theme 
import asyncio
import flet as ft
import uuid
from datetime import datetime
from supabase import create_client
from services.database.db import supabase, SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options
from core.config import PROVINCES, COUNTRIES, get_districts, COUNTRY_PHONE_CODES, DEFAULT_COUNTRY_CODE

PRIMARY    = "#C62828"
PRIMARY_LT = "#FFEBEE"
PRIMARY_MD = "#FFCDD2"
PRIMARY_DK = "#B71C1C"
GREEN      = "#2E7D32"
GREEN_LT   = "#E8F5E9"
BLUE       = "#1565C0"
BLUE_LT    = "#E3F2FD"
ORANGE     = "#E65100"
ORANGE_LT  = "#FFF3E0"
BG         = "#FFF5F5"
TEXT       = "#212121"
TEXT_SUB   = "#757575"
SURFACE    = "#FFFFFF"

# Leader level options — matches the levels shown/grouped on the
# public /leaders and /leaders_view pages (leaders_common.py).
LEADER_LEVELS = [
    ("central",    "🏛️ Central | مرکزی"),
    ("provincial", "🗺️ Provincial | صوبائی"),
    ("overseas",   "🌍 Overseas | بیرون ملک"),
]


def view(page: ft.Page) -> ft.View:

    # ── Session helpers ─────────────────────────────────────
    def sess_get(key: str, default="") -> str:
        try:
            if hasattr(page.session, "_Session__store"):
                return page.session._Session__store.get(key) or default
            return page.session.get(key) or default
        except Exception:
            return default

    role = sess_get("role", "admin")
    is_head_admin = role == "head_admin"

    # ── Per-session Supabase client ──────────────────────────
    _sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())

    async def _restore():
        try:
            at = sess_get("access_token")
            rt = sess_get("refresh_token", "")
            if at:
                await asyncio.to_thread(_sb.auth.set_session, at, rt)
        except Exception as ex:
            print(f"[ADMIN] session error: {ex}")

    # ── Snackbar ────────────────────────────────────────────
    def snack(msg: str, color: str = PRIMARY):
        async def _show():
            try:
                sb = ft.SnackBar(
                    content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD, size=13),
                    bgcolor=color, duration=3500,
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

    # ── State ───────────────────────────────────────────────
    state = {
        "stats":    {"members": 0, "requests": 0, "donors": 0, "pending": 0, "fulfilled": 0},
        "pending":  [],
        "rejected": [],
        "requests": [],
        "users":    [],
        "donations": [],
    }
    members_sub_tab = {"mode": "pending"}

    # ================================================================
    #  TAB COLUMNS
    # ================================================================
    stats_col      = ft.Column(spacing=10, scroll=ft.ScrollMode.ALWAYS, expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    pending_col    = ft.Column(spacing=8,  scroll=ft.ScrollMode.ALWAYS, expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    requests_col   = ft.Column(spacing=8,  scroll=ft.ScrollMode.ALWAYS, expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    donations_col  = ft.Column(spacing=8,  scroll=ft.ScrollMode.ALWAYS, expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    users_col      = ft.Column(spacing=8,  scroll=ft.ScrollMode.ALWAYS, expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    updates_col    = ft.Column(spacing=10, scroll=ft.ScrollMode.ALWAYS, expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    leaders_col    = ft.Column(spacing=8,  scroll=ft.ScrollMode.ALWAYS, expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    flash_list_col = ft.Column(spacing=8, tight=True)

    # ================================================================
    #  ① STATS
    # ================================================================
    def _stat_box(icon, en, ur, val, color) -> ft.Container:
        return ft.Container(
            width=160, height=90,
            border_radius=16, bgcolor=color,
            shadow=ft.BoxShadow(blur_radius=8, color="#00000022", offset=ft.Offset(0, 4)),
            padding=ft.padding.all(14),
            content=ft.Row([
                ft.Icon(icon, color="white", size=26),
                ft.Column([
                    ft.Text(str(val), size=22, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text(en,       size=11, color="white"),
                    ft.Text(ur,       size=10, color="white70"),
                ], spacing=0, expand=True),
            ], spacing=10),
        )

    def build_stats_ui():
        s = state["stats"]
        stats_col.controls = [
            ft.Container(height=8),
            ft.Row([
                _stat_box(ft.Icons.PEOPLE_ROUNDED,       "Members",   "ممبران",     s["members"],   PRIMARY),
                _stat_box(ft.Icons.BLOODTYPE_ROUNDED,    "Requests",  "درخواستیں",  s["requests"],  "#E53935"),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
            ft.Row([
                _stat_box(ft.Icons.FAVORITE_ROUNDED,     "Donors",    "ڈونرز",      s["donors"],    "#D32F2F"),
                _stat_box(ft.Icons.PENDING_ACTIONS,      "Pending",   "زیر التواء", s["pending"],   "#B71C1C"),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
            ft.Row([
                _stat_box(ft.Icons.CHECK_CIRCLE_ROUNDED, "Fulfilled", "مکمل",       s["fulfilled"], GREEN),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
            ft.Container(height=8),

            # Quick actions
            ft.Container(
                margin=ft.margin.symmetric(horizontal=14),
                content=ft.Column([
                    ft.Text("Quick Actions | فوری اقدامات", size=13,
                            weight=ft.FontWeight.W_700, color=PRIMARY),
                    ft.Container(height=6),
                    ft.Row([
                        _quick_btn(ft.Icons.REFRESH, "Refresh", load_data, PRIMARY),
                        _quick_btn(ft.Icons.HOME_ROUNDED, "Home", lambda e: page.go("/home"), BLUE),
                    ], spacing=10),
                    ft.Container(height=8),
                    ft.Row([
                        _quick_btn(ft.Icons.BAR_CHART_ROUNDED, "Reports | رپورٹس", lambda e: page.go("/admin/reports"), GREEN),
                    ], spacing=10),
                ], spacing=4),
            ),
            ft.Container(height=20),
        ]
        safe_update()

    def _quick_btn(icon, label, on_click, color) -> ft.Container:
        return ft.Container(
            expand=True, height=44, border_radius=12, bgcolor=color,
            alignment=ft.Alignment(0, 0),
            on_click=on_click,
            content=ft.Row([
                ft.Icon(icon, color="white", size=16),
                ft.Text(label, color="white", size=12, weight=ft.FontWeight.W_600),
            ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        )

    # ================================================================
    #  ② PENDING MEMBERS
    # ================================================================
    def _member_card(m: dict, rejected: bool = False) -> ft.Card:
        name  = m.get("full_name", "---")
        email = m.get("email", "---")
        city  = m.get("city", "---")
        phone = m.get("phone", "---")
        blood = m.get("blood_group", "")
        uid   = m.get("id", "")

        def _approve(e):
            async def _do():
                try:
                    def _upd():
                        return (
                            supabase.table("profiles")
                            .update({"is_approved": True, "account_status": "active"})
                            .eq("id", uid)
                            .execute()
                        )
                    res = await asyncio.to_thread(_upd)
                    if res.data:
                        snack(f"✅ Approved: {name}", GREEN)
                        load_data()
                    else:
                        snack(f"⚠ Nothing updated — check DB permissions (RLS) for profiles.id={uid}", ORANGE)
                except Exception as ex:
                    snack(f"⚠ {str(ex)[:80]}")
            page.run_task(_do)

        def _reject(e):
            async def _do():
                try:
                    await _restore()
                    def _upd():
                        _sb.table("profiles").update(
                            {"account_status": "rejected"}
                        ).eq("id", uid).execute()
                    await asyncio.to_thread(_upd)
                    snack(f"❌ Rejected: {name}", ORANGE)
                    load_data()
                except Exception as ex:
                    err_txt = str(ex)
                    if "check constraint" in err_txt.lower() and "account_status" in err_txt.lower():
                        snack("⚠ DB rejects 'rejected' status — update the account_status CHECK constraint in Supabase (see fix_account_status.sql)")
                    else:
                        snack(f"⚠ {err_txt[:50]}")
            page.run_task(_do)

        def _restore_pending(e):
            async def _do():
                try:
                    await _restore()
                    def _upd():
                        _sb.table("profiles").update(
                            {"account_status": "active"}
                        ).eq("id", uid).execute()
                    await asyncio.to_thread(_upd)
                    snack(f"↩️ Moved back to pending: {name}", BLUE)
                    load_data()
                except Exception as ex:
                    snack(f"⚠ {str(ex)[:50]}")
            page.run_task(_do)

        def _delete_permanently(e):
            async def _do():
                try:
                    await _restore()
                    def _del():
                        _sb.table("profiles").delete().eq("id", uid).execute()
                    await asyncio.to_thread(_del)
                    snack(f"🗑️ Deleted permanently: {name}", PRIMARY_DK)
                    load_data()
                except Exception as ex:
                    snack(f"⚠ {str(ex)[:50]}")
            page.run_task(_do)

        if rejected:
            action_row = ft.Row([
                ft.ElevatedButton(
                    "↩️ Restore to Pending",
                    style=ft.ButtonStyle(color="white", bgcolor=BLUE,
                                         shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=_restore_pending, height=36,
                ),
                ft.OutlinedButton(
                    "🗑️ Delete Permanently",
                    style=ft.ButtonStyle(color=PRIMARY,
                                         shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=_delete_permanently, height=36,
                ),
            ], spacing=8)
        else:
            action_row = ft.Row([
                ft.ElevatedButton(
                    "✅ Approve",
                    style=ft.ButtonStyle(color="white", bgcolor=GREEN,
                                         shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=_approve, height=36,
                ),
                ft.OutlinedButton(
                    "❌ Reject",
                    style=ft.ButtonStyle(color=PRIMARY,
                                         shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=_reject, height=36,
                ),
            ], spacing=8)

        return ft.Card(
            elevation=3, shape=ft.RoundedRectangleBorder(radius=14),
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            content=ft.Container(
                bgcolor=SURFACE, border_radius=14,
                padding=ft.padding.all(14),
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            width=44, height=44, border_radius=22,
                            bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
                            content=ft.Text(
                                name[0].upper() if name else "?",
                                size=18, color=PRIMARY, weight=ft.FontWeight.BOLD,
                            ),
                        ),
                        ft.Container(width=10),
                        ft.Column([
                            ft.Text(name, size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                            ft.Text(email, size=11, color=TEXT_SUB),
                            ft.Text(f"📍 {city}  📞 {phone}  🩸 {blood}",
                                    size=11, color="#9E9E9E"),
                        ], expand=True, spacing=2),
                    ]),
                    ft.Container(height=8),
                    action_row,
                ], spacing=0),
            ),
        )

    def _switch_members_tab(mode: str):
        members_sub_tab["mode"] = mode
        build_pending_ui()

    def build_pending_ui():
        mode = members_sub_tab["mode"]
        pending_count = len(state["pending"])
        rejected_count = len(state["rejected"])

        def _seg_btn(label: str, key: str) -> ft.Container:
            active = mode == key
            return ft.Container(
                on_click=lambda e: _switch_members_tab(key),
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                border_radius=10,
                bgcolor=PRIMARY if active else "#00000000",
                content=ft.Text(
                    label, size=12,
                    weight=ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL,
                    color="white" if active else TEXT_SUB,
                ),
            )

        header = ft.Row([
            _seg_btn(f"⏳ Pending ({pending_count})", "pending"),
            _seg_btn(f"❌ Rejected ({rejected_count})", "rejected"),
        ], spacing=8)

        if mode == "pending":
            items = state["pending"]
            cards = [_member_card(m, rejected=False) for m in items] if items else \
                [_empty("✅", "All approved!\nسب منظور ہو گئے")]
        else:
            items = state["rejected"]
            cards = [_member_card(m, rejected=True) for m in items] if items else \
                [_empty("📭", "No rejected members\nکوئی مسترد شدہ ممبر نہیں")]

        pending_col.controls = [header, ft.Divider(height=16)] + cards
        safe_update()

    # ================================================================
    #  ③ BLOOD REQUESTS
    # ================================================================
    def _request_card(req: dict) -> ft.Container:
        blood    = req.get("required_blood_group") or req.get("blood_group", "?")
        city     = req.get("city", "---")
        tehsil   = req.get("tehsil") or ""
        province = req.get("province", "")
        status   = req.get("status", "pending")
        patient  = req.get("patient_name", "---")
        urgency  = req.get("urgency", "medium")
        hospital = req.get("hospital", "")
        contact  = req.get("contact", "")
        req_id   = req.get("id", "")
        requester = req.get("requester_name", "")

        status_map = {
            "pending":     ("#FFF9C4", "#F57F17", "⏳ Pending"),
            "matching":    (BLUE_LT,   BLUE,      "🔍 Matching"),
            "in_progress": ("#F3E5F5", "#6A1B9A",  "✅ Donor Found"),
            "fulfilled":   (GREEN_LT,  GREEN,      "🎉 Fulfilled"),
            "cancelled":   ("#FAFAFA", TEXT_SUB,   "❌ Cancelled"),
            "expired":     ("#FAFAFA", TEXT_SUB,   "⌛ Expired"),
        }
        bg, fg, status_label = status_map.get(status, ("#F5F5F5", TEXT_SUB, status))

        urgency_map = {
            "low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"
        }
        em = urgency_map.get(urgency, "📌")

        def _update_status(new_s: str):
            async def _do():
                try:
                    await _restore()
                    def _upd():
                        _sb.table("blood_requests").update(
                            {"status": new_s}
                        ).eq("id", req_id).execute()
                    await asyncio.to_thread(_upd)
                    snack(f"✅ Status updated: {new_s}", GREEN)
                    load_data()
                except Exception as ex:
                    snack(f"⚠ {str(ex)[:50]}")
            page.run_task(_do)

        def _assign_donor(e):
            _show_assign_donor_dialog(req)

        def _view_responses(e):
            _show_donor_responses(req_id, patient)

        status_badge = ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border_radius=8,
            bgcolor=bg,
            content=ft.Text(status_label, size=9, color=fg, weight=ft.FontWeight.BOLD),
        )

        return ft.Container(
            bgcolor=SURFACE, border_radius=16,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(14),
            shadow=ft.BoxShadow(blur_radius=8, color="#15000000", offset=ft.Offset(0, 2)),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        width=50, height=50, border_radius=25,
                        bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
                        content=ft.Text(blood, size=13,
                                        weight=ft.FontWeight.BOLD, color=PRIMARY),
                    ),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(f"{em} {patient}", size=14,
                                weight=ft.FontWeight.W_700, color=TEXT),
                        ft.Text(f"🏥 {hospital}", size=11, color=TEXT_SUB),
                        ft.Text(f"📍 {city} {tehsil} — {province}", size=11, color=TEXT_SUB),
                        ft.Text(f"📞 {contact}  👤 {requester}", size=11, color="#9E9E9E"),
                    ], expand=True, spacing=2, tight=True),
                    status_badge,
                ], vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Container(height=10),
                ft.Row([
                    ft.OutlinedButton(
                        "👥 Responses",
                        style=ft.ButtonStyle(
                            color=BLUE, side=ft.BorderSide(1, BLUE),
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        height=36, on_click=_view_responses,
                    ),
                    ft.OutlinedButton(
                        "👤 Assign",
                        style=ft.ButtonStyle(
                            color=ORANGE, side=ft.BorderSide(1, ORANGE),
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        height=36, on_click=_assign_donor,
                    ),
                    ft.ElevatedButton(
                        "🎉 Fulfill",
                        style=ft.ButtonStyle(
                            color="white", bgcolor=GREEN,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        height=36,
                        on_click=lambda e: _update_status("fulfilled"),
                        visible=status not in ["fulfilled", "cancelled"],
                    ),
                    ft.OutlinedButton(
                        "❌ Cancel",
                        style=ft.ButtonStyle(
                            color=PRIMARY, side=ft.BorderSide(1, PRIMARY_MD),
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        height=36,
                        on_click=lambda e: _update_status("cancelled"),
                        visible=status not in ["fulfilled", "cancelled"],
                    ),
                ], spacing=6, wrap=True),
            ], spacing=0),
        )

    def build_requests_ui():
        reqs = state["requests"]
        if reqs:
            requests_col.controls = [_request_card(r) for r in reqs]
        else:
            requests_col.controls = [_empty("🩸", "No requests\nکوئی درخواست نہیں")]
        safe_update()

    # ── Donor responses dialog ────────────────────────────────
    def _show_donor_responses(req_id, patient_name):
        async def _load():
            try:
                await _restore()
                def _fetch():
                    return (
                        _sb.table("donor_responses")
                        .select("*")
                        .eq("request_id", req_id)
                        .execute()
                    )
                res = await asyncio.to_thread(_fetch)
                responses = res.data or []

                status_colors = {
                    "notified":  (BLUE_LT,   BLUE,     "🔔"),
                    "accepted":  (GREEN_LT,  GREEN,    "✅"),
                    "declined":  ("#FAFAFA", TEXT_SUB, "❌"),
                    "donated":   (GREEN_LT,  GREEN,    "🎉"),
                }

                rows = []
                for r in responses:
                    bg, tc, em = status_colors.get(r.get("status", "notified"), (BLUE_LT, BLUE, "🔔"))
                    rows.append(
                        ft.Container(
                            bgcolor=bg, border_radius=10,
                            padding=ft.padding.symmetric(horizontal=12, vertical=8),
                            content=ft.Row([
                                ft.Text(em, size=18),
                                ft.Container(width=8),
                                ft.Column([
                                    ft.Text(r.get("donor_name", "---"), size=13,
                                            weight=ft.FontWeight.W_600, color=TEXT),
                                    ft.Text(r.get("donor_phone", ""), size=11, color=TEXT_SUB),
                                    ft.Text(r.get("decline_reason", "") or "", size=10, color=TEXT_SUB),
                                ], spacing=2, expand=True, tight=True),
                                ft.Container(
                                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                    border_radius=8,
                                    bgcolor=f"{tc}22",
                                    content=ft.Text(
                                        (r.get("status") or "").upper(),
                                        size=9, color=tc, weight=ft.FontWeight.BOLD,
                                    ),
                                ),
                            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        )
                    )

                if not rows:
                    rows = [ft.Text("No responses yet | ابھی کوئی جواب نہیں",
                                    size=13, color=TEXT_SUB)]

                def _close(e=None):
                    try:
                        dlg.open = False
                        page.update()
                    except Exception:
                        pass

                dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(f"Responses — {patient_name}",
                                  weight=ft.FontWeight.BOLD, color=PRIMARY),
                    content=ft.Container(
                        width=320, height=300,
                        content=ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO),
                    ),
                    actions=[ft.TextButton("Close | بند کریں", on_click=_close)],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                if dlg not in page.overlay:
                    page.overlay.append(dlg)
                dlg.open = True
                page.update()

            except Exception as ex:
                snack(f"Error: {str(ex)[:60]}")

        page.run_task(_load)

    # ── Manual assign donor dialog ────────────────────────────
    def _show_assign_donor_dialog(req: dict):
        req_id    = req.get("id")
        blood_grp = req.get("required_blood_group") or req.get("blood_group", "")
        city      = req.get("city", "")

        async def _load_donors():
            try:
                await _restore()
                def _fetch():
                    return (
                        _sb.table("profiles")
                        .select("id, full_name, phone, blood_group, city")
                        .eq("blood_group", blood_grp)
                        .eq("is_available", True)
                        .execute()
                    )
                res = await asyncio.to_thread(_fetch)
                donors = res.data or []

                def _close(e=None):
                    try:
                        dlg.open = False
                        page.update()
                    except Exception:
                        pass

                def _assign(donor):
                    async def _do():
                        try:
                            await _restore()
                            from datetime import datetime, timezone
                            now = datetime.now(timezone.utc).isoformat()

                            def _upsert():
                                _sb.table("donor_responses").upsert({
                                    "request_id":        req_id,
                                    "donor_id":          donor["id"],
                                    "donor_name":        donor.get("full_name", ""),
                                    "donor_phone":       donor.get("phone", ""),
                                    "donor_blood_group": blood_grp,
                                    "status":            "accepted",
                                    "responded_at":      now,
                                }, on_conflict="request_id,donor_id").execute()

                                _sb.table("blood_requests").update(
                                    {"status": "in_progress",
                                     "assigned_admin_id": sess_get("user_id")}
                                ).eq("id", req_id).execute()

                            await asyncio.to_thread(_upsert)
                            snack(f"✅ {donor.get('full_name', '')} assigned!", GREEN)
                            _close()
                            load_data()
                        except Exception as ex:
                            snack(f"Error: {str(ex)[:60]}")
                    page.run_task(_do)

                rows = []
                for d in donors:
                    rows.append(
                        ft.Container(
                            bgcolor=PRIMARY_LT, border_radius=10,
                            padding=ft.padding.symmetric(horizontal=12, vertical=8),
                            on_click=lambda e, donor=d: _assign(donor),
                            content=ft.Row([
                                ft.Text(d.get("blood_group", "?"), size=13,
                                        weight=ft.FontWeight.BOLD, color=PRIMARY),
                                ft.Container(width=10),
                                ft.Column([
                                    ft.Text(d.get("full_name", "---"), size=13,
                                            weight=ft.FontWeight.W_600),
                                    ft.Text(f"📍 {d.get('city', '')}  📞 {d.get('phone', '')}",
                                            size=11, color=TEXT_SUB),
                                ], spacing=2, expand=True, tight=True),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT_SUB, size=18),
                            ]),
                        )
                    )

                if not rows:
                    rows = [ft.Text(f"No {blood_grp} donors available in {city}",
                                    size=13, color=TEXT_SUB)]

                dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Assign Donor | ڈونر منتخب کریں",
                                  weight=ft.FontWeight.BOLD, color=PRIMARY),
                    content=ft.Container(
                        width=320, height=300,
                        content=ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO),
                    ),
                    actions=[ft.TextButton("Cancel", on_click=_close)],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                if dlg not in page.overlay:
                    page.overlay.append(dlg)
                dlg.open = True
                page.update()

            except Exception as ex:
                snack(f"Error: {str(ex)[:60]}")

        page.run_task(_load_donors)

    # ================================================================
    #  ④ DONATIONS HISTORY
    # ================================================================
    def build_donations_ui():
        donations = state.get("donations", [])
        if not donations:
            donations_col.controls = [_empty("💉", "No donations yet\nابھی کوئی عطیہ نہیں")]
            safe_update()
            return

        cards = []
        for d in donations:
            cards.append(
                ft.Container(
                    bgcolor=SURFACE, border_radius=14,
                    margin=ft.margin.symmetric(horizontal=14, vertical=4),
                    padding=ft.padding.all(14),
                    shadow=ft.BoxShadow(blur_radius=6, color="#15000000", offset=ft.Offset(0, 2)),
                    content=ft.Row([
                        ft.Container(
                            width=46, height=46, border_radius=23,
                            bgcolor=GREEN_LT, alignment=ft.Alignment(0, 0),
                            content=ft.Text(d.get("blood_group", "?"), size=12,
                                            weight=ft.FontWeight.BOLD, color=GREEN),
                        ),
                        ft.Container(width=10),
                        ft.Column([
                            ft.Text(f"🎉 {d.get('donor_name', '---')} → {d.get('requester_name', '---')}",
                                    size=13, weight=ft.FontWeight.W_600, color=TEXT),
                            ft.Text(f"🏥 {d.get('hospital_name', '')} — {d.get('city', '')}",
                                    size=11, color=TEXT_SUB),
                            ft.Text(f"📅 {str(d.get('donated_at', ''))[:10]}",
                                    size=10, color="#9E9E9E"),
                        ], expand=True, spacing=2, tight=True),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8, bgcolor=GREEN_LT,
                            content=ft.Text("Donated", size=9, color=GREEN,
                                            weight=ft.FontWeight.BOLD),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )
        donations_col.controls = cards
        safe_update()

    # ================================================================
    #  ⑤ USER MANAGEMENT
    # ================================================================
    search_f = ft.TextField(
        label="Search | تلاش کریں",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=14, focused_border_color=PRIMARY, border_color="#BDBDBD",
        on_change=lambda e: _filter_users(e.control.value or ""),
    )

    def _filter_users(q: str):
        q = q.lower()
        filtered = [
            u for u in state["users"]
            if q in (u.get("full_name") or "").lower()
            or q in (u.get("email") or "").lower()
            or q in (u.get("phone") or "").lower()
        ]
        _build_users_list(filtered)

    def _build_users_list(users: list):
        if not users:
            users_col.controls = [
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    content=search_f,
                ),
                _empty("👥", "No users found\nکوئی صارف نہیں"),
            ]
        else:
            tiles = []
            for u in users:
                member_uid = u.get("id", "")
                role_val = u.get("role") or "member"
                role_colors = {
                    "head_admin": "#4A148C", "admin": BLUE,
                    "verified": GREEN, "member": ORANGE,
                }
                rc = role_colors.get(role_val, ORANGE)

                acc_status = u.get("account_status", "active") or "active"
                status_meta = {
                    "active":  ("✅ Active",  GREEN),
                    "blocked": ("⛔ Blocked", ORANGE),
                    "banned":  ("🚫 Banned",  PRIMARY_DK),
                    "frozen":  ("❄️ Frozen",  BLUE),
                }
                status_label, status_color = status_meta.get(acc_status, ("✅ Active", GREEN))

                menu_items = []
                if is_head_admin:
                    menu_items.append(
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.Icons.MANAGE_ACCOUNTS, color=BLUE, size=16),
                                ft.Text(f"{role_val.upper()} — Change Role",
                                        size=11, color=BLUE),
                            ], spacing=8),
                            on_click=lambda e, u_id=member_uid, r=role_val: _show_role_dialog(u_id, r),
                        )
                    )
                if acc_status == "active":
                    menu_items += [
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.Icons.BLOCK, color=ORANGE, size=16),
                                ft.Text("Block | بلاک", size=11, color=ORANGE),
                            ], spacing=8),
                            on_click=lambda e, i=member_uid: _restrict_user(i, "blocked"),
                        ),
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.Icons.GAVEL, color=PRIMARY_DK, size=16),
                                ft.Text("Ban | پابندی", size=11, color=PRIMARY_DK),
                            ], spacing=8),
                            on_click=lambda e, i=member_uid: _restrict_user(i, "banned"),
                        ),
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.Icons.AC_UNIT, color=BLUE, size=16),
                                ft.Text("Freeze | منجمد", size=11, color=BLUE),
                            ], spacing=8),
                            on_click=lambda e, i=member_uid: _restrict_user(i, "frozen"),
                        ),
                    ]
                else:
                    menu_items.append(
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.Icons.LOCK_OPEN, color=GREEN, size=16),
                                ft.Text("Reactivate | بحال کریں", size=11, color=GREEN),
                            ], spacing=8),
                            on_click=lambda e, i=member_uid: _reactivate_user(i),
                        )
                    )
                menu_items.append(
                    ft.PopupMenuItem(
                        content=ft.Row([
                            ft.Icon(ft.Icons.DELETE_OUTLINE, color=PRIMARY, size=16),
                            ft.Text("Remove | ہٹائیں", size=11, color=PRIMARY),
                        ], spacing=8),
                        on_click=lambda e, i=member_uid: _remove_user(i),
                    )
                )

                tiles.append(
                    ft.Container(
                        bgcolor=SURFACE, border_radius=12,
                        margin=ft.margin.symmetric(horizontal=14, vertical=3),
                        padding=ft.padding.all(12),
                        shadow=ft.BoxShadow(blur_radius=4, color="#10000000", offset=ft.Offset(0, 1)),
                        content=ft.Row([
                            ft.Container(
                                width=40, height=40, border_radius=20,
                                bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
                                content=ft.Text(
                                    ((u.get("full_name") or "?")[:1] or "?").upper(),
                                    size=16, color=PRIMARY, weight=ft.FontWeight.BOLD,
                                ),
                            ),
                            ft.Container(width=10),
                            ft.Column([
                                ft.Text(u.get("full_name", "---"), size=13,
                                        weight=ft.FontWeight.W_600, color=TEXT),
                                ft.Text(f"{u.get('email', '')} | {u.get('phone', '')}",
                                        size=10, color=TEXT_SUB,
                                        overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"📍 {u.get('city', '')} | 🩸 {u.get('blood_group', '')}",
                                        size=10, color="#9E9E9E"),
                                ft.Text(status_label, size=10, weight=ft.FontWeight.W_600,
                                        color=status_color),
                            ], expand=True, spacing=2, tight=True),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color=TEXT_SUB,
                                items=menu_items,
                            ),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    )
                )

            users_col.controls = [
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    content=search_f,
                ),
                *tiles,
            ]
        safe_update()

    def _show_role_dialog(target_uid: str, current_role: str):
        if not is_head_admin:
            snack("🔒 Only Head Admin can change roles", ORANGE)
            return
        role_dd = ft.Dropdown(
            label="Select Role | کردار منتخب کریں",
            border_radius=12,
            focused_border_color=PRIMARY,
            value=current_role,
            options=[
                ft.dropdown.Option("member",     "👤 Member | ممبر"),
                ft.dropdown.Option("verified",   "✅ Verified | تصدیق شدہ"),
                ft.dropdown.Option("admin",      "⚙️ Admin | ایڈمن"),
                ft.dropdown.Option("head_admin", "👑 Head Admin | ہیڈ ایڈمن"),
            ],
        )

        def _close(e=None):
            try:
                dlg.open = False
                page.update()
            except Exception:
                pass

        def _save(e=None):
            new_role = role_dd.value
            if not new_role:
                snack("⚠ Please select a role!")
                return
            async def _do():
                try:
                    await _restore()
                    def _upd(t_uid=target_uid):
                        print(f"[ROLE] updating target_uid={t_uid} to role={new_role}")
                        res = supabase.table("profiles").update(
                            {"role": new_role, "is_approved": True}
                        ).eq("id", t_uid).execute()
                        print(f"[ROLE] result: {res.data}")
                        return res
                    res = await asyncio.to_thread(_upd)
                    if res.data:
                        snack(f"✅ Role updated: {new_role}", GREEN)
                        _close()
                        _load_users()
                    else:
                        snack("⚠ Update failed!", ORANGE)
                        print(f"[ROLE] WARNING: empty for target_uid={target_uid}")
                except Exception as ex:
                    print(f"[ROLE] exception: {ex}")
                    snack(f"⚠ {str(ex)[:50]}")
            page.run_task(_do)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Change Role | کردار بدلیں",
                          weight=ft.FontWeight.BOLD, color=PRIMARY),
            content=ft.Container(
                width=280,
                padding=ft.padding.only(top=8),
                content=ft.Column([
                    ft.Text(f"Current: {current_role.upper()}",
                            size=11, color=TEXT_SUB),
                    ft.Container(height=8),
                    role_dd,
                ], spacing=4, tight=True),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_close,
                              style=ft.ButtonStyle(color=TEXT_SUB)),
                ft.ElevatedButton(
                    "Save | محفوظ کریں",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY, color="white",
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    _RESTRICT_LABELS = {
        "blocked": ("⛔ User blocked!",  ORANGE),
        "banned":  ("🚫 User banned!",   PRIMARY_DK),
        "frozen":  ("❄️ User frozen!",   BLUE),
    }

    def _restrict_user(uid: str, kind: str):
        msg, color = _RESTRICT_LABELS.get(kind, ("Updated", ORANGE))

        async def _do():
            try:
                await _restore()
                def _upd():
                    _sb.table("profiles").update({"is_active": False}).eq("id", uid).execute()
                    _sb.table("user_restrictions").upsert(
                        {"user_id": uid, "status": kind}
                    ).execute()
                await asyncio.to_thread(_upd)
                snack(msg, color)
                _load_users()
            except Exception as ex:
                snack(f"⚠ {str(ex)[:50]}")
        page.run_task(_do)

    def _reactivate_user(uid: str):
        async def _do():
            try:
                await _restore()
                def _upd():
                    _sb.table("profiles").update({"is_active": True}).eq("id", uid).execute()
                    _sb.table("user_restrictions").upsert(
                        {"user_id": uid, "status": "active"}
                    ).execute()
                await asyncio.to_thread(_upd)
                snack("✅ User reactivated!", GREEN)
                _load_users()
            except Exception as ex:
                snack(f"⚠ {str(ex)[:50]}")
        page.run_task(_do)

    def _remove_user(uid: str):
        async def _do():
            try:
                await _restore()
                def _del():
                    _sb.table("profiles").delete().eq("id", uid).execute()
                await asyncio.to_thread(_del)
                snack("✅ User removed!", GREEN)
                _load_users()
            except Exception as ex:
                snack(f"⚠ {str(ex)[:50]}")
        page.run_task(_do)

    def _load_users():
        async def _do():
            try:
                await _restore()
                is_head = role == "head_admin"
                def _fetch():
                    q = _sb.table("profiles").select("*").order("created_at", desc=True)
                    if not is_head:
                        city = sess_get("city", "")
                        if city:
                            q = q.eq("city", city)
                    return q.execute()
                res = await asyncio.to_thread(_fetch)
                users_list = res.data or []

                try:
                    def _fetch_restrictions():
                        return _sb.table("user_restrictions").select("user_id,status").execute()
                    rres = await asyncio.to_thread(_fetch_restrictions)
                    status_map = {r["user_id"]: r.get("status", "active") for r in (rres.data or [])}
                except Exception as ex:
                    print(f"[USERS] user_restrictions fetch failed: {ex}")
                    status_map = {}

                for u in users_list:
                    u["account_status"] = status_map.get(u.get("id"), "active")

                state["users"] = users_list
                _build_users_list(state["users"])
            except Exception as ex:
                snack(f"⚠ {str(ex)[:60]}")
        page.run_task(_do)

    # ================================================================
    #  ⑥ COMMUNITY UPDATES
    # ================================================================
    upd_title = ft.TextField(
        label="Title | عنوان *", border_radius=14,
        focused_border_color=PRIMARY, border_color="#BDBDBD",
    )
    upd_body = ft.TextField(
        label="Content | مواد *", multiline=True,
        min_lines=3, max_lines=5, border_radius=14,
        focused_border_color=PRIMARY, border_color="#BDBDBD",
    )
    upd_color = ft.Dropdown(
        label="Color | رنگ", border_radius=14, value=PRIMARY,
        focused_border_color=PRIMARY, border_color="#BDBDBD",
        options=[
            ft.dropdown.Option(PRIMARY, "🔴 Red"),
            ft.dropdown.Option(BLUE,    "🔵 Blue"),
            ft.dropdown.Option(GREEN,   "🟢 Green"),
            ft.dropdown.Option(ORANGE,  "🟠 Orange"),
        ],
    )
    post_btn = ft.ElevatedButton(
        content=ft.Text("Post Update | خبر شائع کریں",
                        weight=ft.FontWeight.BOLD, size=14),
        style=ft.ButtonStyle(color="white", bgcolor=PRIMARY,
                             shape=ft.RoundedRectangleBorder(radius=12)),
        width=340, height=48,
    )

    def _on_post(e):
        if not upd_title.value or not upd_body.value:
            snack("⚠ Title and content required!")
            return
        post_btn.disabled = True
        post_btn.content = ft.ProgressRing(width=20, height=20, color="white", stroke_width=2)
        safe_update()

        async def _do():
            try:
                await _restore()
                uid = sess_get("user_id")
                def _insert():
                    _sb.table("community_updates").insert({
                        "title":    upd_title.value.strip(),
                        "content":  upd_body.value.strip(),
                        "color":    upd_color.value or PRIMARY,
                        "admin_id": uid,
                    }).execute()
                await asyncio.to_thread(_insert)
                upd_title.value = ""
                upd_body.value  = ""
                snack("✅ Update posted!", GREEN)
            except Exception as ex:
                snack(f"⚠ {str(ex)[:60]}")
            finally:
                post_btn.disabled = False
                post_btn.content = ft.Text("Post Update | خبر شائع کریں",
                                           weight=ft.FontWeight.BOLD, size=14)
                safe_update()

        page.run_task(_do)

    post_btn.on_click = _on_post

    # ================================================================
    #  ⑥b FLASH TICKER
    # ================================================================
    def _load_flash_notes():
        async def _do():
            try:
                await _restore()
                def _fetch():
                    return (
                        _sb.table("flash_ticker")
                        .select("*")
                        .order("created_at", desc=True)
                        .execute()
                    )
                res = await asyncio.to_thread(_fetch)
                _build_flash_list(res.data or [])
            except Exception as ex:
                snack(f"⚠ {str(ex)[:60]}")
        page.run_task(_do)

    def _build_flash_list(notes: list):
        if not notes:
            flash_list_col.controls = [_empty("📢", "No flash notes yet\nابھی کوئی فلیش نوٹ نہیں")]
            safe_update()
            return

        rows = []
        for n in notes:
            nid = n.get("id", "")
            content = n.get("content", "") or ""
            active = bool(n.get("is_active", True))
            note_color = n.get("color", "#212121") or "#212121"
            note_lang = n.get("language", "en") or "en"
            lang_badge = "اردو" if note_lang == "ur" else "EN"
            rows.append(
                ft.Container(
                    bgcolor=SURFACE, border_radius=12,
                    padding=ft.padding.all(12),
                    shadow=ft.BoxShadow(blur_radius=4, color="#10000000", offset=ft.Offset(0, 1)),
                    content=ft.Row([
                        ft.Icon(ft.Icons.CIRCLE, color=GREEN if active else "#BDBDBD", size=10),
                        ft.Container(width=6, height=18, border_radius=3, bgcolor=note_color),
                        ft.Container(width=8),
                        ft.Text(content, size=12, color=TEXT, expand=True,
                                overflow=ft.TextOverflow.ELLIPSIS, max_lines=2),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            border_radius=10, bgcolor="#EEEEEE",
                            content=ft.Text(lang_badge, size=9, color=TEXT_SUB,
                                             weight=ft.FontWeight.W_600),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.PAUSE_CIRCLE_OUTLINE if active else ft.Icons.PLAY_CIRCLE_OUTLINE,
                            icon_color=ORANGE if active else GREEN, icon_size=18,
                            tooltip="Pause" if active else "Activate",
                            on_click=lambda e, i=nid, a=active: _toggle_flash(i, a),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.EDIT_OUTLINED, icon_color=BLUE, icon_size=18,
                            tooltip="Edit",
                            on_click=lambda e, i=nid, c=content, col=note_color, lg=note_lang:
                                _show_flash_dialog(i, c, col, lg),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE, icon_color=PRIMARY, icon_size=18,
                            tooltip="Delete",
                            on_click=lambda e, i=nid: _delete_flash(i),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )
        flash_list_col.controls = rows
        safe_update()

    def _toggle_flash(nid: str, currently_active: bool):
        async def _do():
            try:
                await _restore()
                def _upd():
                    _sb.table("flash_ticker").update(
                        {"is_active": not currently_active}
                    ).eq("id", nid).execute()
                await asyncio.to_thread(_upd)
                _load_flash_notes()
            except Exception as ex:
                snack(f"⚠ {str(ex)[:50]}")
        page.run_task(_do)

    def _delete_flash(nid: str):
        async def _do():
            try:
                await _restore()
                def _del():
                    _sb.table("flash_ticker").delete().eq("id", nid).execute()
                await asyncio.to_thread(_del)
                snack("✅ Flash note removed!", GREEN)
                _load_flash_notes()
            except Exception as ex:
                snack(f"⚠ {str(ex)[:50]}")
        page.run_task(_do)

    _FLASH_COLORS = [
        "#212121", "#D32F2F", "#1976D2", "#2E7D32",
        "#F9A825", "#6A1B9A", "#455A64",
    ]

    def _show_flash_dialog(nid: str = None, existing_content: str = "",
                            existing_color: str = "#212121", existing_language: str = "en"):
        is_edit = nid is not None
        picked_color = [existing_color or "#212121"]
        picked_lang = [existing_language or "en"]

        content_f = ft.TextField(
            label="Scroll Text | سکرول ٹیکسٹ *", multiline=True,
            min_lines=2, max_lines=4, border_radius=14,
            value=existing_content,
            focused_border_color=PRIMARY, border_color="#BDBDBD",
        )

        swatch_row = ft.Row(spacing=8, wrap=True)

        def _refresh_swatches():
            chips = []
            for c in _FLASH_COLORS:
                selected = (c == picked_color[0])
                chips.append(
                    ft.Container(
                        width=30, height=30, border_radius=15, bgcolor=c,
                        border=ft.border.all(3, PRIMARY) if selected else ft.border.all(1, "#BDBDBD"),
                        on_click=lambda e, col=c: _pick_color(col),
                    )
                )
            swatch_row.controls = chips

        def _pick_color(col: str):
            picked_color[0] = col
            _refresh_swatches()
            page.update()

        _refresh_swatches()

        lang_row = ft.Row(spacing=8)

        def _refresh_lang():
            def _chip(code, label):
                selected = picked_lang[0] == code
                return ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    border_radius=20,
                    bgcolor=PRIMARY if selected else "#EEEEEE",
                    content=ft.Text(label, size=12, color="white" if selected else TEXT,
                                     weight=ft.FontWeight.W_600),
                    on_click=lambda e, c=code: _pick_lang(c),
                )
            lang_row.controls = [_chip("en", "English (R→L)"), _chip("ur", "اردو (L→R)")]

        def _pick_lang(code: str):
            picked_lang[0] = code
            _refresh_lang()
            page.update()

        _refresh_lang()

        def _close(e=None):
            try:
                dlg.open = False
                page.update()
            except Exception:
                pass

        def _save(e=None):
            if not content_f.value or not content_f.value.strip():
                snack("⚠ Text required!")
                return

            async def _do():
                try:
                    await _restore()
                    payload = {
                        "content": content_f.value.strip(),
                        "color": picked_color[0],
                        "language": picked_lang[0],
                    }

                    def _upsert():
                        if is_edit:
                            _sb.table("flash_ticker").update(payload).eq("id", nid).execute()
                        else:
                            payload["is_active"] = True
                            _sb.table("flash_ticker").insert(payload).execute()

                    await asyncio.to_thread(_upsert)
                    snack(f"✅ Flash note {'updated' if is_edit else 'added'}!", GREEN)
                    _close()
                    _load_flash_notes()
                except Exception as ex:
                    snack(f"⚠ {str(ex)[:60]}")
            page.run_task(_do)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Edit Flash Note | ترمیم" if is_edit else "Add Flash Note | فلیش نوٹ شامل کریں",
                weight=ft.FontWeight.BOLD, color=PRIMARY,
            ),
            content=ft.Container(
                width=300,
                content=ft.Column([
                    content_f,
                    ft.Text("Color | رنگ", size=11, color=TEXT_SUB),
                    swatch_row,
                    ft.Text("Language | زبان (scroll direction)", size=11, color=TEXT_SUB),
                    lang_row,
                ], spacing=10, tight=True),
            ),
            actions=[
                ft.TextButton("Cancel | منسوخ", on_click=_close,
                              style=ft.ButtonStyle(color=TEXT_SUB)),
                ft.ElevatedButton(
                    "Save | محفوظ کریں",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY, color="white",
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def build_updates_ui():
        updates_col.controls = [
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CAMPAIGN_OUTLINED, color=PRIMARY, size=20),
                        ft.Text("Post Community Update | کمیونٹی خبر",
                                size=14, weight=ft.FontWeight.BOLD, color=PRIMARY_DK),
                    ], spacing=8),
                    ft.Container(height=8),
                    ft.Card(
                        elevation=4, shape=ft.RoundedRectangleBorder(radius=16),
                        content=ft.Container(
                            bgcolor=SURFACE, border_radius=16,
                            padding=ft.padding.all(18),
                            content=ft.Column([
                                upd_title, upd_body, upd_color,
                                ft.Container(height=4),
                                post_btn,
                            ], spacing=12),
                        ),
                    ),
                    ft.Container(height=20),

                    ft.Row([
                        ft.Icon(ft.Icons.WIFI_TETHERING_ROUNDED, color=PRIMARY, size=20),
                        ft.Text("Flash Ticker | فلیش ٹکر", size=14,
                                weight=ft.FontWeight.BOLD, color=PRIMARY_DK),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE, icon_color=PRIMARY, icon_size=26,
                            tooltip="Add flash note",
                            on_click=lambda e: _show_flash_dialog(),
                        ),
                    ], spacing=8),
                    ft.Text("Scrolling strip on the Home screen — separate from Community Updates | "
                            "ہوم اسکرین پر سکرولنگ پٹی — کمیونٹی خبروں سے الگ",
                            size=10, color=TEXT_SUB),
                    ft.Container(height=8),
                    flash_list_col,
                ], spacing=6),
            )
        ]
        safe_update()

    # ================================================================
    #  EMPTY STATE
    # ================================================================
    def _empty(emoji: str, text: str) -> ft.Container:
        return ft.Container(
            padding=ft.padding.all(40),
            alignment=ft.Alignment(0, 0),
            content=ft.Column([
                ft.Text(emoji, size=48),
                ft.Text(text, size=13, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        )

    # ================================================================
    #  MAIN DATA LOADER
    # ================================================================
    def load_data(_=None):
        for col in [stats_col, pending_col, requests_col, donations_col]:
            col.controls = [ft.Container(
                padding=ft.padding.all(20),
                content=ft.Row([
                    ft.ProgressRing(color=PRIMARY, width=22, height=22, stroke_width=3),
                    ft.Text("Loading...", color=TEXT_SUB, size=13),
                ], spacing=12),
            )]
        safe_update()

        async def _work():
            try:
                await _restore()
                is_head = role == "head_admin"

                # Stats
                for key, table, filt in [
                    ("members",   "profiles",        None),
                    ("requests",  "blood_requests",  None),
                    ("donors",    "donors",           None),
                    ("pending",   "profiles",          ("is_approved", False)),
                    ("fulfilled", "blood_requests",   ("status", "fulfilled")),
                ]:
                    try:
                        def _count(t=table, f=filt):
                            q = _sb.table(t).select("id", count="exact")
                            if f:
                                q = q.eq(f[0], f[1])
                            return q.execute()
                        res = await asyncio.to_thread(_count)
                        state["stats"][key] = res.count or 0
                    except Exception:
                        pass

                try:
                    def _pend():
                        q = _sb.table("profiles").select("*").eq("is_approved", False).order("created_at", desc=True)
                        if not is_head:
                            q = q.eq("city", sess_get("city", ""))
                        return q.execute()
                    res = await asyncio.to_thread(_pend)
                    all_unapproved = res.data or []
                    state["pending"] = [m for m in all_unapproved if m.get("account_status") != "rejected"]
                    state["rejected"] = [m for m in all_unapproved if m.get("account_status") == "rejected"]
                except Exception:
                    state["pending"] = []
                    state["rejected"] = []

                try:
                    def _reqs():
                        q = _sb.table("blood_requests").select("*").order("created_at", desc=True).limit(30)
                        if not is_head:
                            q = q.eq("city", sess_get("city", ""))
                        return q.execute()
                    res = await asyncio.to_thread(_reqs)
                    state["requests"] = res.data or []
                except Exception:
                    state["requests"] = []

                try:
                    def _dons():
                        return _sb.table("donations").select("*").order("donated_at", desc=True).limit(20).execute()
                    res = await asyncio.to_thread(_dons)
                    state["donations"] = res.data or []
                except Exception:
                    state["donations"] = []

                build_stats_ui()
                build_pending_ui()
                build_requests_ui()
                build_donations_ui()
                build_updates_ui()

            except Exception as ex:
                print(f"[ADMIN] load error: {ex}")
                snack(f"⚠ Load error: {str(ex)[:60]}")

        page.run_task(_work)

    # ================================================================
    #  ⑦ LEADERS MANAGEMENT
    # ================================================================
    def _build_leaders_list(leaders: list):
        leaders_col.controls.clear()

        if is_head_admin:
            leaders_col.controls.append(
                ft.Container(
                    margin=ft.margin.symmetric(horizontal=14, vertical=8),
                    content=ft.ElevatedButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.PERSON_ADD_ROUNDED, color="white", size=18),
                            ft.Container(width=8),
                            ft.Text("Add Leader | لیڈر شامل کریں",
                                    color="white", size=13, weight=ft.FontWeight.W_700),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        style=ft.ButtonStyle(
                            bgcolor=PRIMARY,
                            shape=ft.RoundedRectangleBorder(radius=12),
                        ),
                        width=float("inf"), height=48,
                        on_click=lambda e: _show_leader_dialog(),
                    ),
                )
            )
        else:
            leaders_col.controls.append(
                ft.Container(
                    margin=ft.margin.symmetric(horizontal=14, vertical=8),
                    padding=ft.padding.all(10),
                    border_radius=10, bgcolor="#EEEEEE",
                    content=ft.Text(
                        "🔒 Only Head Admin can add/edit leaders | صرف ہیڈ ایڈمن لیڈر شامل/ترمیم کر سکتا ہے",
                        size=11, color=TEXT_SUB, text_align=ft.TextAlign.CENTER,
                    ),
                )
            )

        if not leaders:
            leaders_col.controls.append(
                _empty("👥", "No leaders yet\nکوئی لیڈر نہیں")
            )
        else:
            for l in leaders:
                leaders_col.controls.append(_leader_card(l))

        safe_update()

    def _leader_card(l: dict) -> ft.Container:
        lid      = l.get("id", "")
        name_ur  = l.get("name_ur", "---")
        name_en  = l.get("name_en") or l.get("name", "")
        title_ur = l.get("title_ur", "---")
        title_en = l.get("title_en") or l.get("title", "")
        phone    = l.get("phone", "")
        img_url  = l.get("image_url", "")
        color    = l.get("color", PRIMARY)
        level    = l.get("level", "central")
        province = l.get("province", "")
        country  = l.get("country", "")

        initials = name_ur[0] if name_ur else "?"

        level_label_map = {
            "central":    "🏛️ Central | مرکزی",
            "provincial": "🗺️ Provincial | صوبائی",
            "overseas":   "🌍 Overseas | بیرون ملک",
        }
        level_label = level_label_map.get(level, level)

        loc_bits = []
        if level == "provincial" and province:
            loc_bits.append(province)
        if level == "overseas" and country:
            loc_bits.append(country)
        location_line = " — ".join(loc_bits)

        return ft.Container(
            bgcolor=SURFACE, border_radius=14,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(12),
            shadow=ft.BoxShadow(blur_radius=6, color="#10000000", offset=ft.Offset(0, 2)),
            content=ft.Row([
                ft.Container(
                    width=50, height=50, border_radius=25,
                    bgcolor=f"{color}22",
                    alignment=ft.Alignment(0, 0),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Image(
                        src=img_url, fit="cover", width=50, height=50,
                        error_content=ft.Text(initials, size=20,
                                              weight=ft.FontWeight.BOLD, color=color),
                    ) if img_url else ft.Text(initials, size=20,
                                               weight=ft.FontWeight.BOLD, color=color),
                ),
                ft.Container(width=12),
                ft.Column([
                    ft.Text(name_ur, size=14, weight=ft.FontWeight.W_700, color=TEXT),
                    ft.Text(name_en, size=11, color=TEXT_SUB),
                    ft.Row([
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            border_radius=8, bgcolor=f"{color}22",
                            content=ft.Text(title_ur, size=10, color=color,
                                            weight=ft.FontWeight.W_600),
                        ),
                        ft.Text(phone, size=10, color=TEXT_SUB) if phone else ft.Container(),
                    ], spacing=8),
                    ft.Row([
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            border_radius=8, bgcolor="#EEEEEE",
                            content=ft.Text(level_label, size=9, color=TEXT_SUB,
                                            weight=ft.FontWeight.W_600),
                        ),
                        ft.Text(f"📍 {location_line}", size=10, color="#9E9E9E") if location_line else ft.Container(),
                    ], spacing=8),
                ], expand=True, spacing=3, tight=True),
                ft.Row([
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED,
                        icon_color=BLUE, icon_size=20,
                        tooltip="Edit | ترمیم",
                        on_click=lambda e, leader=l: _show_leader_dialog(leader),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_color=PRIMARY, icon_size=20,
                        tooltip="Delete | حذف",
                        on_click=lambda e, i=lid: _delete_leader(i),
                    ),
                ], spacing=0) if is_head_admin else ft.Container(),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def _delete_leader(lid: str):
        if not is_head_admin:
            snack("🔒 Only Head Admin can remove leaders", ORANGE)
            return
        async def _do():
            try:
                await _restore()
                def _del():
                    _sb.table("leaders").delete().eq("id", lid).execute()
                await asyncio.to_thread(_del)
                snack("✅ Leader removed!", GREEN)
                _load_leaders()
            except Exception as ex:
                snack(f"⚠ {str(ex)[:50]}")
        page.run_task(_do)

    def _show_leader_dialog(leader: dict = None):
        if not is_head_admin:
            snack("🔒 Only Head Admin can add/edit leaders", ORANGE)
            return
        is_edit = leader is not None
        lid = leader.get("id", "") if leader else ""

        def gv(key, default=""):
            if leader:
                val = leader.get(key, default)
                return str(val) if val is not None else default
            return default

        name_ur_f  = ft.TextField(label="Name Urdu | اردو نام *",
            border_radius=12, focused_border_color=PRIMARY,
            value=gv("name_ur"))
        name_en_f  = ft.TextField(label="Name English | انگریزی نام",
            border_radius=12, focused_border_color=PRIMARY,
            value=gv("name_en") or gv("name"))
        title_ur_f = ft.TextField(label="Title Urdu | اردو عہدہ *",
            border_radius=12, focused_border_color=PRIMARY,
            value=gv("title_ur"))
        title_en_f = ft.TextField(label="Title English | انگریزی عہدہ",
            border_radius=12, focused_border_color=PRIMARY,
            value=gv("title_en") or gv("title"))

        level_f = ft.Dropdown(
            label="Level | سطح *",
            border_radius=12, focused_border_color=PRIMARY,
            value=gv("level", "central"),
            options=[ft.dropdown.Option(k, lbl) for k, lbl in LEADER_LEVELS],
        )

        province_f = ft.Dropdown(
            label="Province | صوبہ",
            border_radius=12, focused_border_color=PRIMARY,
            value=gv("province"),
            options=[ft.dropdown.Option(p) for p in PROVINCES],
            visible=gv("level", "central") == "provincial",
        )
        province_slot = ft.Container(content=province_f)

        country_f = ft.Dropdown(
            label="Country | ملک",
            border_radius=12, focused_border_color=PRIMARY,
            value=gv("country") or "Pakistan",
            options=[ft.dropdown.Option(c) for c in COUNTRIES],
            visible=gv("level", "central") == "overseas",
        )
        country_slot = ft.Container(content=country_f)

        # ── Safe Country Code Extractor ────────────────────────────
        def _current_phone_code() -> str:
            if level_f.value == "overseas":
                codes_dict = {}
                if isinstance(COUNTRY_PHONE_CODES, list):
                    for item in COUNTRY_PHONE_CODES:
                        if isinstance(item, dict):
                            c_name = item.get("country") or item.get("name")
                            c_code = item.get("code") or item.get("phone_code")
                            if c_name and c_code:
                                codes_dict[c_name] = c_code
                        elif isinstance(item, (list, tuple)) and len(item) >= 3:
                            codes_dict[item[0]] = item[2]
                        elif isinstance(item, (list, tuple)) and len(item) == 2:
                            codes_dict[item[0]] = item[1]
                elif isinstance(COUNTRY_PHONE_CODES, dict):
                    codes_dict = COUNTRY_PHONE_CODES
                return codes_dict.get(country_f.value, DEFAULT_COUNTRY_CODE)
            return DEFAULT_COUNTRY_CODE

        # ── TextField with ft.Text Control prefix ──────────────────
        phone_f = ft.TextField(
            label="Phone | فون",
            border_radius=12, focused_border_color=PRIMARY,
            keyboard_type=ft.KeyboardType.PHONE,
            value=gv("phone"),
            prefix=ft.Text(f"{_current_phone_code()} "),
        )

        def _update_phone_code():
            code_str = f"{_current_phone_code()} "
            if isinstance(phone_f.prefix, ft.Text):
                phone_f.prefix.value = code_str
            else:
                phone_f.prefix = ft.Text(code_str)
            try:
                phone_f.update()
            except Exception:
                pass

        color_f    = ft.Dropdown(
            label="Color | رنگ", border_radius=12,
            focused_border_color=PRIMARY,
            value=gv("color", PRIMARY),
            options=[
                ft.dropdown.Option(PRIMARY,   "🔴 Red"),
                ft.dropdown.Option("#C62828", "🔴 Dark Red"),
                ft.dropdown.Option(BLUE,      "🔵 Blue"),
                ft.dropdown.Option(GREEN,     "🟢 Green"),
                ft.dropdown.Option(ORANGE,    "🟠 Orange"),
                ft.dropdown.Option("#6A1B9A", "🟣 Purple"),
                ft.dropdown.Option("#00695C", "🩵 Teal"),
            ],
        )
        order_f = ft.TextField(
            label="Display Order | ترتیب (1,2,3...)",
            border_radius=12, focused_border_color=PRIMARY,
            keyboard_type=ft.KeyboardType.NUMBER,
            value=str(gv("display_order", "0")),
        )

        def _update_level_visibility():
            lvl = level_f.value
            province_f.visible = (lvl == "provincial")
            country_f.visible = (lvl == "overseas")
            _update_phone_code()

        def _on_level_change(e=None):
            _update_level_visibility()
            try:
                province_f.update()
                country_f.update()
            except Exception:
                pass
            page.update()

        def _on_country_change(e=None):
            _update_phone_code()
            page.update()

        level_f.on_change = _on_level_change
        country_f.on_change = _on_country_change

        img_url_state = [gv("image_url", "")]
        img_label = ft.Text(
            "📎 " + (img_url_state[0].split("/")[-1] if img_url_state[0] else "No image selected"),
            size=11, color=PRIMARY if img_url_state[0] else TEXT_SUB,
            italic=not img_url_state[0],
        )

        # ── Image Upload logic with UNIQUE FILENAME generator ──────
        async def _pick_image(e=None):
            try:
                from home_module.media_picker import MediaPickerManager, PickedFile
                at = sess_get("access_token", "")
                mm = MediaPickerManager(page, access_token=at)

                def on_picked(picked: PickedFile):
                    async def _upload():
                        def on_done(url: str, is_vid: bool):
                            img_url_state[0] = url
                            img_label.value = f"📎 {picked.name}"
                            img_label.color = PRIMARY
                            img_label.italic = False
                            try:
                                img_label.update()
                            except Exception:
                                pass
                            snack("✅ Image uploaded!", GREEN)

                        ext = picked.name.split(".")[-1] if "." in picked.name else "jpg"
                        unique_name = f"leader_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}.{ext}"
                        dynamic_bucket_path = f"leaders/photos/{unique_name}"

                        await mm.upload_attached_async(
                            bucket_path=dynamic_bucket_path,
                            on_complete=on_done,
                        )
                    page.run_task(_upload)

                await mm.attach_media_async(
                    allowed_extensions=["jpg", "jpeg", "png", "webp"],
                    on_picked=on_picked,
                )
            except Exception as ex:
                snack(f"❌ {str(ex)[:50]}")

        upload_btn = ft.OutlinedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.UPLOAD_FILE_ROUNDED, color=PRIMARY, size=16),
                ft.Container(width=6),
                ft.Text("Upload Photo | تصویر اپلوڈ کریں", color=PRIMARY, size=12),
            ], spacing=0, tight=True),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, PRIMARY_MD),
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            on_click=lambda e: page.run_task(_pick_image),
        )

        def _close(e=None):
            try:
                dlg.open = False
                page.update()
            except Exception:
                pass

        def _save(e=None):
            if not name_ur_f.value or not title_ur_f.value:
                snack("⚠ Urdu name and title required!")
                return
            if not level_f.value:
                snack("⚠ Please select a level (Central/Provincial/Overseas)!")
                return
            if level_f.value == "provincial" and not province_f.value:
                snack("⚠ Please select a province!")
                return
            if level_f.value == "overseas" and not country_f.value:
                snack("⚠ Please select a country!")
                return

            async def _do():
                try:
                    await _restore()

                    lvl = level_f.value
                    raw_phone = (phone_f.value or "").strip()
                    code = _current_phone_code()
                    if raw_phone and not raw_phone.startswith("+"):
                        full_phone = f"{code} {raw_phone}"
                    else:
                        full_phone = raw_phone or None

                    payload = {
                        "name_ur":       name_ur_f.value.strip(),
                        "name_en":       name_en_f.value.strip() or None,
                        "title_ur":      title_ur_f.value.strip(),
                        "title_en":      title_en_f.value.strip() or None,
                        "phone":         full_phone,
                        "image_url":     img_url_state[0] or None,
                        "color":         color_f.value or PRIMARY,
                        "display_order": int(order_f.value or 0),
                        "level":         lvl,
                        "province":      province_f.value if lvl == "provincial" else None,
                        "country":       country_f.value if lvl == "overseas" else None,
                    }

                    def _upsert():
                        if is_edit:
                            _sb.table("leaders").update(payload).eq("id", lid).execute()
                        else:
                            _sb.table("leaders").insert(payload).execute()

                    await asyncio.to_thread(_upsert)
                    snack(f"✅ Leader {'updated' if is_edit else 'added'}!", GREEN)
                    _close()
                    _load_leaders()
                except Exception as ex:
                    snack(f"⚠ {str(ex)[:60]}")

            page.run_task(_do)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Edit Leader | ترمیم" if is_edit else "Add Leader | لیڈر شامل کریں",
                weight=ft.FontWeight.BOLD, color=PRIMARY,
            ),
            content=ft.Container(
                width=320,
                content=ft.Column([
                    name_ur_f, name_en_f,
                    title_ur_f, title_en_f,
                    level_f,
                    province_slot,
                    country_slot,
                    phone_f,
                    ft.Container(height=4),
                    upload_btn,
                    img_label,
                    ft.Container(height=4),
                    color_f, order_f,
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cancel | منسوخ", on_click=_close,
                              style=ft.ButtonStyle(color=TEXT_SUB)),
                ft.ElevatedButton(
                    "Save | محفوظ کریں",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY, color="white",
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _load_leaders():
        async def _do():
            try:
                await _restore()
                def _fetch():
                    return (
                        _sb.table("leaders")
                        .select("*")
                        .order("display_order", desc=False)
                        .execute()
                    )
                res = await asyncio.to_thread(_fetch)
                _build_leaders_list(res.data or [])
            except Exception as ex:
                snack(f"⚠ {str(ex)[:60]}")
        page.run_task(_do)

    # ================================================================
    #  TAB CHANGE
    # ================================================================
    def _on_tab_change(e):
        try:
            idx = int(e.data)
            if idx == 4:
                _load_users()
            elif idx == 5:
                _load_flash_notes()
            elif idx == 6:
                _load_leaders()
        except Exception:
            pass

    # ================================================================
    #  TABS
    # ================================================================
    tab_views = [
        stats_col,
        pending_col,
        requests_col,
        donations_col,
        users_col,
        updates_col,
        leaders_col,
    ]

    tabs = ft.Tabs(
        length=7,
        selected_index=0,
        expand=True,
        animation_duration=200,
        on_change=_on_tab_change,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Stats",     icon=ft.Icons.DASHBOARD_OUTLINED),
                        ft.Tab(label="Members",   icon=ft.Icons.PEOPLE_OUTLINED),
                        ft.Tab(label="Requests",  icon=ft.Icons.BLOODTYPE_OUTLINED),
                        ft.Tab(label="Donations", icon=ft.Icons.FAVORITE_OUTLINED),
                        ft.Tab(label="Users",     icon=ft.Icons.MANAGE_ACCOUNTS_OUTLINED),
                        ft.Tab(label="Updates",   icon=ft.Icons.CAMPAIGN_OUTLINED),
                        ft.Tab(label="Leaders",   icon=ft.Icons.MILITARY_TECH_OUTLINED),
                    ]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=tab_views,
                )
            ]
        )
    )

    # ── Support Requests ────────────────────────────────────
    def _show_support_requests(e=None):
        if not is_head_admin:
            snack("🔒 Only Head Admin can view/respond to support requests", ORANGE)
            return
        try:
            res = (
                supabase.table("support_requests")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            requests = res.data or []
        except Exception as ex:
            snack(f"Error loading support requests: {str(ex)[:60]}", PRIMARY_DK)
            return

        status_meta = {
            "open":        (ORANGE_LT, ORANGE, "🟠"),
            "in_progress": (BLUE_LT,   BLUE,   "🔵"),
            "closed":      (GREEN_LT,  GREEN,  "✅"),
        }

        def _resolve(req_id):
            try:
                supabase.table("support_requests").update(
                    {"status": "closed"}
                ).eq("id", req_id).execute()
                snack("Marked resolved | حل شدہ نشان زد", GREEN)
                _close()
                _show_support_requests()
            except Exception as ex:
                snack(f"Error: {str(ex)[:60]}", PRIMARY_DK)

        rows = []
        for r in requests:
            st = r.get("status", "open")
            bg, tc, em = status_meta.get(st, (ORANGE_LT, ORANGE, "🟠"))
            rows.append(
                ft.Container(
                    bgcolor=bg, border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    margin=ft.margin.only(bottom=6),
                    content=ft.Row([
                        ft.Text(em, size=16),
                        ft.Container(width=8),
                        ft.Column([
                            ft.Text(r.get("name") or "Guest | مہمان", size=13,
                                    weight=ft.FontWeight.W_600, color=TEXT),
                            ft.Text(r.get("phone") or "", size=10, color=TEXT_SUB),
                            ft.Text(r.get("message", ""), size=11, color=TEXT,
                                    max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                        ], spacing=2, expand=True, tight=True),
                        (
                            ft.TextButton(
                                "Resolve", icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                                on_click=lambda e, rid=r.get("id"): _resolve(rid),
                            )
                            if st != "closed" else
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                border_radius=8, bgcolor=f"{tc}22",
                                content=ft.Text("CLOSED", size=9, color=tc,
                                                 weight=ft.FontWeight.BOLD),
                            )
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )

        if not rows:
            rows = [ft.Text("No support requests yet | ابھی کوئی درخواست نہیں",
                            size=13, color=TEXT_SUB)]

        def _close(e=None):
            try:
                dlg.open = False
                page.update()
            except Exception:
                pass

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Support Requests | معاون درخواستیں",
                          weight=ft.FontWeight.BOLD, color=PRIMARY),
            content=ft.Container(
                width=340, height=380,
                content=ft.Column(rows, spacing=0, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[ft.TextButton("Close | بند کریں", on_click=_close)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # Initial load
    load_data()
    build_updates_ui()
    _load_flash_notes()
    _load_leaders()

    # ================================================================
    #  RETURN VIEW
    # ================================================================
    return ft.View(
        route="/admin",
        bgcolor=BG,
        padding=0,
        appbar=ft.AppBar(
            leading=ft.Container(
                padding=ft.padding.only(left=12),
                content=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED, color="white", size=26),
            ),
            leading_width=48,
            title=ft.Column([
                ft.Text("Admin Panel | ایڈمن پینل", size=15,
                        weight=ft.FontWeight.BOLD, color="white"),
                ft.Text(f"Role: {role.upper()}", size=10, color=PRIMARY_MD),
            ], spacing=0),
            bgcolor=PRIMARY,
            actions=(
                [
                    ft.IconButton(ft.Icons.SUPPORT_AGENT_ROUNDED, icon_color="white",
                                  on_click=_show_support_requests, tooltip="Support Requests | معاون درخواستیں"),
                ] if is_head_admin else []
            ) + [
                ft.IconButton(ft.Icons.REFRESH_ROUNDED, icon_color="white",
                              on_click=load_data, tooltip="Refresh"),
                ft.IconButton(ft.Icons.HOME_ROUNDED, icon_color="white",
                              on_click=lambda _: page.go("/home"), tooltip="Home"),
            ],
        ),
        controls=[tabs],
    )



