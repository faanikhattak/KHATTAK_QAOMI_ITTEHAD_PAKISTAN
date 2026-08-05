# ================================================================
#  pages/user/leaderboard.py  —  Leaderboard & Badges
#  Top donors, badges, hall of fame
#  Flet 0.84 compatible | Session-safe | Updated to 'profiles'
# ================================================================
from core.theme import Theme 
import asyncio
import flet as ft
from supabase import create_client
from services.database.db import SUPABASE_URL_STR, SUPABASE_KEY_STR, http1_options

PRIMARY    = "#C62828"
PRIMARY_LT = "#FFEBEE"
PRIMARY_MD = "#FFCDD2"
PRIMARY_DK = "#B71C1C"
GREEN      = "#2E7D32"
GREEN_LT   = "#E8F5E9"
BLUE       = "#1565C0"
BLUE_LT    = "#E3F2FD"
ORANGE     = "#E65100"
PURPLE     = "#6A1B9A"
PURPLE_LT  = "#F3E5F5"
GOLD       = "#F57F17"
SILVER     = "#607D8B"
BRONZE     = "#795548"
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

BADGES = {
    "first_drop": ("🌱", "First Drop",  "پہلا قطرہ",  "1 donation",   GREEN_LT,  GREEN),
    "helper":     ("💪", "Helper",      "مددگار",      "5 donations",  BLUE_LT,   BLUE),
    "hero":       ("⭐", "Hero",        "ہیرو",        "10 donations", PRIMARY_LT, PRIMARY),
    "legend":     ("👑", "Legend",      "لیجنڈ",       "20 donations", PURPLE_LT, PURPLE),
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

    # ── State ───────────────────────────────────────────────
    state = {
        "top_donors":  [],
        "my_badges":   [],
        "my_stats":    {},
        "all_badges":  [],
    }

    uid = sess_get("user_id")

    # ── Tab system ───────────────────────────────────────────
    selected_tab = [0]

    tab_leader_btn = ft.Container(
        expand=True, height=40, border_radius=10,
        bgcolor=PRIMARY, alignment=ft.Alignment(0, 0),
        content=ft.Text("🏆 Leaderboard", size=12,
                        color="white", weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_tab(0),
    )
    tab_badges_btn = ft.Container(
        expand=True, height=40, border_radius=10,
        bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
        content=ft.Text("🎖️ My Badges", size=12,
                        color=PRIMARY, weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_tab(1),
    )
    tab_all_badges_btn = ft.Container(
        expand=True, height=40, border_radius=10,
        bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
        content=ft.Text("📋 All Badges", size=12,
                        color=PRIMARY, weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_tab(2),
    )

    leader_col     = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO)
    my_badges_col  = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    all_badges_col = ft.Column(spacing=6,  scroll=ft.ScrollMode.AUTO)

    leader_view     = ft.Container(visible=True,  content=leader_col)
    my_badges_view  = ft.Container(visible=False, content=my_badges_col)
    all_badges_view = ft.Container(visible=False, content=all_badges_col)

    def _switch_tab(idx: int):
        selected_tab[0] = idx
        btns = [tab_leader_btn, tab_badges_btn, tab_all_badges_btn]
        views = [leader_view, my_badges_view, all_badges_view]

        for i, (btn, v) in enumerate(zip(btns, views)):
            if i == idx:
                btn.bgcolor = PRIMARY
                btn.content.color = "white"
                v.visible = True
            else:
                btn.bgcolor = PRIMARY_LT
                btn.content.color = PRIMARY
                v.visible = False
        page.update()

    # ================================================================
    #  MY STATS CARD
    # ================================================================
    def _my_stats_card() -> ft.Container:
        s     = state.get("my_stats", {}) or {}
        raw_count = s.get("total_donations", 0)
        
        # ٹیکسٹ کو محفوظ طریقے سے نمبر میں تبدیل کرنے کا لاجک
        try:
            count = int(raw_count) if raw_count is not None else 0
        except (ValueError, TypeError):
            count = 0
        badge = s.get("donor_badge", "none")
        blood = s.get("blood_group", "?")
        name  = sess_get("full_name", "You")
        bc    = BLOOD_COLORS.get(blood, PRIMARY)

        # Next badge
        next_badge = None
        thresholds = [(1, "first_drop"), (5, "helper"), (10, "hero"), (20, "legend")]
        for threshold, btype in thresholds:
            if count < threshold:
                next_badge = (threshold, btype)
                break

        progress_text = ""
        if next_badge:
            needed = next_badge[0] - count
            em, en, ur, _, _, _ = BADGES.get(next_badge[1], ("🎯","","","","",""))
            progress_text = f"{needed} more donations to earn {em} {en}"

        return ft.Container(
            margin=ft.margin.symmetric(horizontal=14, vertical=8),
            padding=ft.padding.all(16),
            border_radius=20,
            bgcolor=PRIMARY,
            shadow=ft.BoxShadow(blur_radius=12, color="#33C62828", offset=ft.Offset(0, 4)),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        width=52, height=52, border_radius=26,
                        bgcolor=f"{bc}44", alignment=ft.Alignment(0, 0),
                        content=ft.Text(blood, size=14,
                                        weight=ft.FontWeight.BOLD, color="white"),
                    ),
                    ft.Container(width=12),
                    ft.Column([
                        ft.Text(name, size=15, weight=ft.FontWeight.BOLD, color="white"),
                        ft.Text(f"💉 {count} donations | عطیات",
                                size=12, color=PRIMARY_MD),
                    ], spacing=3, expand=True, tight=True),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        border_radius=12, bgcolor="#FFFFFF33",
                        content=ft.Text(
                            BADGES.get(badge, ("🌱","","","","",""))[0] + " " +
                            BADGES.get(badge, ("","Hero","","","",""))[1]
                            if badge != "none" else "🆕 New",
                            size=11, color="white", weight=ft.FontWeight.BOLD,
                        ),
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

                ft.Container(height=10),

                # Progress bar
                ft.Column([
                    ft.Text(progress_text, size=10, color=PRIMARY_MD),
                    ft.Container(height=4),
                    ft.Container(
                        height=6, border_radius=3, bgcolor="#FFFFFF33",
                        content=ft.Container(
                            height=6, border_radius=3, bgcolor="white",
                            width=max(4, int(200 * min(count / (next_badge[0] if next_badge else 20), 1.0))),
                        ),
                    ),
                ], spacing=0, tight=True) if next_badge else ft.Container(
                    padding=ft.padding.all(8),
                    border_radius=10, bgcolor="#FFFFFF22",
                    content=ft.Text("👑 Legend achieved! Maximum badge!", size=11, color="white"),
                ),
            ], spacing=0),
        )

    # ================================================================
    #  LEADERBOARD
    # ================================================================
    def _build_leaderboard():
        donors = state.get("top_donors", [])
        leader_col.controls.clear()

        # My stats card
        leader_col.controls.append(_my_stats_card())

        # Header
        leader_col.controls.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                content=ft.Row([
                    ft.Icon(ft.Icons.MILITARY_TECH_ROUNDED, color=GOLD, size=20),
                    ft.Text("Top Donors | بہترین ڈونرز", size=15,
                            weight=ft.FontWeight.BOLD, color=PRIMARY_DK),
                ], spacing=8),
            )
        )

        if not donors:
            leader_col.controls.append(_empty("🏆", "No donors yet\nابھی کوئی ڈونر نہیں"))
            try:
                page.update()
            except Exception:
                pass
            return

        medals = [
            ("🥇", GOLD,   "#FFF8E1"),
            ("🥈", SILVER, "#ECEFF1"),
            ("🥉", BRONZE, "#EFEBE9"),
        ]
        
        for i, d in enumerate(donors):
            name   = d.get("full_name", "---")
            blood  = d.get("blood_group", "?")
            city   = d.get("city", "")
            badge  = d.get("donor_badge", "")
            bc     = BLOOD_COLORS.get(blood, PRIMARY)
            raw_count = d.get("total_donations", 0)
            try:
                count = int(raw_count) if raw_count is not None else 0
            except (ValueError, TypeError):
                count = 0

            if i < 3:
                medal_em, medal_color, card_bg = medals[i]
            else:
                medal_em, medal_color, card_bg = f"{i+1}", TEXT_SUB, SURFACE

            badge_info = BADGES.get(badge, None)
            badge_chip = ft.Container()
            if badge_info:
                bem, ben, bur, _, bbg, bfg = badge_info
                badge_chip = ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    border_radius=10, bgcolor=bbg,
                    content=ft.Text(f"{bem} {ben}", size=9,
                                    color=bfg, weight=ft.FontWeight.BOLD),
                )

            is_me = d.get("id") == uid

            leader_col.controls.append(
                ft.Container(
                    bgcolor=card_bg,
                    border_radius=16,
                    margin=ft.margin.symmetric(horizontal=14, vertical=3),
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    shadow=ft.BoxShadow(
                        blur_radius=8 if i < 3 else 4,
                        color=f"{medal_color}44" if i < 3 else "#10000000",
                        offset=ft.Offset(0, 2),
                    ),
                    border=ft.Border(
                        left=ft.BorderSide(3 if is_me else 0, PRIMARY),
                        top=ft.BorderSide(0, "transparent"),
                        right=ft.BorderSide(0, "transparent"),
                        bottom=ft.BorderSide(0, "transparent"),
                    ),
                    content=ft.Row([
                        ft.Container(
                            width=32,
                            content=ft.Text(
                                medal_em, size=20 if i < 3 else 13,
                                color=medal_color,
                                text_align=ft.TextAlign.CENTER,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ),
                        ft.Container(
                            width=44, height=44, border_radius=22,
                            bgcolor=f"{bc}22", alignment=ft.Alignment(0, 0),
                            content=ft.Text(blood, size=11,
                                            weight=ft.FontWeight.BOLD, color=bc),
                        ),
                        ft.Container(width=10),
                        ft.Column([
                            ft.Row([
                                ft.Text(
                                    name + (" (You)" if is_me else ""),
                                    size=13, weight=ft.FontWeight.W_700,
                                    color=PRIMARY if is_me else TEXT,
                                ),
                                badge_chip,
                            ], spacing=6),
                            ft.Text(f"📍 {city}", size=11, color=TEXT_SUB),
                        ], expand=True, spacing=2, tight=True),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=10, bgcolor=PRIMARY_LT,
                            content=ft.Text(f"💉 {count}", size=13,
                                            color=PRIMARY, weight=ft.FontWeight.BOLD),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )

        leader_col.controls.append(ft.Container(height=40))
        try:
            page.update()
        except Exception:
            pass

    # ================================================================
    #  MY BADGES
    # ================================================================
    def _build_my_badges():
        my_badges = {b.get("badge_type"): b for b in state.get("my_badges", [])}
        my_badges_col.controls.clear()

        # Header
        my_badges_col.controls.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                content=ft.Text(
                    f"🎖️ {len(my_badges)} / {len(BADGES)} badges earned",
                    size=13, color=TEXT_SUB,
                ),
            )
        )

        for btype, (bem, ben, bur, breq, bbg, bfg) in BADGES.items():
            earned = btype in my_badges
            awarded_at = str(my_badges.get(btype, {}).get("awarded_at",""))[:10] if earned else ""

            my_badges_col.controls.append(
                ft.Container(
                    bgcolor=bbg if earned else "#FAFAFA",
                    border_radius=16,
                    margin=ft.margin.symmetric(horizontal=14, vertical=4),
                    padding=ft.padding.all(16),
                    opacity=1.0 if earned else 0.5,
                    shadow=ft.BoxShadow(
                        blur_radius=8 if earned else 2,
                        color=f"{bfg}33" if earned else "#10000000",
                        offset=ft.Offset(0, 2),
                    ),
                    content=ft.Row([
                        ft.Container(
                            width=60, height=60, border_radius=30,
                            bgcolor=f"{bfg}22" if earned else "#EEEEEE",
                            alignment=ft.Alignment(0, 0),
                            content=ft.Text(bem if earned else "🔒", size=32),
                        ),
                        ft.Container(width=14),
                        ft.Column([
                            ft.Text(f"{ben} | {bur}", size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color=bfg if earned else TEXT_SUB),
                            ft.Text(breq, size=12, color=TEXT_SUB),
                            ft.Text(
                                f"✅ Earned on {awarded_at}" if earned else "🔒 Not earned yet",
                                size=11,
                                color=bfg if earned else TEXT_SUB,
                            ),
                        ], expand=True, spacing=3, tight=True),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )

        my_badges_col.controls.append(ft.Container(height=40))
        try:
            page.update()
        except Exception:
            pass

    # ================================================================
    #  ALL BADGES (Community)
    # ================================================================
    def _build_all_badges():
        all_badges = state.get("all_badges", [])
        all_badges_col.controls.clear()

        all_badges_col.controls.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                content=ft.Text(
                    f"🏅 {len(all_badges)} badges awarded in community",
                    size=13, color=TEXT_SUB,
                ),
            )
        )

        if not all_badges:
            all_badges_col.controls.append(
                _empty("🏅", "No badges awarded yet\nابھی کوئی بیج نہیں")
            )
        else:
            for b in all_badges:
                btype = b.get("badge_type","")
                info  = BADGES.get(btype)
                if not info:
                    continue
                bem, ben, bur, breq, bbg, bfg = info
                donor_name = b.get("donor_name","---")
                awarded_at = str(b.get("awarded_at",""))[:10]
                count      = b.get("donations_at_award", 0)

                all_badges_col.controls.append(
                    ft.Container(
                        bgcolor=SURFACE, border_radius=12,
                        margin=ft.margin.symmetric(horizontal=14, vertical=3),
                        padding=ft.padding.symmetric(horizontal=14, vertical=10),
                        shadow=ft.BoxShadow(blur_radius=4, color="#10000000", offset=ft.Offset(0,1)),
                        content=ft.Row([
                            ft.Container(
                                width=44, height=44, border_radius=22,
                                bgcolor=bbg, alignment=ft.Alignment(0, 0),
                                content=ft.Text(bem, size=22),
                            ),
                            ft.Container(width=10),
                            ft.Column([
                                ft.Text(donor_name, size=13,
                                        weight=ft.FontWeight.W_700, color=TEXT),
                                ft.Row([
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                        border_radius=8, bgcolor=bbg,
                                        content=ft.Text(f"{bem} {ben}", size=10,
                                                        color=bfg, weight=ft.FontWeight.BOLD),
                                    ),
                                    ft.Text(f"💉 {count} donations", size=10, color=TEXT_SUB),
                                ], spacing=8),
                                ft.Text(f"📅 {awarded_at}", size=10, color="#9E9E9E"),
                            ], expand=True, spacing=2, tight=True),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    )
                )

        all_badges_col.controls.append(ft.Container(height=40))
        try:
            page.update()
        except Exception:
            pass

    # ================================================================
    #  HELPERS
    # ================================================================
    def _empty(emoji, text):
        return ft.Container(
            padding=ft.padding.all(40),
            alignment=ft.Alignment(0, 0),
            content=ft.Column([
                ft.Text(emoji, size=48),
                ft.Text(text, size=13, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        )

    # ================================================================
    #  DATA LOADER (Updated from members to profiles)
    # ================================================================
    def load_data(_=None):
        leader_col.controls = [
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
                await _restore()

                # ✅ Top donors: profiles table
                def _top():
                    return (
                        _sb.table("profiles")
                        .select("id, full_name, blood_group, city, total_donations, donor_badge")
                        .gt("total_donations", 0)
                        .order("total_donations", desc=True)
                        .limit(20)
                        .execute()
                    )
                res = await asyncio.to_thread(_top)
                state["top_donors"] = res.data or []

                # ✅ My stats: profiles table
                if uid:
                    def _my():
                        return (
                            _sb.table("profiles")
                            .select("total_donations, donor_badge, blood_group, last_donation_date")
                            .eq("id", uid)
                            .limit(1)
                            .execute()
                        )
                    mr = await asyncio.to_thread(_my)
                    state["my_stats"] = mr.data[0] if mr.data else {}

                    # My badges
                    def _my_badges():
                        return (
                            _sb.table("donor_badges")
                            .select("*")
                            .eq("donor_id", uid)
                            .execute()
                        )
                    mbr = await asyncio.to_thread(_my_badges)
                    state["my_badges"] = mbr.data or []

                # ✅ All badges with donor names: linked with profiles instead of members
                def _all_badges():
                    return (
                        _sb.table("donor_badges")
                        .select("*, profiles(full_name)")
                        .order("awarded_at", desc=True)
                        .limit(50)
                        .execute()
                    )
                abr = await asyncio.to_thread(_all_badges)
                raw = abr.data or []

                # Flatten donor name (Updated key lookup)
                for b in raw:
                    m = b.pop("profiles", None)
                    if isinstance(m, dict):
                        b["donor_name"] = m.get("full_name","---")
                    else:
                        b["donor_name"] = "---"

                state["all_badges"] = raw

                _build_leaderboard()
                _build_my_badges()
                _build_all_badges()

            except Exception as ex:
                print(f"[LEADER] error: {ex}")
                leader_col.controls = [
                    ft.Container(
                        padding=ft.padding.all(40),
                        content=ft.Column([
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color=PRIMARY, size=48),
                            ft.Text(f"Error: {str(ex)[:80]}", color=PRIMARY,
                                    size=12, text_align=ft.TextAlign.CENTER),
                            ft.TextButton("Retry", on_click=load_data),
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
        route="/leaderboard",
        bgcolor=BG,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/"),
            ),
            title=ft.Column([
                ft.Text("Leaderboard & Badges", size=15,
                        weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("لیڈر بورڈ اور بیجز", size=11, color=PRIMARY_MD),
            ], spacing=0),
            bgcolor=PRIMARY,
            actions=[
                ft.IconButton(ft.Icons.REFRESH_ROUNDED, icon_color="white",
                              on_click=load_data, tooltip="Refresh"),
            ],
        ),
        controls=[
            ft.Column(
                expand=True, spacing=0,
                controls=[
                    # Tab bar
                    ft.Container(
                        bgcolor=SURFACE,
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        content=ft.Row([
                            tab_leader_btn,
                            ft.Container(width=6),
                            tab_badges_btn,
                            ft.Container(width=6),
                            tab_all_badges_btn,
                        ], spacing=0),
                    ),
                    # Content
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            expand=True,
                            controls=[leader_view, my_badges_view, all_badges_view],
                            padding=ft.padding.only(bottom=20),
                        ),
                    ),
                ],
            ),
        ],
    )




