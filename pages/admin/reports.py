# ================================================================
#  pages/admin/reports.py  —  Reports & Analytics
#  Real Supabase data | Area-wise | Blood group stats
#  Flet 0.84 compatible | Session-safe
# ================================================================
from core.theme import Theme 
import asyncio
import flet as ft
from supabase import create_client
from services.database.db import SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options
from datetime import datetime, timezone, timedelta

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
PURPLE     = "#6A1B9A"
BG         = "#FFF5F5"
TEXT       = "#212121"
TEXT_SUB   = "#757575"
SURFACE    = "#FFFFFF"

BLOOD_COLORS = {
    "A+":  "#E53935", "A-":  "#C62828",
    "B+":  "#1565C0", "B-":  "#0D47A1",
    "AB+": "#6A1B9A", "AB-": "#4A148C",
    "O+":  "#2E7D32", "O-":  "#1B5E20",
}


def view(page: ft.Page) -> ft.View:

    # ── Session helpers ─────────────────────────────────────
    def sess_get(key, default=""):
        try:
            if hasattr(page.session, "_Session__store"):
                return page.session._Session__store.get(key) or default
            return page.session.get(key) or default
        except Exception:
            return default

    _sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())

    async def _restore():
        try:
            at = sess_get("access_token")
            rt = sess_get("refresh_token", "")
            if at:
                await asyncio.to_thread(_sb.auth.set_session, at, rt)
        except Exception:
            pass

    def snack(msg, color=PRIMARY):
        async def _show():
            try:
                sb = ft.SnackBar(
                    content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD),
                    bgcolor=color, duration=3000,
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
        "stats":        {},
        "blood_stats":  {},
        "city_stats":   {},
        "recent":       [],
        "monthly":      {},
        "top_donors":   [],
    }

    # ── Content column ───────────────────────────────────────
    content_col = ft.Column(
        spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
    )

    # ================================================================
    #  UI HELPERS
    # ================================================================
    def _stat_card(icon, title, value, color, subtitle="") -> ft.Container:
        return ft.Container(
            expand=True, height=90,
            border_radius=16, bgcolor=color,
            shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0,3)),
            padding=ft.padding.all(12),
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color="white", size=20),
                    ft.Text(str(value), size=24,
                            weight=ft.FontWeight.BOLD, color="white"),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(title, size=11, color="white"),
                ft.Text(subtitle, size=9, color="white70") if subtitle else ft.Container(height=0),
            ], spacing=2, tight=True),
        )

    def _section(title: str, icon=None) -> ft.Container:
        return ft.Container(
            padding=ft.padding.only(left=14, right=14, top=16, bottom=6),
            content=ft.Row([
                ft.Icon(icon, color=PRIMARY, size=18) if icon else ft.Container(),
                ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=PRIMARY_DK),
            ], spacing=8),
        )

    def _divider():
        return ft.Container(
            height=1, bgcolor=PRIMARY_MD,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
        )

    def _empty(emoji, text):
        return ft.Container(
            padding=ft.padding.all(24),
            alignment=ft.Alignment(0, 0),
            content=ft.Column([
                ft.Text(emoji, size=36),
                ft.Text(text, size=12, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
        )

    # ================================================================
    #  BLOOD GROUP BAR CHART
    # ================================================================
    def _blood_group_chart(blood_stats: dict) -> ft.Container:
        if not blood_stats:
            return _empty("🩸", "No data")

        max_val = max(blood_stats.values()) or 1
        bars = []

        for bg, count in sorted(blood_stats.items(), key=lambda x: -x[1]):
            pct    = count / max_val
            color  = BLOOD_COLORS.get(bg, PRIMARY)
            width  = max(30, int(220 * pct))

            bars.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=3),
                    content=ft.Row([
                        ft.Container(
                            width=36,
                            content=ft.Text(bg, size=11,
                                            weight=ft.FontWeight.BOLD, color=color),
                        ),
                        ft.Container(
                            width=width, height=22, border_radius=6,
                            bgcolor=color,
                            alignment=ft.Alignment(1, 0),
                            padding=ft.padding.only(right=6),
                            content=ft.Text(str(count), size=10,
                                            color="white", weight=ft.FontWeight.BOLD),
                        ),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )

        return ft.Container(
            bgcolor=SURFACE, border_radius=16,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(14),
            shadow=ft.BoxShadow(blur_radius=6, color="#10000000", offset=ft.Offset(0,2)),
            content=ft.Column(bars, spacing=2, tight=True),
        )

    # ================================================================
    #  CITY/AREA STATS
    # ================================================================
    def _city_stats_card(city_stats: dict) -> ft.Container:
        if not city_stats:
            return _empty("📍", "No area data")

        rows = []
        for i, (city, data) in enumerate(
            sorted(city_stats.items(), key=lambda x: -x[1].get("requests", 0))[:10]
        ):
            requests  = data.get("requests", 0)
            donations = data.get("donations", 0)
            bg = PRIMARY_LT if i % 2 == 0 else SURFACE

            rows.append(
                ft.Container(
                    bgcolor=bg, border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Row([
                        ft.Text(f"{i+1}.", size=11, color=TEXT_SUB, width=20),
                        ft.Text(city, size=13, weight=ft.FontWeight.W_600,
                                color=TEXT, expand=True),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            border_radius=8, bgcolor=PRIMARY_LT,
                            content=ft.Text(f"🩸 {requests}", size=10,
                                            color=PRIMARY, weight=ft.FontWeight.BOLD),
                        ),
                        ft.Container(width=6),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            border_radius=8, bgcolor=GREEN_LT,
                            content=ft.Text(f"💉 {donations}", size=10,
                                            color=GREEN, weight=ft.FontWeight.BOLD),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )

        return ft.Container(
            bgcolor=SURFACE, border_radius=16,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(12),
            shadow=ft.BoxShadow(blur_radius=6, color="#10000000", offset=ft.Offset(0,2)),
            content=ft.Column([
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                    content=ft.Row([
                        ft.Container(width=20),
                        ft.Text("Area", size=11, color=TEXT_SUB, expand=True),
                        ft.Text("Requests", size=10, color=PRIMARY),
                        ft.Container(width=6),
                        ft.Text("Donations", size=10, color=GREEN),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ),
                *rows,
            ], spacing=2, tight=True),
        )

    # ================================================================
    #  TOP DONORS
    # ================================================================
    def _top_donors_list(donors: list) -> ft.Column:
        if not donors:
            return ft.Column([_empty("🏆", "No donors yet")])

        cards = []
        medals = ["🥇", "🥈", "🥉"]

        for i, d in enumerate(donors[:10]):
            medal  = medals[i] if i < 3 else f"{i+1}."
            blood  = d.get("blood_group", "?")
            bc     = BLOOD_COLORS.get(blood, PRIMARY)
            name   = d.get("full_name", "---")
            city   = d.get("city", "")
            count  = d.get("total_donations", 0)
            badge  = d.get("donor_badge", "")

            badge_map = {
                "first_drop": "🌱", "helper": "💪",
                "hero": "⭐", "legend": "👑",
            }
            badge_emoji = badge_map.get(badge, "")

            cards.append(
                ft.Container(
                    bgcolor=SURFACE, border_radius=14,
                    margin=ft.margin.symmetric(horizontal=14, vertical=3),
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    shadow=ft.BoxShadow(blur_radius=4, color="#10000000", offset=ft.Offset(0,1)),
                    content=ft.Row([
                        ft.Text(medal, size=18, width=32),
                        ft.Container(
                            width=38, height=38, border_radius=19,
                            bgcolor=f"{bc}22", alignment=ft.Alignment(0,0),
                            content=ft.Text(blood, size=11,
                                            weight=ft.FontWeight.BOLD, color=bc),
                        ),
                        ft.Container(width=8),
                        ft.Column([
                            ft.Row([
                                ft.Text(name, size=13,
                                        weight=ft.FontWeight.W_700, color=TEXT),
                                ft.Text(badge_emoji, size=14),
                            ], spacing=4),
                            ft.Text(f"📍 {city}", size=11, color=TEXT_SUB),
                        ], expand=True, spacing=2, tight=True),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            border_radius=10, bgcolor=PRIMARY_LT,
                            content=ft.Text(f"💉 {count}", size=12,
                                            color=PRIMARY, weight=ft.FontWeight.BOLD),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )
        return ft.Column(cards, spacing=0)

    # ================================================================
    #  RECENT ACTIVITY
    # ================================================================
    def _recent_activity(items: list) -> ft.Column:
        if not items:
            return ft.Column([_empty("📋", "No recent activity")])

        status_map = {
            "pending":     ("⏳", ORANGE),
            "matching":    ("🔍", BLUE),
            "in_progress": ("✅", GREEN),
            "fulfilled":   ("🎉", GREEN),
            "cancelled":   ("❌", TEXT_SUB),
        }

        rows = []
        for r in items[:15]:
            status = r.get("status") or "pending"
            em, tc = status_map.get(status, ("📌", TEXT_SUB))
            blood  = r.get("required_blood_group") or r.get("blood_group", "?")
            city   = r.get("city", "")
            date   = str(r.get("created_at", ""))[:10]
            patient = r.get("patient_name", "---")

            rows.append(
                ft.Container(
                    bgcolor=SURFACE, border_radius=10,
                    margin=ft.margin.symmetric(horizontal=14, vertical=2),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Row([
                        ft.Text(em, size=16, width=24),
                        ft.Container(
                            width=34, height=34, border_radius=17,
                            bgcolor=PRIMARY_LT, alignment=ft.Alignment(0,0),
                            content=ft.Text(blood, size=9,
                                            weight=ft.FontWeight.BOLD, color=PRIMARY),
                        ),
                        ft.Container(width=8),
                        ft.Column([
                            ft.Text(patient, size=12,
                                    weight=ft.FontWeight.W_600, color=TEXT),
                            ft.Text(f"📍 {city} — {date}",
                                    size=10, color=TEXT_SUB),
                        ], expand=True, spacing=1, tight=True),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            border_radius=6, bgcolor=f"{tc}22",
                            content=ft.Text(status.upper(), size=8,
                                            color=tc, weight=ft.FontWeight.BOLD),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )
        return ft.Column(rows, spacing=0)

    # ================================================================
    #  MONTHLY SUMMARY CARD
    # ================================================================
    def _monthly_card(monthly: dict) -> ft.Container:
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        data = monthly.get(this_month, {})

        return ft.Container(
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(16),
            border_radius=16,
            bgcolor=PRIMARY,
            shadow=ft.BoxShadow(blur_radius=10, color="#33C62828", offset=ft.Offset(0,4)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CALENDAR_MONTH, color="white", size=20),
                    ft.Text("This Month | اس ماہ", size=14,
                            weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text(datetime.now().strftime("%B %Y"),
                            size=12, color=PRIMARY_MD),
                ], spacing=8),
                ft.Container(height=10),
                ft.Row([
                    _mini_stat("🩸", "Requests", data.get("requests", 0)),
                    _mini_stat("💉", "Donations", data.get("donations", 0)),
                    _mini_stat("👥", "New Members", data.get("members", 0)),
                    _mini_stat("✅", "Fulfilled", data.get("fulfilled", 0)),
                ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
            ], spacing=0),
        )

    def _mini_stat(emoji, label, val) -> ft.Column:
        return ft.Column([
            ft.Text(emoji, size=20, text_align=ft.TextAlign.CENTER),
            ft.Text(str(val), size=20, weight=ft.FontWeight.BOLD,
                    color="white", text_align=ft.TextAlign.CENTER),
            ft.Text(label, size=9, color=PRIMARY_MD,
                    text_align=ft.TextAlign.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2, tight=True)

    # ================================================================
    #  BUILD UI
    # ================================================================
    def build_ui():
        s  = state["stats"]
        bs = state["blood_stats"]
        cs = state["city_stats"]

        controls = [
            # ── Overall Stats ──
            _section("Overall Stats | مجموعی اعداد", ft.Icons.DASHBOARD_ROUNDED),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=4),
                content=ft.Column([
                    ft.Row([
                        _stat_card(ft.Icons.PEOPLE_ROUNDED, "Total Members\nکل ممبران",
                                   s.get("members",0), PRIMARY),
                        _stat_card(ft.Icons.BLOODTYPE_ROUNDED, "Total Requests\nکل درخواستیں",
                                   s.get("requests",0), "#E53935"),
                    ], spacing=10),
                    ft.Container(height=8),
                    ft.Row([
                        _stat_card(ft.Icons.FAVORITE_ROUNDED, "Total Donations\nکل عطیات",
                                   s.get("donations",0), GREEN),
                        _stat_card(ft.Icons.CHECK_CIRCLE_ROUNDED, "Fulfilled\nمکمل",
                                   s.get("fulfilled",0), BLUE),
                    ], spacing=10),
                    ft.Container(height=8),
                    ft.Row([
                        _stat_card(ft.Icons.PENDING_ACTIONS, "Pending\nزیر التواء",
                                   s.get("pending",0), ORANGE),
                        _stat_card(ft.Icons.STAR_ROUNDED, "Avg Rating\nاوسط ریٹنگ",
                                   f"{s.get('avg_rating',0):.1f}⭐", PURPLE),
                    ], spacing=10),
                ], spacing=0),
            ),

            # ── Monthly Summary ──
            _section("This Month | اس ماہ", ft.Icons.CALENDAR_MONTH),
            _monthly_card(state["monthly"]),

            # ── Blood Group Stats ──
            _section("Blood Group Demand | خون گروپ", ft.Icons.BLOODTYPE_ROUNDED),
            _blood_group_chart(bs),

            # ── Area Stats ──
            _section("Area-wise Stats | علاقہ وار", ft.Icons.LOCATION_ON_ROUNDED),
            _city_stats_card(cs),

            # ── Top Donors ──
            _section("Top Donors | بہترین ڈونرز", ft.Icons.MILITARY_TECH_ROUNDED),
            _top_donors_list(state["top_donors"]),

            # ── Recent Activity ──
            _section("Recent Requests | حالیہ درخواستیں", ft.Icons.HISTORY_ROUNDED),
            _recent_activity(state["recent"]),

            ft.Container(height=40),
        ]

        content_col.controls = controls
        try:
            page.update()
        except Exception:
            pass

    # ================================================================
    #  DATA LOADER
    # ================================================================
    def load_data(_=None):
        content_col.controls = [
            ft.Container(
                expand=True, padding=ft.padding.all(40),
                alignment=ft.Alignment(0, 0),
                content=ft.Column([
                    ft.ProgressRing(color=PRIMARY, width=48, height=48, stroke_width=4),
                    ft.Container(height=12),
                    ft.Text("Loading reports...", size=13, color=TEXT_SUB),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, tight=True),
            )
        ]
        try:
            page.update()
        except Exception:
            pass

        async def _work():
            try:
                await _restore()
                now = datetime.now(timezone.utc)
                this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

                # ── Overall stats ──
                for key, table, filt in [
                    ("members",   "members",        None),
                    ("requests",  "blood_requests",  None),
                    ("donations", "donations",       None),
                    ("fulfilled", "blood_requests",  ("status", "fulfilled")),
                    ("pending",   "blood_requests",  ("status", "pending")),
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

                # Avg rating
                try:
                    def _rating():
                        return _sb.table("feedback").select("requester_rating").execute()
                    rr = await asyncio.to_thread(_rating)
                    ratings = [r["requester_rating"] for r in (rr.data or []) if r.get("requester_rating")]
                    state["stats"]["avg_rating"] = sum(ratings)/len(ratings) if ratings else 0
                except Exception:
                    state["stats"]["avg_rating"] = 0

                # ── Blood group stats (from requests) ──
                try:
                    def _blood():
                        return _sb.table("blood_requests").select("required_blood_group").execute()
                    br = await asyncio.to_thread(_blood)
                    blood_count = {}
                    for r in (br.data or []):
                        bg = r.get("required_blood_group","")
                        if bg:
                            blood_count[bg] = blood_count.get(bg, 0) + 1
                    state["blood_stats"] = blood_count
                except Exception:
                    pass

                # ── City stats ──
                try:
                    def _reqs():
                        return _sb.table("blood_requests").select("city, status").execute()
                    def _dons():
                        return _sb.table("donations").select("city").execute()

                    req_res = await asyncio.to_thread(_reqs)
                    don_res = await asyncio.to_thread(_dons)

                    city_data = {}
                    for r in (req_res.data or []):
                        c = r.get("city","").strip()
                        if c:
                            if c not in city_data:
                                city_data[c] = {"requests": 0, "donations": 0}
                            city_data[c]["requests"] += 1

                    for d in (don_res.data or []):
                        c = d.get("city","").strip()
                        if c:
                            if c not in city_data:
                                city_data[c] = {"requests": 0, "donations": 0}
                            city_data[c]["donations"] += 1

                    state["city_stats"] = city_data
                except Exception:
                    pass

                # ── Monthly stats ──
                try:
                    def _month_reqs():
                        return (
                            _sb.table("blood_requests")
                            .select("status, created_at")
                            .gte("created_at", this_month_start)
                            .execute()
                        )
                    def _month_dons():
                        return (
                            _sb.table("donations")
                            .select("id")
                            .gte("donated_at", this_month_start)
                            .execute()
                        )
                    def _month_members():
                        return (
                            _sb.table("members")
                            .select("id", count="exact")
                            .gte("created_at", this_month_start)
                            .execute()
                        )

                    mr = await asyncio.to_thread(_month_reqs)
                    md = await asyncio.to_thread(_month_dons)
                    mm = await asyncio.to_thread(_month_members)

                    this_month = now.strftime("%Y-%m")
                    fulfilled  = sum(1 for r in (mr.data or []) if r.get("status") == "fulfilled")

                    state["monthly"][this_month] = {
                        "requests":  len(mr.data or []),
                        "donations": len(md.data or []),
                        "members":   mm.count or 0,
                        "fulfilled": fulfilled,
                    }
                except Exception:
                    pass

                # ── Top donors ──
                try:
                    def _top():
                        return (
                            _sb.table("members")
                            .select("full_name, blood_group, city, total_donations, donor_badge")
                            .gt("total_donations", 0)
                            .order("total_donations", desc=True)
                            .limit(10)
                            .execute()
                        )
                    tr = await asyncio.to_thread(_top)
                    state["top_donors"] = tr.data or []
                except Exception:
                    pass

                # ── Recent requests ──
                try:
                    def _recent():
                        return (
                            _sb.table("blood_requests")
                            .select("*")
                            .order("created_at", desc=True)
                            .limit(15)
                            .execute()
                        )
                    rr = await asyncio.to_thread(_recent)
                    state["recent"] = rr.data or []
                except Exception:
                    pass

                build_ui()

            except Exception as ex:
                print(f"[REPORTS] error: {ex}")
                content_col.controls = [
                    ft.Container(
                        padding=ft.padding.all(40),
                        content=ft.Column([
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color=PRIMARY, size=48),
                            ft.Text(f"Error: {str(ex)[:80]}", color=PRIMARY,
                                    text_align=ft.TextAlign.CENTER, size=12),
                            ft.TextButton("Retry | دوبارہ", on_click=load_data),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    )
                ]
                try:
                    page.update()
                except Exception:
                    pass

        page.run_task(_work)

    # Initial load
    load_data()

    # ================================================================
    #  RETURN VIEW
    # ================================================================
    return ft.View(
        route="/admin/reports",
        bgcolor=BG,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/admin"),
            ),
            title=ft.Column([
                ft.Text("Reports & Analytics", size=15,
                        weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("رپورٹس اور تجزیہ", size=11, color=PRIMARY_MD),
            ], spacing=0),
            bgcolor=PRIMARY,
            actions=[
                ft.IconButton(
                    ft.Icons.REFRESH_ROUNDED,
                    icon_color="white",
                    on_click=load_data,
                    tooltip="Refresh",
                ),
            ],
        ),
        controls=[
            ft.Column(
                expand=True, spacing=0,
                controls=[
                    ft.Container(
                        expand=True,
                        content=content_col,
                    ),
                ],
            ),
        ],
    )

























# # ================================================================
# #  pages/admin/reports.py  —  Reports & Analytics
# #  Real Supabase data | Area-wise | Blood group stats
# #  Flet 0.84 compatible | Session-safe
# # ================================================================
# from core.theme import Theme 
# import asyncio
# import flet as ft
# from supabase import create_client
# from services.database.db import SUPABASE_URL_STR, SUPABASE_KEY_STR
# from datetime import datetime, timezone, timedelta

# PRIMARY    = "#C62828"
# PRIMARY_LT = "#FFEBEE"
# PRIMARY_MD = "#FFCDD2"
# PRIMARY_DK = "#B71C1C"
# GREEN      = "#2E7D32"
# GREEN_LT   = "#E8F5E9"
# BLUE       = "#1565C0"
# BLUE_LT    = "#E3F2FD"
# ORANGE     = "#E65100"
# ORANGE_LT  = "#FFF3E0"
# PURPLE     = "#6A1B9A"
# BG         = "#FFF5F5"
# TEXT       = "#212121"
# TEXT_SUB   = "#757575"
# SURFACE    = "#FFFFFF"

# BLOOD_COLORS = {
#     "A+":  "#E53935", "A-":  "#C62828",
#     "B+":  "#1565C0", "B-":  "#0D47A1",
#     "AB+": "#6A1B9A", "AB-": "#4A148C",
#     "O+":  "#2E7D32", "O-":  "#1B5E20",
# }


# def view(page: ft.Page) -> ft.View:

#     # ── Session helpers ─────────────────────────────────────
#     def sess_get(key, default=""):
#         try:
#             if hasattr(page.session, "_Session__store"):
#                 return page.session._Session__store.get(key) or default
#             return page.session.get(key) or default
#         except Exception:
#             return default

#     _sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR)

#     async def _restore():
#         try:
#             at = sess_get("access_token")
#             rt = sess_get("refresh_token", "")
#             if at:
#                 await asyncio.to_thread(_sb.auth.set_session, at, rt)
#         except Exception:
#             pass

#     def snack(msg, color=PRIMARY):
#         async def _show():
#             try:
#                 sb = ft.SnackBar(
#                     content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD),
#                     bgcolor=color, duration=3000,
#                 )
#                 page.overlay.append(sb)
#                 sb.open = True
#                 page.update()
#             except Exception:
#                 pass
#         try:
#             page.run_task(_show)
#         except Exception:
#             pass

#     # ── State ───────────────────────────────────────────────
#     state = {
#         "stats":        {},
#         "blood_stats":  {},
#         "city_stats":   {},
#         "recent":       [],
#         "monthly":      {},
#         "top_donors":   [],
#     }

#     # ── Content column ───────────────────────────────────────
#     content_col = ft.Column(
#         spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
#     )

#     # ================================================================
#     #  UI HELPERS
#     # ================================================================
#     def _stat_card(icon, title, value, color, subtitle="") -> ft.Container:
#         return ft.Container(
#             expand=True, height=90,
#             border_radius=16, bgcolor=color,
#             shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0,3)),
#             padding=ft.padding.all(12),
#             content=ft.Column([
#                 ft.Row([
#                     ft.Icon(icon, color="white", size=20),
#                     ft.Text(str(value), size=24,
#                             weight=ft.FontWeight.BOLD, color="white"),
#                 ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 ft.Text(title, size=11, color="white"),
#                 ft.Text(subtitle, size=9, color="white70") if subtitle else ft.Container(height=0),
#             ], spacing=2, tight=True),
#         )

#     def _section(title: str, icon=None) -> ft.Container:
#         return ft.Container(
#             padding=ft.padding.only(left=14, right=14, top=16, bottom=6),
#             content=ft.Row([
#                 ft.Icon(icon, color=PRIMARY, size=18) if icon else ft.Container(),
#                 ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=PRIMARY_DK),
#             ], spacing=8),
#         )

#     def _divider():
#         return ft.Container(
#             height=1, bgcolor=PRIMARY_MD,
#             margin=ft.margin.symmetric(horizontal=14, vertical=4),
#         )

#     def _empty(emoji, text):
#         return ft.Container(
#             padding=ft.padding.all(24),
#             alignment=ft.Alignment(0, 0),
#             content=ft.Column([
#                 ft.Text(emoji, size=36),
#                 ft.Text(text, size=12, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
#             ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
#         )

#     # ================================================================
#     #  BLOOD GROUP BAR CHART
#     # ================================================================
#     def _blood_group_chart(blood_stats: dict) -> ft.Container:
#         if not blood_stats:
#             return _empty("🩸", "No data")

#         max_val = max(blood_stats.values()) or 1
#         bars = []

#         for bg, count in sorted(blood_stats.items(), key=lambda x: -x[1]):
#             pct    = count / max_val
#             color  = BLOOD_COLORS.get(bg, PRIMARY)
#             width  = max(30, int(220 * pct))

#             bars.append(
#                 ft.Container(
#                     padding=ft.padding.symmetric(horizontal=14, vertical=3),
#                     content=ft.Row([
#                         ft.Container(
#                             width=36,
#                             content=ft.Text(bg, size=11,
#                                             weight=ft.FontWeight.BOLD, color=color),
#                         ),
#                         ft.Container(
#                             width=width, height=22, border_radius=6,
#                             bgcolor=color,
#                             alignment=ft.Alignment(1, 0),
#                             padding=ft.padding.only(right=6),
#                             content=ft.Text(str(count), size=10,
#                                             color="white", weight=ft.FontWeight.BOLD),
#                         ),
#                     ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 )
#             )

#         return ft.Container(
#             bgcolor=SURFACE, border_radius=16,
#             margin=ft.margin.symmetric(horizontal=14, vertical=4),
#             padding=ft.padding.all(14),
#             shadow=ft.BoxShadow(blur_radius=6, color="#10000000", offset=ft.Offset(0,2)),
#             content=ft.Column(bars, spacing=2, tight=True),
#         )

#     # ================================================================
#     #  CITY/AREA STATS
#     # ================================================================
#     def _city_stats_card(city_stats: dict) -> ft.Container:
#         if not city_stats:
#             return _empty("📍", "No area data")

#         rows = []
#         for i, (city, data) in enumerate(
#             sorted(city_stats.items(), key=lambda x: -x[1].get("requests", 0))[:10]
#         ):
#             requests  = data.get("requests", 0)
#             donations = data.get("donations", 0)
#             bg = PRIMARY_LT if i % 2 == 0 else SURFACE

#             rows.append(
#                 ft.Container(
#                     bgcolor=bg, border_radius=8,
#                     padding=ft.padding.symmetric(horizontal=12, vertical=8),
#                     content=ft.Row([
#                         ft.Text(f"{i+1}.", size=11, color=TEXT_SUB, width=20),
#                         ft.Text(city, size=13, weight=ft.FontWeight.W_600,
#                                 color=TEXT, expand=True),
#                         ft.Container(
#                             padding=ft.padding.symmetric(horizontal=8, vertical=3),
#                             border_radius=8, bgcolor=PRIMARY_LT,
#                             content=ft.Text(f"🩸 {requests}", size=10,
#                                             color=PRIMARY, weight=ft.FontWeight.BOLD),
#                         ),
#                         ft.Container(width=6),
#                         ft.Container(
#                             padding=ft.padding.symmetric(horizontal=8, vertical=3),
#                             border_radius=8, bgcolor=GREEN_LT,
#                             content=ft.Text(f"💉 {donations}", size=10,
#                                             color=GREEN, weight=ft.FontWeight.BOLD),
#                         ),
#                     ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 )
#             )

#         return ft.Container(
#             bgcolor=SURFACE, border_radius=16,
#             margin=ft.margin.symmetric(horizontal=14, vertical=4),
#             padding=ft.padding.all(12),
#             shadow=ft.BoxShadow(blur_radius=6, color="#10000000", offset=ft.Offset(0,2)),
#             content=ft.Column([
#                 ft.Container(
#                     padding=ft.padding.symmetric(horizontal=12, vertical=4),
#                     content=ft.Row([
#                         ft.Container(width=20),
#                         ft.Text("Area", size=11, color=TEXT_SUB, expand=True),
#                         ft.Text("Requests", size=10, color=PRIMARY),
#                         ft.Container(width=6),
#                         ft.Text("Donations", size=10, color=GREEN),
#                     ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 ),
#                 *rows,
#             ], spacing=2, tight=True),
#         )

#     # ================================================================
#     #  TOP DONORS
#     # ================================================================
#     def _top_donors_list(donors: list) -> ft.Column:
#         if not donors:
#             return ft.Column([_empty("🏆", "No donors yet")])

#         cards = []
#         medals = ["🥇", "🥈", "🥉"]

#         for i, d in enumerate(donors[:10]):
#             medal  = medals[i] if i < 3 else f"{i+1}."
#             blood  = d.get("blood_group", "?")
#             bc     = BLOOD_COLORS.get(blood, PRIMARY)
#             name   = d.get("full_name", "---")
#             city   = d.get("city", "")
#             count  = d.get("total_donations", 0)
#             badge  = d.get("donor_badge", "")

#             badge_map = {
#                 "first_drop": "🌱", "helper": "💪",
#                 "hero": "⭐", "legend": "👑",
#             }
#             badge_emoji = badge_map.get(badge, "")

#             cards.append(
#                 ft.Container(
#                     bgcolor=SURFACE, border_radius=14,
#                     margin=ft.margin.symmetric(horizontal=14, vertical=3),
#                     padding=ft.padding.symmetric(horizontal=14, vertical=10),
#                     shadow=ft.BoxShadow(blur_radius=4, color="#10000000", offset=ft.Offset(0,1)),
#                     content=ft.Row([
#                         ft.Text(medal, size=18, width=32),
#                         ft.Container(
#                             width=38, height=38, border_radius=19,
#                             bgcolor=f"{bc}22", alignment=ft.Alignment(0,0),
#                             content=ft.Text(blood, size=11,
#                                             weight=ft.FontWeight.BOLD, color=bc),
#                         ),
#                         ft.Container(width=8),
#                         ft.Column([
#                             ft.Row([
#                                 ft.Text(name, size=13,
#                                         weight=ft.FontWeight.W_700, color=TEXT),
#                                 ft.Text(badge_emoji, size=14),
#                             ], spacing=4),
#                             ft.Text(f"📍 {city}", size=11, color=TEXT_SUB),
#                         ], expand=True, spacing=2, tight=True),
#                         ft.Container(
#                             padding=ft.padding.symmetric(horizontal=10, vertical=4),
#                             border_radius=10, bgcolor=PRIMARY_LT,
#                             content=ft.Text(f"💉 {count}", size=12,
#                                             color=PRIMARY, weight=ft.FontWeight.BOLD),
#                         ),
#                     ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 )
#             )
#         return ft.Column(cards, spacing=0)

#     # ================================================================
#     #  RECENT ACTIVITY
#     # ================================================================
#     def _recent_activity(items: list) -> ft.Column:
#         if not items:
#             return ft.Column([_empty("📋", "No recent activity")])

#         status_map = {
#             "pending":     ("⏳", ORANGE),
#             "matching":    ("🔍", BLUE),
#             "in_progress": ("✅", GREEN),
#             "fulfilled":   ("🎉", GREEN),
#             "cancelled":   ("❌", TEXT_SUB),
#         }

#         rows = []
#         for r in items[:15]:
#             status = r.get("status") or "pending"
#             em, tc = status_map.get(status, ("📌", TEXT_SUB))
#             blood  = r.get("required_blood_group") or r.get("blood_group", "?")
#             city   = r.get("city", "")
#             date   = str(r.get("created_at", ""))[:10]
#             patient = r.get("patient_name", "---")

#             rows.append(
#                 ft.Container(
#                     bgcolor=SURFACE, border_radius=10,
#                     margin=ft.margin.symmetric(horizontal=14, vertical=2),
#                     padding=ft.padding.symmetric(horizontal=12, vertical=8),
#                     content=ft.Row([
#                         ft.Text(em, size=16, width=24),
#                         ft.Container(
#                             width=34, height=34, border_radius=17,
#                             bgcolor=PRIMARY_LT, alignment=ft.Alignment(0,0),
#                             content=ft.Text(blood, size=9,
#                                             weight=ft.FontWeight.BOLD, color=PRIMARY),
#                         ),
#                         ft.Container(width=8),
#                         ft.Column([
#                             ft.Text(patient, size=12,
#                                     weight=ft.FontWeight.W_600, color=TEXT),
#                             ft.Text(f"📍 {city} — {date}",
#                                     size=10, color=TEXT_SUB),
#                         ], expand=True, spacing=1, tight=True),
#                         ft.Container(
#                             padding=ft.padding.symmetric(horizontal=6, vertical=2),
#                             border_radius=6, bgcolor=f"{tc}22",
#                             content=ft.Text(status.upper(), size=8,
#                                             color=tc, weight=ft.FontWeight.BOLD),
#                         ),
#                     ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 )
#             )
#         return ft.Column(rows, spacing=0)

#     # ================================================================
#     #  MONTHLY SUMMARY CARD
#     # ================================================================
#     def _monthly_card(monthly: dict) -> ft.Container:
#         this_month = datetime.now(timezone.utc).strftime("%Y-%m")
#         data = monthly.get(this_month, {})

#         return ft.Container(
#             margin=ft.margin.symmetric(horizontal=14, vertical=4),
#             padding=ft.padding.all(16),
#             border_radius=16,
#             bgcolor=PRIMARY,
#             shadow=ft.BoxShadow(blur_radius=10, color="#33C62828", offset=ft.Offset(0,4)),
#             content=ft.Column([
#                 ft.Row([
#                     ft.Icon(ft.Icons.CALENDAR_MONTH, color="white", size=20),
#                     ft.Text("This Month | اس ماہ", size=14,
#                             weight=ft.FontWeight.BOLD, color="white"),
#                     ft.Text(datetime.now().strftime("%B %Y"),
#                             size=12, color=PRIMARY_MD),
#                 ], spacing=8),
#                 ft.Container(height=10),
#                 ft.Row([
#                     _mini_stat("🩸", "Requests", data.get("requests", 0)),
#                     _mini_stat("💉", "Donations", data.get("donations", 0)),
#                     _mini_stat("👥", "New Members", data.get("members", 0)),
#                     _mini_stat("✅", "Fulfilled", data.get("fulfilled", 0)),
#                 ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
#             ], spacing=0),
#         )

#     def _mini_stat(emoji, label, val) -> ft.Column:
#         return ft.Column([
#             ft.Text(emoji, size=20, text_align=ft.TextAlign.CENTER),
#             ft.Text(str(val), size=20, weight=ft.FontWeight.BOLD,
#                     color="white", text_align=ft.TextAlign.CENTER),
#             ft.Text(label, size=9, color=PRIMARY_MD,
#                     text_align=ft.TextAlign.CENTER),
#         ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2, tight=True)

#     # ================================================================
#     #  BUILD UI
#     # ================================================================
#     def build_ui():
#         s  = state["stats"]
#         bs = state["blood_stats"]
#         cs = state["city_stats"]

#         controls = [
#             # ── Overall Stats ──
#             _section("Overall Stats | مجموعی اعداد", ft.Icons.DASHBOARD_ROUNDED),
#             ft.Container(
#                 padding=ft.padding.symmetric(horizontal=14, vertical=4),
#                 content=ft.Column([
#                     ft.Row([
#                         _stat_card(ft.Icons.PEOPLE_ROUNDED, "Total Members\nکل ممبران",
#                                    s.get("members",0), PRIMARY),
#                         _stat_card(ft.Icons.BLOODTYPE_ROUNDED, "Total Requests\nکل درخواستیں",
#                                    s.get("requests",0), "#E53935"),
#                     ], spacing=10),
#                     ft.Container(height=8),
#                     ft.Row([
#                         _stat_card(ft.Icons.FAVORITE_ROUNDED, "Total Donations\nکل عطیات",
#                                    s.get("donations",0), GREEN),
#                         _stat_card(ft.Icons.CHECK_CIRCLE_ROUNDED, "Fulfilled\nمکمل",
#                                    s.get("fulfilled",0), BLUE),
#                     ], spacing=10),
#                     ft.Container(height=8),
#                     ft.Row([
#                         _stat_card(ft.Icons.PENDING_ACTIONS, "Pending\nزیر التواء",
#                                    s.get("pending",0), ORANGE),
#                         _stat_card(ft.Icons.STAR_ROUNDED, "Avg Rating\nاوسط ریٹنگ",
#                                    f"{s.get('avg_rating',0):.1f}⭐", PURPLE),
#                     ], spacing=10),
#                 ], spacing=0),
#             ),

#             # ── Monthly Summary ──
#             _section("This Month | اس ماہ", ft.Icons.CALENDAR_MONTH),
#             _monthly_card(state["monthly"]),

#             # ── Blood Group Stats ──
#             _section("Blood Group Demand | خون گروپ", ft.Icons.BLOODTYPE_ROUNDED),
#             _blood_group_chart(bs),

#             # ── Area Stats ──
#             _section("Area-wise Stats | علاقہ وار", ft.Icons.LOCATION_ON_ROUNDED),
#             _city_stats_card(cs),

#             # ── Top Donors ──
#             _section("Top Donors | بہترین ڈونرز", ft.Icons.MILITARY_TECH_ROUNDED),
#             _top_donors_list(state["top_donors"]),

#             # ── Recent Activity ──
#             _section("Recent Requests | حالیہ درخواستیں", ft.Icons.HISTORY_ROUNDED),
#             _recent_activity(state["recent"]),

#             ft.Container(height=40),
#         ]

#         content_col.controls = controls
#         try:
#             page.update()
#         except Exception:
#             pass

#     # ================================================================
#     #  DATA LOADER
#     # ================================================================
#     def load_data(_=None):
#         content_col.controls = [
#             ft.Container(
#                 expand=True, padding=ft.padding.all(40),
#                 alignment=ft.Alignment(0, 0),
#                 content=ft.Column([
#                     ft.ProgressRing(color=PRIMARY, width=48, height=48, stroke_width=4),
#                     ft.Container(height=12),
#                     ft.Text("Loading reports...", size=13, color=TEXT_SUB),
#                 ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, tight=True),
#             )
#         ]
#         try:
#             page.update()
#         except Exception:
#             pass

#         async def _work():
#             try:
#                 await _restore()
#                 now = datetime.now(timezone.utc)
#                 this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

#                 # ── Overall stats ──
#                 for key, table, filt in [
#                     ("members",   "members",        None),
#                     ("requests",  "blood_requests",  None),
#                     ("donations", "donations",       None),
#                     ("fulfilled", "blood_requests",  ("status", "fulfilled")),
#                     ("pending",   "blood_requests",  ("status", "pending")),
#                 ]:
#                     try:
#                         def _count(t=table, f=filt):
#                             q = _sb.table(t).select("id", count="exact")
#                             if f:
#                                 q = q.eq(f[0], f[1])
#                             return q.execute()
#                         res = await asyncio.to_thread(_count)
#                         state["stats"][key] = res.count or 0
#                     except Exception:
#                         pass

#                 # Avg rating
#                 try:
#                     def _rating():
#                         return _sb.table("feedback").select("requester_rating").execute()
#                     rr = await asyncio.to_thread(_rating)
#                     ratings = [r["requester_rating"] for r in (rr.data or []) if r.get("requester_rating")]
#                     state["stats"]["avg_rating"] = sum(ratings)/len(ratings) if ratings else 0
#                 except Exception:
#                     state["stats"]["avg_rating"] = 0

#                 # ── Blood group stats (from requests) ──
#                 try:
#                     def _blood():
#                         return _sb.table("blood_requests").select("required_blood_group").execute()
#                     br = await asyncio.to_thread(_blood)
#                     blood_count = {}
#                     for r in (br.data or []):
#                         bg = r.get("required_blood_group","")
#                         if bg:
#                             blood_count[bg] = blood_count.get(bg, 0) + 1
#                     state["blood_stats"] = blood_count
#                 except Exception:
#                     pass

#                 # ── City stats ──
#                 try:
#                     def _reqs():
#                         return _sb.table("blood_requests").select("city, status").execute()
#                     def _dons():
#                         return _sb.table("donations").select("city").execute()

#                     req_res = await asyncio.to_thread(_reqs)
#                     don_res = await asyncio.to_thread(_dons)

#                     city_data = {}
#                     for r in (req_res.data or []):
#                         c = r.get("city","").strip()
#                         if c:
#                             if c not in city_data:
#                                 city_data[c] = {"requests": 0, "donations": 0}
#                             city_data[c]["requests"] += 1

#                     for d in (don_res.data or []):
#                         c = d.get("city","").strip()
#                         if c:
#                             if c not in city_data:
#                                 city_data[c] = {"requests": 0, "donations": 0}
#                             city_data[c]["donations"] += 1

#                     state["city_stats"] = city_data
#                 except Exception:
#                     pass

#                 # ── Monthly stats ──
#                 try:
#                     def _month_reqs():
#                         return (
#                             _sb.table("blood_requests")
#                             .select("status, created_at")
#                             .gte("created_at", this_month_start)
#                             .execute()
#                         )
#                     def _month_dons():
#                         return (
#                             _sb.table("donations")
#                             .select("id")
#                             .gte("donated_at", this_month_start)
#                             .execute()
#                         )
#                     def _month_members():
#                         return (
#                             _sb.table("members")
#                             .select("id", count="exact")
#                             .gte("created_at", this_month_start)
#                             .execute()
#                         )

#                     mr = await asyncio.to_thread(_month_reqs)
#                     md = await asyncio.to_thread(_month_dons)
#                     mm = await asyncio.to_thread(_month_members)

#                     this_month = now.strftime("%Y-%m")
#                     fulfilled  = sum(1 for r in (mr.data or []) if r.get("status") == "fulfilled")

#                     state["monthly"][this_month] = {
#                         "requests":  len(mr.data or []),
#                         "donations": len(md.data or []),
#                         "members":   mm.count or 0,
#                         "fulfilled": fulfilled,
#                     }
#                 except Exception:
#                     pass

#                 # ── Top donors ──
#                 try:
#                     def _top():
#                         return (
#                             _sb.table("members")
#                             .select("full_name, blood_group, city, total_donations, donor_badge")
#                             .gt("total_donations", 0)
#                             .order("total_donations", desc=True)
#                             .limit(10)
#                             .execute()
#                         )
#                     tr = await asyncio.to_thread(_top)
#                     state["top_donors"] = tr.data or []
#                 except Exception:
#                     pass

#                 # ── Recent requests ──
#                 try:
#                     def _recent():
#                         return (
#                             _sb.table("blood_requests")
#                             .select("*")
#                             .order("created_at", desc=True)
#                             .limit(15)
#                             .execute()
#                         )
#                     rr = await asyncio.to_thread(_recent)
#                     state["recent"] = rr.data or []
#                 except Exception:
#                     pass

#                 build_ui()

#             except Exception as ex:
#                 print(f"[REPORTS] error: {ex}")
#                 content_col.controls = [
#                     ft.Container(
#                         padding=ft.padding.all(40),
#                         content=ft.Column([
#                             ft.Icon(ft.Icons.ERROR_OUTLINE, color=PRIMARY, size=48),
#                             ft.Text(f"Error: {str(ex)[:80]}", color=PRIMARY,
#                                     text_align=ft.TextAlign.CENTER, size=12),
#                             ft.TextButton("Retry | دوبارہ", on_click=load_data),
#                         ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
#                     )
#                 ]
#                 try:
#                     page.update()
#                 except Exception:
#                     pass

#         page.run_task(_work)

#     # Initial load
#     load_data()

#     # ================================================================
#     #  RETURN VIEW
#     # ================================================================
#     return ft.View(
#         route="/admin/reports",
#         bgcolor=BG,
#         appbar=ft.AppBar(
#             leading=ft.IconButton(
#                 ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
#                 icon_color="white",
#                 on_click=lambda _: page.go("/admin"),
#             ),
#             title=ft.Column([
#                 ft.Text("Reports & Analytics", size=15,
#                         weight=ft.FontWeight.BOLD, color="white"),
#                 ft.Text("رپورٹس اور تجزیہ", size=11, color=PRIMARY_MD),
#             ], spacing=0),
#             bgcolor=PRIMARY,
#             actions=[
#                 ft.IconButton(
#                     ft.Icons.REFRESH_ROUNDED,
#                     icon_color="white",
#                     on_click=load_data,
#                     tooltip="Refresh",
#                 ),
#             ],
#         ),
#         controls=[
#             ft.Column(
#                 expand=True, spacing=0,
#                 controls=[
#                     ft.Container(
#                         expand=True,
#                         content=content_col,
#                     ),
#                 ],
#             ),
#         ],
#     )

















# # ================================================================
# #  pages/admin/reports.py  —  Reports & Analytics
# #  Real Supabase data | Area-wise | Blood group stats
# #  Flet 0.84 compatible | Session-safe
# # ================================================================
# from core.theme import Theme 
# import asyncio
# import flet as ft
# from supabase import create_client
# from services.database.db import SUPABASE_URL_STR, SUPABASE_KEY_STR
# from datetime import datetime, timezone, timedelta

# PRIMARY    = "#C62828"
# PRIMARY_LT = "#FFEBEE"
# PRIMARY_MD = "#FFCDD2"
# PRIMARY_DK = "#B71C1C"
# GREEN      = "#2E7D32"
# GREEN_LT   = "#E8F5E9"
# BLUE       = "#1565C0"
# BLUE_LT    = "#E3F2FD"
# ORANGE     = "#E65100"
# ORANGE_LT  = "#FFF3E0"
# PURPLE     = "#6A1B9A"
# BG         = "#FFF5F5"
# TEXT       = "#212121"
# TEXT_SUB   = "#757575"
# SURFACE    = "#FFFFFF"

# BLOOD_COLORS = {
#     "A+":  "#E53935", "A-":  "#C62828",
#     "B+":  "#1565C0", "B-":  "#0D47A1",
#     "AB+": "#6A1B9A", "AB-": "#4A148C",
#     "O+":  "#2E7D32", "O-":  "#1B5E20",
# }


# def view(page: ft.Page) -> ft.View:

#     # ── Session helpers ─────────────────────────────────────
#     def sess_get(key, default=""):
#         try:
#             if hasattr(page.session, "_Session__store"):
#                 return page.session._Session__store.get(key) or default
#             return page.session.get(key) or default
#         except Exception:
#             return default

#     _sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR)

#     async def _restore():
#         try:
#             at = sess_get("access_token")
#             rt = sess_get("refresh_token", "")
#             if at:
#                 await asyncio.to_thread(_sb.auth.set_session, at, rt)
#         except Exception:
#             pass

#     def snack(msg, color=PRIMARY):
#         async def _show():
#             try:
#                 sb = ft.SnackBar(
#                     content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD),
#                     bgcolor=color, duration=3000,
#                 )
#                 page.overlay.append(sb)
#                 sb.open = True
#                 page.update()
#             except Exception:
#                 pass
#         try:
#             page.run_task(_show)
#         except Exception:
#             pass

#     # ── State ───────────────────────────────────────────────
#     state = {
#         "stats":        {},
#         "blood_stats":  {},
#         "city_stats":   {},
#         "recent":       [],
#         "monthly":      {},
#         "top_donors":   [],
#     }

#     # ── Content column ───────────────────────────────────────
#     content_col = ft.Column(
#         spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
#     )

#     # ================================================================
#     #  UI HELPERS
#     # ================================================================
#     def _stat_card(icon, title, value, color, subtitle="") -> ft.Container:
#         return ft.Container(
#             expand=True, height=90,
#             border_radius=16, bgcolor=color,
#             shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0,3)),
#             padding=ft.padding.all(12),
#             content=ft.Column([
#                 ft.Row([
#                     ft.Icon(icon, color="white", size=20),
#                     ft.Text(str(value), size=24,
#                             weight=ft.FontWeight.BOLD, color="white"),
#                 ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 ft.Text(title, size=11, color="white"),
#                 ft.Text(subtitle, size=9, color="white70") if subtitle else ft.Container(height=0),
#             ], spacing=2, tight=True),
#         )

#     def _section(title: str, icon=None) -> ft.Container:
#         return ft.Container(
#             padding=ft.padding.only(left=14, right=14, top=16, bottom=6),
#             content=ft.Row([
#                 ft.Icon(icon, color=PRIMARY, size=18) if icon else ft.Container(),
#                 ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=PRIMARY_DK),
#             ], spacing=8),
#         )

#     def _divider():
#         return ft.Container(
#             height=1, bgcolor=PRIMARY_MD,
#             margin=ft.margin.symmetric(horizontal=14, vertical=4),
#         )

#     def _empty(emoji, text):
#         return ft.Container(
#             padding=ft.padding.all(24),
#             alignment=ft.Alignment(0, 0),
#             content=ft.Column([
#                 ft.Text(emoji, size=36),
#                 ft.Text(text, size=12, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
#             ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
#         )

#     # ================================================================
#     #  BLOOD GROUP BAR CHART
#     # ================================================================
#     def _blood_group_chart(blood_stats: dict) -> ft.Container:
#         if not blood_stats:
#             return _empty("🩸", "No data")

#         max_val = max(blood_stats.values()) or 1
#         bars = []

#         for bg, count in sorted(blood_stats.items(), key=lambda x: -x[1]):
#             pct    = count / max_val
#             color  = BLOOD_COLORS.get(bg, PRIMARY)
#             width  = max(30, int(220 * pct))

#             bars.append(
#                 ft.Container(
#                     padding=ft.padding.symmetric(horizontal=14, vertical=3),
#                     content=ft.Row([
#                         ft.Container(
#                             width=36,
#                             content=ft.Text(bg, size=11,
#                                             weight=ft.FontWeight.BOLD, color=color),
#                         ),
#                         ft.Container(
#                             width=width, height=22, border_radius=6,
#                             bgcolor=color,
#                             alignment=ft.Alignment(1, 0),
#                             padding=ft.padding.only(right=6),
#                             content=ft.Text(str(count), size=10,
#                                             color="white", weight=ft.FontWeight.BOLD),
#                         ),
#                     ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 )
#             )

#         return ft.Container(
#             bgcolor=SURFACE, border_radius=16,
#             margin=ft.margin.symmetric(horizontal=14, vertical=4),
#             padding=ft.padding.all(14),
#             shadow=ft.BoxShadow(blur_radius=6, color="#10000000", offset=ft.Offset(0,2)),
#             content=ft.Column(bars, spacing=2, tight=True),
#         )

#     # ================================================================
#     #  CITY/AREA STATS
#     # ================================================================
#     def _city_stats_card(city_stats: dict) -> ft.Container:
#         if not city_stats:
#             return _empty("📍", "No area data")

#         rows = []
#         for i, (city, data) in enumerate(
#             sorted(city_stats.items(), key=lambda x: -x[1].get("requests", 0))[:10]
#         ):
#             requests  = data.get("requests", 0)
#             donations = data.get("donations", 0)
#             bg = PRIMARY_LT if i % 2 == 0 else SURFACE

#             rows.append(
#                 ft.Container(
#                     bgcolor=bg, border_radius=8,
#                     padding=ft.padding.symmetric(horizontal=12, vertical=8),
#                     content=ft.Row([
#                         ft.Text(f"{i+1}.", size=11, color=TEXT_SUB, width=20),
#                         ft.Text(city, size=13, weight=ft.FontWeight.W_600,
#                                 color=TEXT, expand=True),
#                         ft.Container(
#                             padding=ft.padding.symmetric(horizontal=8, vertical=3),
#                             border_radius=8, bgcolor=PRIMARY_LT,
#                             content=ft.Text(f"🩸 {requests}", size=10,
#                                             color=PRIMARY, weight=ft.FontWeight.BOLD),
#                         ),
#                         ft.Container(width=6),
#                         ft.Container(
#                             padding=ft.padding.symmetric(horizontal=8, vertical=3),
#                             border_radius=8, bgcolor=GREEN_LT,
#                             content=ft.Text(f"💉 {donations}", size=10,
#                                             color=GREEN, weight=ft.FontWeight.BOLD),
#                         ),
#                     ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 )
#             )

#         return ft.Container(
#             bgcolor=SURFACE, border_radius=16,
#             margin=ft.margin.symmetric(horizontal=14, vertical=4),
#             padding=ft.padding.all(12),
#             shadow=ft.BoxShadow(blur_radius=6, color="#10000000", offset=ft.Offset(0,2)),
#             content=ft.Column([
#                 ft.Container(
#                     padding=ft.padding.symmetric(horizontal=12, vertical=4),
#                     content=ft.Row([
#                         ft.Container(width=20),
#                         ft.Text("Area", size=11, color=TEXT_SUB, expand=True),
#                         ft.Text("Requests", size=10, color=PRIMARY),
#                         ft.Container(width=6),
#                         ft.Text("Donations", size=10, color=GREEN),
#                     ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 ),
#                 *rows,
#             ], spacing=2, tight=True),
#         )

#     # ================================================================
#     #  TOP DONORS
#     # ================================================================
#     def _top_donors_list(donors: list) -> ft.Column:
#         if not donors:
#             return ft.Column([_empty("🏆", "No donors yet")])

#         cards = []
#         medals = ["🥇", "🥈", "🥉"]

#         for i, d in enumerate(donors[:10]):
#             medal  = medals[i] if i < 3 else f"{i+1}."
#             blood  = d.get("blood_group", "?")
#             bc     = BLOOD_COLORS.get(blood, PRIMARY)
#             name   = d.get("full_name", "---")
#             city   = d.get("city", "")
#             count  = d.get("total_donations", 0)
#             badge  = d.get("donor_badge", "")

#             badge_map = {
#                 "first_drop": "🌱", "helper": "💪",
#                 "hero": "⭐", "legend": "👑",
#             }
#             badge_emoji = badge_map.get(badge, "")

#             cards.append(
#                 ft.Container(
#                     bgcolor=SURFACE, border_radius=14,
#                     margin=ft.margin.symmetric(horizontal=14, vertical=3),
#                     padding=ft.padding.symmetric(horizontal=14, vertical=10),
#                     shadow=ft.BoxShadow(blur_radius=4, color="#10000000", offset=ft.Offset(0,1)),
#                     content=ft.Row([
#                         ft.Text(medal, size=18, width=32),
#                         ft.Container(
#                             width=38, height=38, border_radius=19,
#                             bgcolor=f"{bc}22", alignment=ft.Alignment(0,0),
#                             content=ft.Text(blood, size=11,
#                                             weight=ft.FontWeight.BOLD, color=bc),
#                         ),
#                         ft.Container(width=8),
#                         ft.Column([
#                             ft.Row([
#                                 ft.Text(name, size=13,
#                                         weight=ft.FontWeight.W_700, color=TEXT),
#                                 ft.Text(badge_emoji, size=14),
#                             ], spacing=4),
#                             ft.Text(f"📍 {city}", size=11, color=TEXT_SUB),
#                         ], expand=True, spacing=2, tight=True),
#                         ft.Container(
#                             padding=ft.padding.symmetric(horizontal=10, vertical=4),
#                             border_radius=10, bgcolor=PRIMARY_LT,
#                             content=ft.Text(f"💉 {count}", size=12,
#                                             color=PRIMARY, weight=ft.FontWeight.BOLD),
#                         ),
#                     ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 )
#             )
#         return ft.Column(cards, spacing=0)

#     # ================================================================
#     #  RECENT ACTIVITY
#     # ================================================================
#     def _recent_activity(items: list) -> ft.Column:
#         if not items:
#             return ft.Column([_empty("📋", "No recent activity")])

#         status_map = {
#             "pending":     ("⏳", ORANGE),
#             "matching":    ("🔍", BLUE),
#             "in_progress": ("✅", GREEN),
#             "fulfilled":   ("🎉", GREEN),
#             "cancelled":   ("❌", TEXT_SUB),
#         }

#         rows = []
#         for r in items[:15]:
#             status = r.get("status", "pending")
#             em, tc = status_map.get(status, ("📌", TEXT_SUB))
#             blood  = r.get("required_blood_group") or r.get("blood_group", "?")
#             city   = r.get("city", "")
#             date   = str(r.get("created_at", ""))[:10]
#             patient = r.get("patient_name", "---")

#             rows.append(
#                 ft.Container(
#                     bgcolor=SURFACE, border_radius=10,
#                     margin=ft.margin.symmetric(horizontal=14, vertical=2),
#                     padding=ft.padding.symmetric(horizontal=12, vertical=8),
#                     content=ft.Row([
#                         ft.Text(em, size=16, width=24),
#                         ft.Container(
#                             width=34, height=34, border_radius=17,
#                             bgcolor=PRIMARY_LT, alignment=ft.Alignment(0,0),
#                             content=ft.Text(blood, size=9,
#                                             weight=ft.FontWeight.BOLD, color=PRIMARY),
#                         ),
#                         ft.Container(width=8),
#                         ft.Column([
#                             ft.Text(patient, size=12,
#                                     weight=ft.FontWeight.W_600, color=TEXT),
#                             ft.Text(f"📍 {city} — {date}",
#                                     size=10, color=TEXT_SUB),
#                         ], expand=True, spacing=1, tight=True),
#                         ft.Container(
#                             padding=ft.padding.symmetric(horizontal=6, vertical=2),
#                             border_radius=6, bgcolor=f"{tc}22",
#                             content=ft.Text(status.upper(), size=8,
#                                             color=tc, weight=ft.FontWeight.BOLD),
#                         ),
#                     ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
#                 )
#             )
#         return ft.Column(rows, spacing=0)

#     # ================================================================
#     #  MONTHLY SUMMARY CARD
#     # ================================================================
#     def _monthly_card(monthly: dict) -> ft.Container:
#         this_month = datetime.now(timezone.utc).strftime("%Y-%m")
#         data = monthly.get(this_month, {})

#         return ft.Container(
#             margin=ft.margin.symmetric(horizontal=14, vertical=4),
#             padding=ft.padding.all(16),
#             border_radius=16,
#             bgcolor=PRIMARY,
#             shadow=ft.BoxShadow(blur_radius=10, color="#33C62828", offset=ft.Offset(0,4)),
#             content=ft.Column([
#                 ft.Row([
#                     ft.Icon(ft.Icons.CALENDAR_MONTH, color="white", size=20),
#                     ft.Text("This Month | اس ماہ", size=14,
#                             weight=ft.FontWeight.BOLD, color="white"),
#                     ft.Text(datetime.now().strftime("%B %Y"),
#                             size=12, color=PRIMARY_MD),
#                 ], spacing=8),
#                 ft.Container(height=10),
#                 ft.Row([
#                     _mini_stat("🩸", "Requests", data.get("requests", 0)),
#                     _mini_stat("💉", "Donations", data.get("donations", 0)),
#                     _mini_stat("👥", "New Members", data.get("members", 0)),
#                     _mini_stat("✅", "Fulfilled", data.get("fulfilled", 0)),
#                 ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
#             ], spacing=0),
#         )

#     def _mini_stat(emoji, label, val) -> ft.Column:
#         return ft.Column([
#             ft.Text(emoji, size=20, text_align=ft.TextAlign.CENTER),
#             ft.Text(str(val), size=20, weight=ft.FontWeight.BOLD,
#                     color="white", text_align=ft.TextAlign.CENTER),
#             ft.Text(label, size=9, color=PRIMARY_MD,
#                     text_align=ft.TextAlign.CENTER),
#         ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2, tight=True)

#     # ================================================================
#     #  BUILD UI
#     # ================================================================
#     def build_ui():
#         s  = state["stats"]
#         bs = state["blood_stats"]
#         cs = state["city_stats"]

#         controls = [
#             # ── Overall Stats ──
#             _section("Overall Stats | مجموعی اعداد", ft.Icons.DASHBOARD_ROUNDED),
#             ft.Container(
#                 padding=ft.padding.symmetric(horizontal=14, vertical=4),
#                 content=ft.Column([
#                     ft.Row([
#                         _stat_card(ft.Icons.PEOPLE_ROUNDED, "Total Members\nکل ممبران",
#                                    s.get("members",0), PRIMARY),
#                         _stat_card(ft.Icons.BLOODTYPE_ROUNDED, "Total Requests\nکل درخواستیں",
#                                    s.get("requests",0), "#E53935"),
#                     ], spacing=10),
#                     ft.Container(height=8),
#                     ft.Row([
#                         _stat_card(ft.Icons.FAVORITE_ROUNDED, "Total Donations\nکل عطیات",
#                                    s.get("donations",0), GREEN),
#                         _stat_card(ft.Icons.CHECK_CIRCLE_ROUNDED, "Fulfilled\nمکمل",
#                                    s.get("fulfilled",0), BLUE),
#                     ], spacing=10),
#                     ft.Container(height=8),
#                     ft.Row([
#                         _stat_card(ft.Icons.PENDING_ACTIONS, "Pending\nزیر التواء",
#                                    s.get("pending",0), ORANGE),
#                         _stat_card(ft.Icons.STAR_ROUNDED, "Avg Rating\nاوسط ریٹنگ",
#                                    f"{s.get('avg_rating',0):.1f}⭐", PURPLE),
#                     ], spacing=10),
#                 ], spacing=0),
#             ),

#             # ── Monthly Summary ──
#             _section("This Month | اس ماہ", ft.Icons.CALENDAR_MONTH),
#             _monthly_card(state["monthly"]),

#             # ── Blood Group Stats ──
#             _section("Blood Group Demand | خون گروپ", ft.Icons.BLOODTYPE_ROUNDED),
#             _blood_group_chart(bs),

#             # ── Area Stats ──
#             _section("Area-wise Stats | علاقہ وار", ft.Icons.LOCATION_ON_ROUNDED),
#             _city_stats_card(cs),

#             # ── Top Donors ──
#             _section("Top Donors | بہترین ڈونرز", ft.Icons.MILITARY_TECH_ROUNDED),
#             _top_donors_list(state["top_donors"]),

#             # ── Recent Activity ──
#             _section("Recent Requests | حالیہ درخواستیں", ft.Icons.HISTORY_ROUNDED),
#             _recent_activity(state["recent"]),

#             ft.Container(height=40),
#         ]

#         content_col.controls = controls
#         try:
#             page.update()
#         except Exception:
#             pass

#     # ================================================================
#     #  DATA LOADER
#     # ================================================================
#     def load_data(_=None):
#         content_col.controls = [
#             ft.Container(
#                 expand=True, padding=ft.padding.all(40),
#                 alignment=ft.Alignment(0, 0),
#                 content=ft.Column([
#                     ft.ProgressRing(color=PRIMARY, width=48, height=48, stroke_width=4),
#                     ft.Container(height=12),
#                     ft.Text("Loading reports...", size=13, color=TEXT_SUB),
#                 ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, tight=True),
#             )
#         ]
#         try:
#             page.update()
#         except Exception:
#             pass

#         async def _work():
#             try:
#                 await _restore()
#                 now = datetime.now(timezone.utc)
#                 this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

#                 # ── Overall stats ──
#                 for key, table, filt in [
#                     ("members",   "members",        None),
#                     ("requests",  "blood_requests",  None),
#                     ("donations", "donations",       None),
#                     ("fulfilled", "blood_requests",  ("status", "fulfilled")),
#                     ("pending",   "blood_requests",  ("status", "pending")),
#                 ]:
#                     try:
#                         def _count(t=table, f=filt):
#                             q = _sb.table(t).select("id", count="exact")
#                             if f:
#                                 q = q.eq(f[0], f[1])
#                             return q.execute()
#                         res = await asyncio.to_thread(_count)
#                         state["stats"][key] = res.count or 0
#                     except Exception:
#                         pass

#                 # Avg rating
#                 try:
#                     def _rating():
#                         return _sb.table("feedback").select("requester_rating").execute()
#                     rr = await asyncio.to_thread(_rating)
#                     ratings = [r["requester_rating"] for r in (rr.data or []) if r.get("requester_rating")]
#                     state["stats"]["avg_rating"] = sum(ratings)/len(ratings) if ratings else 0
#                 except Exception:
#                     state["stats"]["avg_rating"] = 0

#                 # ── Blood group stats (from requests) ──
#                 try:
#                     def _blood():
#                         return _sb.table("blood_requests").select("required_blood_group").execute()
#                     br = await asyncio.to_thread(_blood)
#                     blood_count = {}
#                     for r in (br.data or []):
#                         bg = r.get("required_blood_group","")
#                         if bg:
#                             blood_count[bg] = blood_count.get(bg, 0) + 1
#                     state["blood_stats"] = blood_count
#                 except Exception:
#                     pass

#                 # ── City stats ──
#                 try:
#                     def _reqs():
#                         return _sb.table("blood_requests").select("city, status").execute()
#                     def _dons():
#                         return _sb.table("donations").select("city").execute()

#                     req_res = await asyncio.to_thread(_reqs)
#                     don_res = await asyncio.to_thread(_dons)

#                     city_data = {}
#                     for r in (req_res.data or []):
#                         c = r.get("city","").strip()
#                         if c:
#                             if c not in city_data:
#                                 city_data[c] = {"requests": 0, "donations": 0}
#                             city_data[c]["requests"] += 1

#                     for d in (don_res.data or []):
#                         c = d.get("city","").strip()
#                         if c:
#                             if c not in city_data:
#                                 city_data[c] = {"requests": 0, "donations": 0}
#                             city_data[c]["donations"] += 1

#                     state["city_stats"] = city_data
#                 except Exception:
#                     pass

#                 # ── Monthly stats ──
#                 try:
#                     def _month_reqs():
#                         return (
#                             _sb.table("blood_requests")
#                             .select("status, created_at")
#                             .gte("created_at", this_month_start)
#                             .execute()
#                         )
#                     def _month_dons():
#                         return (
#                             _sb.table("donations")
#                             .select("id")
#                             .gte("donated_at", this_month_start)
#                             .execute()
#                         )
#                     def _month_members():
#                         return (
#                             _sb.table("members")
#                             .select("id", count="exact")
#                             .gte("created_at", this_month_start)
#                             .execute()
#                         )

#                     mr = await asyncio.to_thread(_month_reqs)
#                     md = await asyncio.to_thread(_month_dons)
#                     mm = await asyncio.to_thread(_month_members)

#                     this_month = now.strftime("%Y-%m")
#                     fulfilled  = sum(1 for r in (mr.data or []) if r.get("status") == "fulfilled")

#                     state["monthly"][this_month] = {
#                         "requests":  len(mr.data or []),
#                         "donations": len(md.data or []),
#                         "members":   mm.count or 0,
#                         "fulfilled": fulfilled,
#                     }
#                 except Exception:
#                     pass

#                 # ── Top donors ──
#                 try:
#                     def _top():
#                         return (
#                             _sb.table("members")
#                             .select("full_name, blood_group, city, total_donations, donor_badge")
#                             .gt("total_donations", 0)
#                             .order("total_donations", desc=True)
#                             .limit(10)
#                             .execute()
#                         )
#                     tr = await asyncio.to_thread(_top)
#                     state["top_donors"] = tr.data or []
#                 except Exception:
#                     pass

#                 # ── Recent requests ──
#                 try:
#                     def _recent():
#                         return (
#                             _sb.table("blood_requests")
#                             .select("*")
#                             .order("created_at", desc=True)
#                             .limit(15)
#                             .execute()
#                         )
#                     rr = await asyncio.to_thread(_recent)
#                     state["recent"] = rr.data or []
#                 except Exception:
#                     pass

#                 build_ui()

#             except Exception as ex:
#                 print(f"[REPORTS] error: {ex}")
#                 content_col.controls = [
#                     ft.Container(
#                         padding=ft.padding.all(40),
#                         content=ft.Column([
#                             ft.Icon(ft.Icons.ERROR_OUTLINE, color=PRIMARY, size=48),
#                             ft.Text(f"Error: {str(ex)[:80]}", color=PRIMARY,
#                                     text_align=ft.TextAlign.CENTER, size=12),
#                             ft.TextButton("Retry | دوبارہ", on_click=load_data),
#                         ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
#                     )
#                 ]
#                 try:
#                     page.update()
#                 except Exception:
#                     pass

#         page.run_task(_work)

#     # Initial load
#     load_data()

#     # ================================================================
#     #  RETURN VIEW
#     # ================================================================
#     return ft.View(
#         route="/admin/reports",
#         bgcolor=BG,
#         appbar=ft.AppBar(
#             leading=ft.IconButton(
#                 ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
#                 icon_color="white",
#                 on_click=lambda _: page.go("/admin"),
#             ),
#             title=ft.Column([
#                 ft.Text("Reports & Analytics", size=15,
#                         weight=ft.FontWeight.BOLD, color="white"),
#                 ft.Text("رپورٹس اور تجزیہ", size=11, color=PRIMARY_MD),
#             ], spacing=0),
#             bgcolor=PRIMARY,
#             actions=[
#                 ft.IconButton(
#                     ft.Icons.REFRESH_ROUNDED,
#                     icon_color="white",
#                     on_click=load_data,
#                     tooltip="Refresh",
#                 ),
#             ],
#         ),
#         controls=[
#             ft.Column(
#                 expand=True, spacing=0,
#                 controls=[
#                     ft.Container(
#                         expand=True,
#                         content=content_col,
#                     ),
#                 ],
#             ),
#         ],
#     )