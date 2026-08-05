import datetime
import threading
import traceback

import flet as ft
from services.database.db import supabase

try:
    from services.database.db import supabase_admin
except ImportError:
    print("[SUPPORT] supabase_admin not found — using supabase")
    supabase_admin = supabase


def build_support_dialog(page: ft.Page, profile: dict, on_sent=None, on_closed=None) -> ft.AlertDialog:
    name_field = ft.TextField(
        label="Name | نام",
        value=profile.get("full_name", "") or "",
    )
    phone_field = ft.TextField(
        label="Phone | فون نمبر",
        value=profile.get("phone", "") or "",
        keyboard_type=ft.KeyboardType.PHONE,
    )
    message_field = ft.TextField(
        label="How can we help? | مسئلہ بیان کریں",
        multiline=True,
        min_lines=3,
        max_lines=6,
    )
    error_text = ft.Text("", color="#C62828", size=11, visible=False)

    _busy = {"on": False}

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Text("Contact Support | رابطہ کریں", weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.IconButton(
                    ft.Icons.CLOSE_ROUNDED,
                    icon_size=18,
                    tooltip="Close",
                    on_click=lambda e: _close(),
                ),
            ]
        ),
        content=ft.Container(
            width=320,
            content=ft.Column(
                [name_field, phone_field, message_field, error_text],
                tight=True,
                spacing=10,
            ),
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # ✅ SAFE CLOSE (delayed removal so Flet's close animation/barrier
    # fully clears before the control leaves the overlay — same 0.3s
    # pattern already used for PickerManager elsewhere in this app)
    def _close():
        dlg.open = False
        page.update()

        def _remove():
            if dlg in page.overlay:
                page.overlay.remove(dlg)
                try:
                    page.update()
                except Exception as e:
                    print("[SUPPORT] close update skipped:", e)
            if on_closed:
                on_closed()

        threading.Timer(0.3, _remove).start()

    # ✅ SUBMIT HANDLER
    def _submit(e=None):
        print("🔴 [SUPPORT] SEND CLICKED")

        if _busy["on"]:
            return

        msg = (message_field.value or "").strip()
        if not msg:
            error_text.value = "Please describe your issue."
            error_text.visible = True
            page.update()
            return

        _busy["on"] = True
        send_btn.disabled = True
        cancel_btn.disabled = True
        error_text.visible = False
        page.update()

        # 🔧 BACKGROUND THREAD
        def _save():
            try:
                supabase_admin.table("support_requests").insert(
                    {
                        "user_id": profile.get("id") or profile.get("uid"),
                        "name": (name_field.value or "").strip() or None,
                        "phone": (phone_field.value or "").strip() or None,
                        "message": msg,
                        "status": "open",
                        "created_at": datetime.datetime.utcnow().isoformat(),
                    }
                ).execute()

                print("[SUPPORT] insert OK")

                def _safe_update():
                    # 🛡️ GUARD: page/session may already be disposed if user
                    # navigated away or disconnected while the request was in flight.
                    try:
                        page.update()
                    except Exception as e:
                        print("[SUPPORT] page.update() skipped — session gone:", e)

                def _ui_success():
                    try:
                        print("[SUPPORT] Updating UI")

                        dlg.open = False
                        _safe_update()

                        def _finish_close():
                            if dlg in page.overlay:
                                page.overlay.remove(dlg)
                                _safe_update()

                            success_snack = ft.SnackBar(
                                content=ft.Text("✅ Request submitted successfully!"),
                                bgcolor=ft.Colors.GREEN_600,
                            )
                            page.overlay.append(success_snack)
                            success_snack.open = True
                            _safe_update()

                            # clean the snackbar out of overlay after it's had
                            # time to show, so overlay doesn't grow forever
                            def _drop_snack():
                                if success_snack in page.overlay:
                                    page.overlay.remove(success_snack)
                                    _safe_update()

                            threading.Timer(4.0, _drop_snack).start()

                            _busy["on"] = False
                            send_btn.disabled = False
                            cancel_btn.disabled = False
                            _safe_update()

                            if on_sent:
                                on_sent()

                            print("[SUPPORT] UI DONE")

                        threading.Timer(0.3, _finish_close).start()

                    except Exception as e:
                        print("[SUPPORT UI ERROR]", e)

                # 🔥 FIX: call directly, no call_from_thread (method doesn't exist in this Flet version)
                _ui_success()

            except Exception as ex:
                print("[SUPPORT ERROR]", ex)
                traceback.print_exc()

                def _ui_fail():
                    error_text.value = "Send failed. Try again."
                    error_text.visible = True
                    _busy["on"] = False
                    send_btn.disabled = False
                    cancel_btn.disabled = False
                    try:
                        page.update()
                    except Exception as e:
                        print("[SUPPORT] page.update() skipped — session gone:", e)

                # 🔥 FIX: call directly, no call_from_thread
                _ui_fail()

        threading.Thread(target=_save, daemon=True).start()

    # ✅ BUTTONS
    send_btn = ft.ElevatedButton(
        "Send | بھیجیں",
        on_click=_submit,
        style=ft.ButtonStyle(bgcolor="#C62828", color="white"),
    )

    cancel_btn = ft.TextButton("Cancel", on_click=lambda e: _close())

    dlg.actions = [cancel_btn, send_btn]

    return dlg


# ✅ OPEN DIALOG SAFELY (NO DUPLICATE)
def show_support_dialog(page: ft.Page, profile: dict, on_sent=None):
    prev = getattr(page, "_support_dialog_ref", None)

    if prev and prev in page.overlay and prev.open:
        return

    def _mark_closed():
        page._support_dialog_ref = None

    dlg = build_support_dialog(
        page,
        profile,
        on_sent=on_sent,
        on_closed=_mark_closed,
    )

    page._support_dialog_ref = dlg

    if dlg not in page.overlay:
        page.overlay.append(dlg)

    dlg.open = True
    page.update()