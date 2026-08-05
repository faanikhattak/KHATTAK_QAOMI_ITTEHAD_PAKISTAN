# ================================================================
#  pages/user/feedback.py
#  Feedback System + Success Stories
#  - Auto dialog after donation confirmation
#  - Standalone feedback page
#  - Public success stories wall
#  Flet 0.84 compatible | Session-safe
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
ORANGE     = "#E65100"
BG         = "#FFF5F5"
TEXT       = "#212121"
TEXT_SUB   = "#757575"
SURFACE    = "#FFFFFF"


# ================================================================
#  AUTO FEEDBACK DIALOG
#  Call this after donation is confirmed in donor.py
# ================================================================
def show_feedback_dialog(
    page: ft.Page,
    donation_id: str,
    request_id: int,
    donor_id: str,
    requester_id: str,
    blood_group: str,
    is_donor: bool = True,       # True = donor giving feedback, False = requester
    on_done=None,
):
    """
    Auto popup after donation confirmation.
    is_donor=True  → donor feedback form
    is_donor=False → requester feedback form
    """

    def sess_get(key, default=""):
        try:
            if hasattr(page.session, "_Session__store"):
                return page.session._Session__store.get(key) or default
            return page.session.get(key) or default
        except Exception:
            return default

    _sb = create_client(SUPABASE_URL_STR, SUPABASE_KEY_STR, options=http1_options())

    # ── Authorization gate ───────────────────────────────────
    # Only head_admin/admin, the donor on this donation, or the
    # requester (accepter) on this donation may submit feedback.
    def _show_not_authorized_popup():
        def _close_blocked():
            try:
                blocked.open = False
                page.close(blocked)
                page.update()
            except Exception:
                pass

        def _go_donor(e=None):
            _close_blocked()
            page.go("/donor")

        blocked = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.LOCK_OUTLINE, color=PRIMARY, size=22),
                    ft.Text("Not Part of This Donation", size=15,
                            weight=ft.FontWeight.BOLD, color=TEXT),
                ],
                spacing=8,
            ),
            content=ft.Container(
                width=300,
                content=ft.Text(
                    "Only the donor, the requester, or an admin involved in "
                    "this donation can submit feedback to complete it.\n\n"
                    "آپ اس عطیہ کے عمل کا حصہ نہیں ہیں — صرف ڈونر، درخواست "
                    "دہندہ یا ایڈمن ہی تاثر جمع کروا سکتے ہیں۔\n\n"
                    "Would you like to register as a blood donor instead?",
                    size=13, color=TEXT_SUB,
                ),
            ),
            actions=[
                ft.TextButton("Cancel | منسوخ", on_click=lambda e: _close_blocked()),
                ft.ElevatedButton(
                    "🩸 Donate Blood | خون عطیہ کریں",
                    style=ft.ButtonStyle(bgcolor=PRIMARY, color="white",
                                          shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=_go_donor,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if blocked not in page.overlay:
            page.overlay.append(blocked)
        blocked.open = True
        page.update()

    async def _check_authorized_and_open():
        try:
            at = sess_get("access_token")
            rt = sess_get("refresh_token", "")
            if at:
                await asyncio.to_thread(_sb.auth.set_session, at, rt)

            uid = sess_get("user_id")
            authorized = False

            if uid and (uid == donor_id or uid == requester_id):
                authorized = True

            if not authorized and uid:
                def _get_role():
                    return (
                        _sb.table("profiles")
                        .select("role")
                        .eq("id", uid)
                        .limit(1)
                        .execute()
                    )
                role_res = await asyncio.to_thread(_get_role)
                if role_res.data:
                    role = role_res.data[0].get("role")
                    if role in ("head_admin", "admin"):
                        authorized = True

            if not authorized:
                _show_not_authorized_popup()
                return

            _build_and_open_dialog()
        except Exception as ex:
            print(f"[FEEDBACK] authorization check error: {ex}")
            _show_not_authorized_popup()

    def _build_and_open_dialog():
        # Rating state
        rating_val = [0]
        star_refs  = []

        # Experience options (donor)
        experience_val = [None]

        def _close(e=None):
            try:
                dlg.open = False
                page.close(dlg)
                page.update()
            except Exception:
                pass
            if on_done:
                on_done()

        def _submit(comment: str, share_story: bool, story_title: str = ""):
            async def _do():
                try:
                    at = sess_get("access_token")
                    rt = sess_get("refresh_token","")
                    if at:
                        await asyncio.to_thread(_sb.auth.set_session, at, rt)

                    payload = {
                        "donation_id": donation_id,
                        "request_id":  request_id,
                        "is_public":   share_story,
                    }

                    if is_donor:
                        payload["donor_id"]         = donor_id
                        payload["donor_experience"] = experience_val[0]
                        payload["donor_comment"]    = comment
                    else:
                        payload["requester_id"]     = requester_id
                        payload["requester_rating"] = rating_val[0] or None
                        payload["requester_comment"] = comment

                    if share_story and story_title:
                        payload["story_title"] = story_title
                        payload["story_body"]  = comment

                    def _insert():
                        _sb.table("feedback").upsert(
                            payload,
                            on_conflict="donation_id",
                        ).execute()
                
                    await asyncio.to_thread(_insert)
                    _close()
                    _snack("✅ Feedback submitted! JazakAllah!", GREEN)

                except Exception as ex:
                    print(f"[FEEDBACK] submit error: {ex}")
                    _close()

            page.run_task(_do)

        def _snack(msg, color=PRIMARY):
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

        # ── Star rating (requester only) ─────────────────────────
        def _build_stars():
            stars = []
            for i in range(1, 6):
                ref = ft.Ref[ft.Text]()
                star_refs.append(ref)
                stars.append(
                    ft.GestureDetector(
                        content=ft.Text(
                            ref=ref,
                            value="☆",
                            size=36,
                            color=ORANGE,
                        ),
                        on_tap=lambda e, n=i: _set_rating(n),
                    )
                )
            return ft.Row(stars, alignment=ft.MainAxisAlignment.CENTER, spacing=4)

        def _set_rating(n: int):
            rating_val[0] = n
            for i, ref in enumerate(star_refs):
                if ref.current:
                    ref.current.value = "⭐" if i < n else "☆"
            try:
                page.update()
            except Exception:
                pass

        # ── Experience chips (donor only) ────────────────────────
        exp_chip_refs = {}

        def _build_experience():
            options = [
                ("easy",   "😊 Easy"),
                ("medium", "😐 Medium"),
                ("hard",   "😓 Hard"),
            ]
            chips = []
            for val, label in options:
                ref = ft.Ref[ft.Container]()
                exp_chip_refs[val] = ref
                chips.append(
                    ft.Container(
                        ref=ref,
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        border_radius=20,
                        bgcolor=PRIMARY_LT,
                        border=ft.Border(
                            top=ft.BorderSide(1, PRIMARY_MD),
                            bottom=ft.BorderSide(1, PRIMARY_MD),
                            left=ft.BorderSide(1, PRIMARY_MD),
                            right=ft.BorderSide(1, PRIMARY_MD),
                        ),
                        on_click=lambda e, v=val: _set_experience(v),
                        content=ft.Text(label, size=13, color=PRIMARY),
                    )
                )
            return ft.Row(chips, alignment=ft.MainAxisAlignment.CENTER, spacing=8)

        def _set_experience(val: str):
            experience_val[0] = val
            for v, ref in exp_chip_refs.items():
                if ref.current:
                    ref.current.bgcolor = PRIMARY if v == val else PRIMARY_LT
                    ref.current.content.color = "white" if v == val else PRIMARY
            try:
                page.update()
            except Exception:
                pass

        # ── Form fields ──────────────────────────────────────────
        comment_f = ft.TextField(
            label="Your feedback | آپ کا تاثر (optional)",
            multiline=True, min_lines=2, max_lines=4,
            border_radius=12, focused_border_color=PRIMARY,
        )
        story_title_f = ft.TextField(
            label="Story Title | کہانی کا عنوان",
            border_radius=12, focused_border_color=PRIMARY,
            visible=False,
        )
        # اگر اسٹائل دینا ضروری ہے تو یہ طریقہ استعمال کریں:
        share_toggle = ft.Switch(value=False)

        share_label = ft.Text(
            "Share Feedback Publicly",
            color="blue", # یا جو بھی کلر آپ دینا چاہیں
            size=14
        )
        share_row = ft.Row(controls=[share_toggle, share_label])
        # share_toggle = ft.Switch(
        #     value=False, active_color=GREEN,
        #     label="Share as Success Story | کامیابی کی کہانی شیئر کریں",
        #     label_style=ft.TextStyle(size=12, color=TEXT_SUB),
        #     on_change=lambda e: _toggle_story(e.control.value),
        # )

        def _toggle_story(val: bool):
            story_title_f.visible = val
            try:
                page.update()
            except Exception:
                pass

        # ── Dialog content ───────────────────────────────────────
        if is_donor:
            form_content = ft.Column([
                ft.Text("🩸 JazakAllah Khair!", size=20,
                        weight=ft.FontWeight.BOLD, color=GREEN,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(f"You donated {blood_group} blood",
                        size=13, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                ft.Container(height=12),
                ft.Text("How was your experience? | تجربہ کیسا رہا؟",
                        size=13, weight=ft.FontWeight.W_600, color=TEXT),
                _build_experience(),
                ft.Container(height=8),
                comment_f,
                ft.Container(height=8),
                share_toggle,
                story_title_f,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6, tight=True)
        else:
            form_content = ft.Column([
                ft.Text("🎉 Blood Received!", size=20,
                        weight=ft.FontWeight.BOLD, color=GREEN,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Rate your donor | ڈونر کو ریٹنگ دیں",
                        size=13, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                ft.Container(height=8),
                _build_stars(),
                ft.Container(height=8),
                comment_f,
                ft.Container(height=8),
                share_toggle,
                story_title_f,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6, tight=True)

        dlg = ft.AlertDialog(
            modal=True,
            content_padding=ft.padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=20),
            content=ft.Container(
                width=320,
                padding=ft.padding.all(20),
                content=form_content,
            ),
            actions=[
                ft.TextButton(
                    "Skip | چھوڑیں",
                    style=ft.ButtonStyle(color=TEXT_SUB),
                    on_click=_close,
                ),
                ft.ElevatedButton(
                    "Submit | جمع کریں",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY, color="white",
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=lambda e: _submit(
                        comment_f.value or "",
                        share_toggle.value,
                        story_title_f.value or "",
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # Kick off the authorization check; it opens either the real
    # feedback form (_build_and_open_dialog) or the donate-blood
    # redirect popup (_show_not_authorized_popup), never both.
    page.run_task(_check_authorized_and_open)


# ================================================================
#  FEEDBACK PAGE  (standalone)
# ================================================================
def view(page: ft.Page) -> ft.View:

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
            rt = sess_get("refresh_token","")
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
    selected_tab = [0]  # 0=My Donations, 1=Success Stories

    # ── Tab buttons ─────────────────────────────────────────
    tab_my_btn = ft.Container(
        expand=True, height=40, border_radius=10,
        bgcolor=PRIMARY, alignment=ft.Alignment(0, 0),
        content=ft.Text("My Donations | میرے عطیے", size=12,
                        color="white", weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_tab(0),
    )
    tab_stories_btn = ft.Container(
        expand=True, height=40, border_radius=10,
        bgcolor=PRIMARY_LT, alignment=ft.Alignment(0, 0),
        content=ft.Text("Success Stories | کامیابیاں", size=12,
                        color=PRIMARY, weight=ft.FontWeight.W_600),
        on_click=lambda e: _switch_tab(1),
    )

    my_col      = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    stories_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    my_view      = ft.Container(visible=True,  content=my_col)
    stories_view = ft.Container(visible=False, content=stories_col)

    def _switch_tab(idx: int):
        selected_tab[0] = idx
        if idx == 0:
            tab_my_btn.bgcolor      = PRIMARY
            tab_my_btn.content.color = "white"
            tab_stories_btn.bgcolor       = PRIMARY_LT
            tab_stories_btn.content.color = PRIMARY
            my_view.visible      = True
            stories_view.visible = False
        else:
            tab_my_btn.bgcolor      = PRIMARY_LT
            tab_my_btn.content.color = PRIMARY
            tab_stories_btn.bgcolor       = PRIMARY
            tab_stories_btn.content.color = "white"
            my_view.visible      = False
            stories_view.visible = True
            _load_stories()
        page.update()

    # ── My Donations ─────────────────────────────────────────
    def _load_my_donations():
        my_col.controls = [_spinner()]
        try:
            page.update()
        except Exception:
            pass

        async def _work():
            try:
                await _restore()
                uid = sess_get("user_id")
                if not uid:
                    my_col.controls = [_empty("🔐", "Please login first")]
                    page.update()
                    return

                def _fetch():
                    return (
                        _sb.table("donations")
                        .select("*")
                        .eq("donor_id", uid)
                        .order("donated_at", desc=True)
                        .execute()
                    )

                res = await asyncio.to_thread(_fetch)
                donations = res.data or []

                # Also load feedback already given
                def _fetch_fb():
                    return (
                        _sb.table("feedback")
                        .select("donation_id, donor_experience, donor_comment, requester_rating")
                        .eq("donor_id", uid)
                        .execute()
                    )
                fb_res = await asyncio.to_thread(_fetch_fb)
                fb_map = {f["donation_id"]: f for f in (fb_res.data or [])}

                my_col.controls.clear()

                if not donations:
                    my_col.controls.append(
                        _empty("💉", "No donations yet\nابھی کوئی عطیہ نہیں")
                    )
                else:
                    for d in donations:
                        my_col.controls.append(_donation_card(d, fb_map))

                page.update()

            except Exception as ex:
                print(f"[FEEDBACK] load error: {ex}")
                my_col.controls = [_empty("⚠", f"Error: {str(ex)[:60]}")]
                page.update()

        page.run_task(_work)

    def _donation_card(d: dict, fb_map: dict) -> ft.Container:
        don_id    = d.get("id")
        blood     = d.get("blood_group", "?")
        requester = d.get("requester_name", "---")
        hospital  = d.get("hospital_name", "")
        city      = d.get("city", "")
        date      = str(d.get("donated_at",""))[:10]
        has_fb    = don_id in fb_map
        fb        = fb_map.get(don_id, {})

        def _give_feedback(e):
            show_feedback_dialog(
                page=page,
                donation_id=don_id,
                request_id=d.get("request_id"),
                donor_id=d.get("donor_id",""),
                requester_id=d.get("requester_id",""),
                blood_group=blood,
                is_donor=True,
                on_done=_load_my_donations,
            )

        return ft.Container(
            bgcolor=SURFACE, border_radius=16,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(14),
            shadow=ft.BoxShadow(blur_radius=8, color="#15000000", offset=ft.Offset(0,2)),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        width=48, height=48, border_radius=24,
                        bgcolor=GREEN_LT, alignment=ft.Alignment(0,0),
                        content=ft.Text(blood, size=13,
                                        weight=ft.FontWeight.BOLD, color=GREEN),
                    ),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(f"🎉 Donated to: {requester}", size=13,
                                weight=ft.FontWeight.W_700, color=TEXT),
                        ft.Text(f"🏥 {hospital} — {city}", size=11, color=TEXT_SUB),
                        ft.Text(f"📅 {date}", size=10, color="#9E9E9E"),
                    ], expand=True, spacing=2, tight=True),
                ]),

                # Existing feedback
                ft.Container(
                    visible=has_fb,
                    bgcolor=GREEN_LT, border_radius=10,
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    margin=ft.margin.only(top=8),
                    content=ft.Column([
                        ft.Text(f"😊 Experience: {fb.get('donor_experience','')}", size=11, color=GREEN),
                        ft.Text(fb.get("donor_comment",""), size=11, color=GREEN),
                    ], spacing=2, tight=True),
                ),

                # Feedback button
                ft.Container(
                    visible=not has_fb,
                    margin=ft.margin.only(top=8),
                    content=ft.ElevatedButton(
                        "⭐ Give Feedback | تاثر دیں",
                        style=ft.ButtonStyle(
                            bgcolor=PRIMARY_LT, color=PRIMARY,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        height=38,
                        on_click=_give_feedback,
                    ),
                ),
            ], spacing=0),
        )

    # ── Success Stories ──────────────────────────────────────
    def _load_stories():
        stories_col.controls = [_spinner()]
        try:
            page.update()
        except Exception:
            pass

        async def _work():
            try:
                await _restore()

                def _fetch():
                    return (
                        _sb.table("feedback")
                        .select("*")
                        .eq("is_public", True)
                        .order("created_at", desc=True)
                        .limit(20)
                        .execute()
                    )

                res = await asyncio.to_thread(_fetch)
                stories = res.data or []

                stories_col.controls.clear()

                # Stats banner
                stories_col.controls.append(
                    ft.Container(
                        margin=ft.margin.symmetric(horizontal=14, vertical=4),
                        padding=ft.padding.all(16),
                        border_radius=16,
                        bgcolor=PRIMARY,
                        content=ft.Column([
                            ft.Text("❤️ Lives Saved", size=18,
                                    weight=ft.FontWeight.BOLD, color="white",
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text(f"{len(stories)} success stories shared",
                                    size=12, color=PRIMARY_MD,
                                    text_align=ft.TextAlign.CENTER),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                    )
                )

                if not stories:
                    stories_col.controls.append(
                        _empty("🌟", "No stories yet\nBe the first to share!")
                    )
                else:
                    for s in stories:
                        stories_col.controls.append(_story_card(s))

                page.update()

            except Exception as ex:
                print(f"[FEEDBACK] stories error: {ex}")
                stories_col.controls = [_empty("⚠", f"Error: {str(ex)[:60]}")]
                page.update()

        page.run_task(_work)

    def _story_card(s: dict) -> ft.Container:
        title   = s.get("story_title") or "Success Story"
        body    = s.get("story_body") or s.get("donor_comment") or s.get("requester_comment","")
        rating  = s.get("requester_rating")
        exp     = s.get("donor_experience","")
        date    = str(s.get("created_at",""))[:10]

        stars = "⭐" * (rating or 0) if rating else ""
        exp_emoji = {"easy": "😊", "medium": "😐", "hard": "😓"}.get(exp, "")

        return ft.Container(
            bgcolor=SURFACE, border_radius=16,
            margin=ft.margin.symmetric(horizontal=14, vertical=4),
            padding=ft.padding.all(16),
            shadow=ft.BoxShadow(blur_radius=8, color="#15000000", offset=ft.Offset(0,2)),
            border=ft.Border(
                left=ft.BorderSide(4, GREEN),
                top=ft.BorderSide(0,"transparent"),
                right=ft.BorderSide(0,"transparent"),
                bottom=ft.BorderSide(0,"transparent"),
            ),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        width=40, height=40, border_radius=20,
                        bgcolor=GREEN_LT, alignment=ft.Alignment(0,0),
                        content=ft.Text("❤️", size=20),
                    ),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(title, size=14,
                                weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Row([
                            ft.Text(stars, size=14) if stars else ft.Container(),
                            ft.Text(exp_emoji, size=14) if exp_emoji else ft.Container(),
                            ft.Text(date, size=10, color="#9E9E9E"),
                        ], spacing=8),
                    ], expand=True, spacing=2, tight=True),
                ]),
                ft.Container(height=8),
                ft.Text(body, size=13, color=TEXT_SUB),
            ], spacing=0),
        )

    # ── Helpers ──────────────────────────────────────────────
    def _spinner():
        return ft.Container(
            padding=ft.padding.all(40),
            alignment=ft.Alignment(0,0),
            content=ft.ProgressRing(color=PRIMARY, width=36, height=36, stroke_width=3),
        )

    def _empty(emoji, text):
        return ft.Container(
            padding=ft.padding.all(40),
            alignment=ft.Alignment(0,0),
            content=ft.Column([
                ft.Text(emoji, size=48),
                ft.Text(text, size=13, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        )

    # Initial load
    _load_my_donations()

    # ================================================================
    #  RETURN VIEW
    # ================================================================
    return ft.View(
        route="/feedback",
        bgcolor=BG,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color="white",
                on_click=lambda _: page.go("/"),
            ),
            title=ft.Column([
                ft.Text("Feedback & Stories", size=15,
                        weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("تاثرات اور کامیابیاں", size=11, color=PRIMARY_MD),
            ], spacing=0),
            bgcolor=PRIMARY,
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
                            tab_my_btn,
                            ft.Container(width=8),
                            tab_stories_btn,
                        ], spacing=0),
                    ),
                    # Content
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            expand=True,
                            controls=[my_view, stories_view],
                            padding=ft.padding.only(bottom=20),
                        ),
                    ),
                ],
            ),
        ],
    )

