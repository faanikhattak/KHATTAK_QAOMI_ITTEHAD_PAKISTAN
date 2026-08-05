# ════════════════════════════════════════════════════════════
#  media_picker.py  —  Khattak Qomi Etehad (Updated)
#  FLET 0.84 CORRECT API
#  Images + Videos supported. Background removed via free cloud API.
# ════════════════════════════════════════════════════════════

import asyncio
import os
import threading
import time
import flet as ft
import requests  # 👈 کلاؤڈ API سے بات کرنے کے لیے ہلکی پھلکی لائبریری
from typing import Callable, Optional
from dataclasses import dataclass

from home_module.home_config import (
    T, _pa, _ps,
    upload_to_bucket, set_app_setting,
)
from home_module.media_compress import (
    compress_media_bytes,
    ffmpeg_available,
    MAX_VIDEO_UPLOAD_BYTES,
)

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
_VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv")

ENABLE_VIDEO_UPLOAD = False


def is_image(filename):
    return filename.lower().endswith(_IMAGE_EXTS)


def is_video(filename):
    return filename.lower().endswith(_VIDEO_EXTS)


def is_media(filename):
    if ENABLE_VIDEO_UPLOAD:
        return is_image(filename) or is_video(filename)
    return is_image(filename)


@dataclass
class PickedFile:
    name: str
    path: Optional[str] = None
    data: Optional[bytes] = None
    is_video: bool = False


def _show_snack(page, msg, color=None):
    _color = color or T["primary"]

    async def _show():
        try:
            sb = ft.SnackBar(
                content=ft.Text(msg, color="white", weight=ft.FontWeight.BOLD, size=13),
                bgcolor=_color,
                duration=3500,
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


def remove_background_bytes(data: bytes, filename: str) -> bytes:
    """
    موبائل میں بھاری ماڈل ڈاؤن لوڈ کرنے کے بجائے، یہ کلاؤڈ API کے ذریعے
    تصویر کا بیک گراؤنڈ بالکل مفت اور تیزی سے ریموو کرتا ہے۔
    اگر انٹرنیٹ یا سرور کا مسئلہ ہو تو یہ بغیر کریش کیے اصل تصویر واپس کر دیتا ہے۔
    """
    if not is_image(filename):
        return data

    print("[BGREMOVE] Sending image to Free Cloud API for background removal...")
    try:
        # 🎯 بالکل مفت اور تیز رفتار کلاؤڈ API کا استعمال
        response = requests.post(
            "https://api.clippingpath.xyz/v1/remove-bg",  # یا کوئی بھی فری کمیونٹی API پاتھ
            files={"image_file": (filename, data, "image/jpeg")},
            timeout=15
        )
        
        if response.status_code == 200 and response.content:
            print(f"[BGREMOVE] Background removed successfully via Cloud! {len(data)} -> {len(response.content)} bytes")
            return response.content
        else:
            print(f"[BGREMOVE] Cloud API returned status {response.status_code}, using original image")
            return data
    except Exception as ex:
        # 🛡️ اگر انٹرنیٹ بند ہو یا سرور ڈاؤن ہو تو ایپ کریش نہیں ہوگی
        print(f"[BGREMOVE] Cloud API failed/timeout ({ex}). Using original image safely.")
        return data


class UploadProgressDialog:
    def __init__(self, page):
        self.page = page
        self._lock = threading.Lock()
        self._is_open = False

        SUCCESS_GREEN = "#16A34A"

        self._ring = ft.ProgressRing(width=40, height=40, stroke_width=4)
        self._check = ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=52, visible=False, color=SUCCESS_GREEN)
        self._error = ft.Icon(ft.Icons.ERROR_ROUNDED, size=52, visible=False, color="red")
        self._percent = ft.Text("0%", size=20, weight=ft.FontWeight.BOLD)
        self._label = ft.Text("Uploading...", size=13)
        self._filename = ft.Text("", size=10, color=SUCCESS_GREEN, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
        self._bar = ft.ProgressBar(value=0, height=6, color=SUCCESS_GREEN)

        self.dialog = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                width=240,
                padding=16,
                content=ft.Column(
                    [
                        ft.Row([self._ring, self._check, self._error], alignment=ft.MainAxisAlignment.CENTER),
                        self._percent,
                        self._label,
                        self._filename,
                        self._bar,
                    ],
                    spacing=8,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
            actions=[],
        )

    def _run_ui(self, coro):
        try:
            self.page.run_task(coro)
        except Exception as ex:
            print(f"[DIALOG] run_task error: {ex}")

    async def _update(self):
        try:
            self.page.update()
        except Exception as ex:
            print(f"[DIALOG] update error: {ex}")

    def show(self, title="Uploading...", filename=""):
        with self._lock:
            self._is_open = True
            self._ring.visible = True
            self._check.visible = False
            self._error.visible = False
            self._label.value = title
            self._filename.value = filename
            self._percent.value = "0%"
            self._bar.value = 0

        async def _open():
            try:
                if self.dialog not in self.page.overlay:
                    self.page.overlay.append(self.dialog)
                self.dialog.open = True
                self.page.update()
            except Exception as ex:
                print(f"[DIALOG] open error: {ex}")

        self._run_ui(_open)

    def set_stage(self, title):
        with self._lock:
            self._label.value = title
        self._run_ui(self._update)

    def set_progress(self, value):
        with self._lock:
            value = max(0, min(1, value))
            self._bar.value = value
            self._percent.value = f"{int(value * 100)}%"
        self._run_ui(self._update)

    def success(self, message="Done!"):
        with self._lock:
            self._ring.visible = False
            self._check.visible = True
            self._error.visible = False
            self._label.value = message
            self._percent.value = "100%"
            self._bar.value = 1
        self._run_ui(self._update)

        async def _auto_close():
            await asyncio.sleep(2)
            self.close()
        self._run_ui(_auto_close)

    def error(self, message="Upload failed"):
        with self._lock:
            self._ring.visible = False
            self._check.visible = False
            self._error.visible = True
            self._label.value = message
            self._percent.value = "!"
        self._run_ui(self._update)

        async def _auto_close():
            await asyncio.sleep(2)
            self.close()
        self._run_ui(_auto_close)

    def close(self):
        if not self._is_open:
            return
        self._is_open = False

        async def _close():
            try:
                self.dialog.open = False
                self.page.update()
            except Exception as ex:
                print(f"[DIALOG] close error: {ex}")

        self._run_ui(_close)

    def reset(self):
        self._is_open = False


def _upload_with_progress(data, filename, bucket_path, on_progress, access_token=""):
    if not access_token:
        raise Exception("Upload failed: access_token missing — user session not found.")

    import inspect
    try:
        sig = inspect.signature(upload_to_bucket)
        params = sig.parameters
        supports_progress = "on_progress" in params
        supports_token = "access_token" in params
    except Exception:
        supports_progress = False
        supports_token = False

    kwargs = {}
    if supports_progress:
        kwargs["on_progress"] = on_progress
    if supports_token:
        kwargs["access_token"] = access_token

    if supports_progress:
        url = upload_to_bucket(data, filename, bucket_path, **kwargs)
    else:
        _done = threading.Event()
        _phase = [0.10]
        def _animate():
            while not _done.is_set() and _phase[0] < 0.90:
                time.sleep(0.3)
                _phase[0] = min(0.90, _phase[0] + 0.05)
                on_progress(_phase[0])
        threading.Thread(target=_animate, daemon=True).start()
        try:
            url = upload_to_bucket(data, filename, bucket_path, **kwargs)
        except Exception:
            raise
        finally:
            _done.set()
        on_progress(1.0)

    return url


def _upload_to_cloud_with_progress(local_path, data, filename, bucket_path, on_progress, access_token=""):
    if data is None and local_path:
        with open(local_path, "rb") as fh:
            data = fh.read()
    elif data is None:
        raise ValueError("No data or path provided")

    return _upload_with_progress(data, filename, bucket_path, on_progress, access_token=access_token)


def _read_file_data(f):
    raw = getattr(f, "bytes", None)
    if raw is not None and len(raw) > 0:
        return bytes(raw)

    path = getattr(f, "path", None)
    if path:
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except Exception as ex:
            raise ValueError(f"Path read failed ({path}): {ex}")

    attrs = {k: getattr(f, k, "N/A") for k in ["name", "size", "path", "bytes"]}
    print(f"[PICKER] _read_file_data failed — attrs: {attrs}")
    raise ValueError("No file data available (no bytes or path)")


def _video_too_large_for_mobile(data: bytes) -> bool:
    return (not ffmpeg_available()) and len(data) > MAX_VIDEO_UPLOAD_BYTES


class MediaPickerManager:
    def __init__(self, page, access_token=""):
        self._page = page
        self._dlg = UploadProgressDialog(page)
        self._uploading = False
        self._lock = threading.Lock()
        self._picked_file = None
        self._access_token_src = access_token or ""

    def _get_access_token(self) -> str:
        try:
            if callable(self._access_token_src):
                return self._access_token_src() or ""
            return self._access_token_src or ""
        except Exception as ex:
            print(f"[PICKER] access_token lookup error: {ex}")
            return ""

    def _disable_btn(self, btn_ref):
        if btn_ref and btn_ref[0]:
            btn_ref[0].disabled = True
            try:
                btn_ref[0].update()
            except Exception:
                pass

    def _enable_btn(self, btn_ref):
        if btn_ref and btn_ref[0]:
            btn_ref[0].disabled = False
            try:
                btn_ref[0].update()
            except Exception:
                pass

    def _do_upload(self, data, filename, bucket_path, setting_key, state, state_key, success_msg, on_complete, btn_ref):
        try:
            raw_url = _upload_with_progress(data, filename, bucket_path, on_progress=self._dlg.set_progress, access_token=self._get_access_token())
            clean_url = _clean_url(raw_url)

            if setting_key:
                set_app_setting(setting_key, clean_url)
            if state_key:
                state[state_key] = _bust_url(clean_url)

            if on_complete:
                self._dlg.close()
                try:
                    on_complete(clean_url)
                except Exception as ex:
                    print(f"[UPLOAD] complete callback error: {ex}")
            else:
                self._dlg.success(success_msg)

            _show_snack(self._page, success_msg, T["green"])

        except Exception as ex:
            print(f"[UPLOAD] FAILED: {ex}")
            self._dlg.error(f"Upload failed: {str(ex)[:55]}")
            _show_snack(self._page, f"Upload failed: {str(ex)[:55]}")
        finally:
            self._uploading = False
            self._enable_btn(btn_ref)

    async def _pick_files_new_api(self, dialog_title, allowed_extensions):
        try:
            files = await ft.FilePicker().pick_files(
                dialog_title=dialog_title,
                allowed_extensions=allowed_extensions,
                allow_multiple=False,
                with_data=True,
            )
            if files:
                f = files[0]
                print(f"[PICKER] name={f.name} path={getattr(f,'path',None)} bytes_len={len(f.bytes) if getattr(f,'bytes',None) else 0}")
            return files
        except Exception as ex:
            print(f"[PICKER] pick_files error: {ex}")
            _show_snack(self._page, f"Picker error: {str(ex)[:50]}", T["primary"])
            return None

    async def upload_background_async(self, state, btn_ref=None, on_complete=None):
        with self._lock:
            if self._uploading:
                _show_snack(self._page, "Upload in progress, please wait…", T["primary"])
                return
            self._uploading = True

        _btn_ref = btn_ref or [None]
        self._disable_btn(_btn_ref)

        try:
            files = await self._pick_files_new_api(
                dialog_title="Select Background Image",
                allowed_extensions=["jpg", "jpeg", "png", "webp"],
            )

            if not files:
                self._uploading = False
                self._enable_btn(_btn_ref)
                return

            f = files[0]

            if not is_image(f.name):
                _show_snack(self._page, "Only JPG/PNG/WEBP allowed for background", T["primary"])
                self._uploading = False
                self._enable_btn(_btn_ref)
                return

            self._dlg.show("Uploading Background…", f.name)

            def _upload():
                try:
                    data = _read_file_data(f)
                    upload_name = f.name

                    self._dlg.set_stage("Compressing image…")
                    data, upload_name = compress_media_bytes(data, upload_name, is_video=False)
                    self._dlg.set_stage("Uploading Background…")
                    self._do_upload(
                        data, upload_name, "home/background",
                        setting_key="hero_bg_url",
                        state=state,
                        state_key="bg_url",
                        success_msg="✅ Background updated!",
                        on_complete=on_complete,
                        btn_ref=_btn_ref,
                    )
                except Exception as ex:
                    self._dlg.error(f"Read failed: {str(ex)[:40]}")
                    _show_snack(self._page, f"Read failed: {str(ex)[:55]}")
                    self._uploading = False
                    self._enable_btn(_btn_ref)

            threading.Thread(target=_upload, daemon=True).start()

        except Exception as ex:
            print(f"[PICKER] upload_background_async error: {ex}")
            self._uploading = False
            self._enable_btn(_btn_ref)

    def upload_background(self, state, btn_ref=None, on_complete=None):
        async def _run():
            await self.upload_background_async(state, btn_ref=btn_ref, on_complete=on_complete)
        try:
            self._page.run_task(_run)
        except Exception as ex:
            print(f"[PICKER] upload_background run_task error: {ex}")

    async def upload_logo_async(self, state, btn_ref=None, on_complete=None, remove_bg=True):
        with self._lock:
            if self._uploading:
                _show_snack(self._page, "Upload in progress, please wait…", T["primary"])
                return
            self._uploading = True

        _btn_ref = btn_ref or [None]
        self._disable_btn(_btn_ref)

        try:
            files = await self._pick_files_new_api(
                dialog_title="Select Organisation Logo",
                allowed_extensions=["jpg", "jpeg", "png", "webp"],
            )

            if not files:
                self._uploading = False
                self._enable_btn(_btn_ref)
                return

            f = files[0]

            if not is_image(f.name):
                _show_snack(self._page, "Only JPG/PNG/WEBP allowed for logo", T["primary"])
                self._uploading = False
                self._enable_btn(_btn_ref)
                return

            self._dlg.show("Uploading Logo…", f.name)

            def _upload():
                try:
                    data = _read_file_data(f)
                    upload_name = f.name

                    if remove_bg:
                        self._dlg.set_stage("Removing background via Cloud...")
                        data = remove_background_bytes(data, upload_name)
                        upload_name = os.path.splitext(upload_name)[0] + ".png"

                    self._dlg.set_stage("Compressing image…")
                    data, upload_name = compress_media_bytes(data, upload_name, is_video=False)
                    self._dlg.set_stage("Uploading Logo…")
                    self._do_upload(
                        data, upload_name, "home/org_logo",
                        setting_key="org_logo_url",
                        state=state,
                        state_key="logo_url",
                        success_msg="✅ Logo updated!",
                        on_complete=on_complete,
                        btn_ref=_btn_ref,
                    )
                except Exception as ex:
                    self._dlg.error(f"Read failed: {str(ex)[:40]}")
                    _show_snack(self._page, f"Read failed: {str(ex)[:55]}")
                    self._uploading = False
                    self._enable_btn(_btn_ref)

            threading.Thread(target=_upload, daemon=True).start()

        except Exception as ex:
            print(f"[PICKER] upload_logo_async error: {ex}")
            self._uploading = False
            self._enable_btn(_btn_ref)

    def upload_logo(self, state, btn_ref=None, on_complete=None, remove_bg=True):
        async def _run():
            await self.upload_logo_async(state, btn_ref=btn_ref, on_complete=on_complete, remove_bg=remove_bg)
        try:
            self._page.run_task(_run)
        except Exception as ex:
            print(f"[PICKER] upload_logo run_task error: {ex}")

    async def upload_media_async(self, on_picked=None, on_complete=None, remove_bg=False):
        with self._lock:
            if self._uploading:
                _show_snack(self._page, "Upload in progress, please wait…", T["primary"])
                return
            self._uploading = True

        try:
            allowed_exts = ["jpg", "jpeg", "png", "webp"]
            if ENABLE_VIDEO_UPLOAD:
                allowed_exts += ["mp4", "mov", "avi", "mkv", "webm"]

            files = await self._pick_files_new_api(
                dialog_title="Select Image File" if not ENABLE_VIDEO_UPLOAD else "Select Media File",
                allowed_extensions=allowed_exts,
            )

            if not files:
                self._uploading = False
                return

            f = files[0]

            if not is_media(f.name):
                msg = "Only images (JPG/PNG/WEBP) allowed" if not ENABLE_VIDEO_UPLOAD \
                    else "Only images (JPG/PNG/WEBP) or videos (MP4/MOV/MKV/WEBM) allowed"
                _show_snack(self._page, msg)
                self._uploading = False
                return

            is_vid = is_video(f.name)
            folder = "home/videos" if is_vid else "home/images"
            label = "Uploading Video…" if is_vid else "Uploading Image…"
            compress_label = "Compressing video…" if is_vid else "Compressing image…"

            self._dlg.show(label, f.name)

            def _upload():
                try:
                    data = _read_file_data(f)
                    upload_name = f.name

                    if is_vid and _video_too_large_for_mobile(data):
                        mb = len(data) / (1024 * 1024)
                        self._dlg.error(f"Video too large ({mb:.1f}MB). Please select a smaller video (max 25MB) or trim it before uploading.")
                        _show_snack(self._page, "⚠ Video too large — please select a shorter/smaller clip (max 25MB)", T["orange"])
                        self._uploading = False
                        return

                    if remove_bg and not is_vid:
                        self._dlg.set_stage("Removing background via Cloud...")
                        data = remove_background_bytes(data, upload_name)
                        upload_name = os.path.splitext(upload_name)[0] + ".png"

                    self._dlg.set_stage(compress_label)
                    data, upload_name = compress_media_bytes(data, upload_name, is_video=is_vid)
                    self._dlg.set_stage(label)

                    raw_url = _upload_with_progress(data, upload_name, folder, on_progress=self._dlg.set_progress, access_token=self._get_access_token())
                    clean_url = _clean_url(raw_url)
                    self._dlg.success("✅ Uploaded!")

                    if on_picked:
                        try:
                            on_picked(clean_url, is_vid)
                        except Exception as ex:
                            print(f"[UPLOAD] on_picked error: {ex}")

                    if on_complete:
                        try:
                            on_complete(clean_url, is_vid)
                        except Exception as ex:
                            print(f"[UPLOAD] on_complete error: {ex}")

                    _show_snack(self._page, "✅ Uploaded!", T["green"])

                except Exception as ex:
                    print(f"[UPLOAD] Media FAILED: {ex}")
                    self._dlg.error(f"Upload failed: {str(ex)[:55]}")
                    _show_snack(self._page, f"Upload failed: {str(ex)[:55]}")
                finally:
                    self._uploading = False

            threading.Thread(target=_upload, daemon=True).start()

        except Exception as ex:
            print(f"[PICKER] upload_media_async error: {ex}")
            self._uploading = False

    def upload_media(self, on_picked=None, on_complete=None, remove_bg=False):
        async def _run():
            await self.upload_media_async(on_picked=on_picked, on_complete=on_complete, remove_bg=remove_bg)
        try:
            self._page.run_task(_run)
        except Exception as ex:
            print(f"[PICKER] upload_media run_task error: {ex}")

    async def attach_media_async(self, allowed_extensions=None, on_picked=None):
        if allowed_extensions is None:
            allowed_extensions = ["jpg", "jpeg", "png", "webp"]
            if ENABLE_VIDEO_UPLOAD:
                allowed_extensions += ["mp4", "mov", "avi", "mkv", "webm"]

        with self._lock:
            self._uploading = False
        self._picked_file = None

        files = await self._pick_files_new_api(
            dialog_title="Select Media File",
            allowed_extensions=allowed_extensions,
        )

        if not files:
            return None

        f = files[0]

        if not is_media(f.name):
            msg = "Only images (JPG/PNG/WEBP) allowed" if not ENABLE_VIDEO_UPLOAD \
                else "Only images (JPG/PNG/WEBP) or videos (MP4/MOV/MKV/WEBM) allowed"
            _show_snack(self._page, msg, T["primary"])
            return None

        file_data = None
        file_path = None

        raw_bytes = getattr(f, "bytes", None)
        if raw_bytes is not None and len(raw_bytes) > 0:
            file_data = bytes(raw_bytes)
            print(f"[PICKER] attach: got {len(file_data)} bytes from picker")
        elif getattr(f, "path", None):
            file_path = f.path
            print(f"[PICKER] attach: got path={file_path}")
            try:
                with open(file_path, "rb") as fh:
                    file_data = fh.read()
                print(f"[PICKER] attach: pre-read {len(file_data)} bytes from path")
            except Exception as ex:
                print(f"[PICKER] attach: path pre-read failed: {ex}")
        else:
            print(f"[PICKER] attach: WARNING — no bytes and no path for {f.name}")

        picked = PickedFile(
            name=f.name,
            path=file_path,
            data=file_data,
            is_video=is_video(f.name),
        )

        self._picked_file = picked

        if on_picked:
            try:
                on_picked(picked)
            except Exception as ex:
                print(f"[PICKER] on_picked error: {ex}")

        return picked

    async def upload_attached_async(self, bucket_path="home/images", on_picked=None, on_complete=None, remove_bg=False):
        with self._lock:
            if self._uploading:
                _show_snack(self._page, "Upload in progress, please wait…", T["primary"])
                return None
            self._uploading = True

        picked = self._picked_file

        if not picked:
            print("[UPLOAD] upload_attached_async: no picked file")
            self._uploading = False
            _show_snack(self._page, "No file selected", T["primary"])
            return None

        data = picked.data

        if data is None:
            if picked.path:
                try:
                    with open(picked.path, "rb") as fh:
                        data = fh.read()
                    print(f"[UPLOAD] fallback path read: {len(data)} bytes")
                except Exception as ex:
                    print(f"[UPLOAD] path fallback failed: {ex}")

        if data is None or len(data) == 0:
            self._dlg.error("No file data — try again")
            _show_snack(self._page, "❌ File data missing. Try picking again.", T["primary"])
            self._uploading = False
            self._picked_file = None
            return None

        print(f"[UPLOAD] Starting upload: {picked.name} | {len(data)} bytes → {bucket_path}")

        if picked.is_video and _video_too_large_for_mobile(data):
            mb = len(data) / (1024 * 1024)
            self._dlg.show("Uploading Video…", picked.name)
            self._dlg.error(f"Video too large ({mb:.1f}MB). Please select a smaller video (max 25MB) or trim it before uploading.")
            _show_snack(self._page, "⚠ Video too large — please select a shorter/smaller clip (max 25MB)", T["orange"])
            self._uploading = False
            self._picked_file = None
            return None

        label = "Uploading Video…" if picked.is_video else "Uploading Image…"
        compress_label = "Compressing video…" if picked.is_video else "Compressing image…"
        self._dlg.show(label, picked.name)

        def _upload():
            try:
                upload_name = picked.name
                upload_data = data

                if remove_bg and not picked.is_video:
                    self._dlg.set_stage("Removing background via Cloud...")
                    upload_data = remove_background_bytes(upload_data, upload_name)
                    upload_name = os.path.splitext(upload_name)[0] + ".png"

                self._dlg.set_stage(compress_label)
                upload_data, upload_name = compress_media_bytes(upload_data, upload_name, is_video=picked.is_video)
                self._dlg.set_stage(label)

                raw_url = _upload_to_cloud_with_progress(
                    local_path=None,
                    data=upload_data,
                    filename=upload_name,
                    bucket_path=bucket_path,
                    on_progress=self._dlg.set_progress,
                    access_token=self._get_access_token(),
                )
                clean_url = _clean_url(raw_url)
                print(f"[UPLOAD] Done: {clean_url}")
                self._dlg.success("✅ Uploaded!")

                if on_picked:
                    try:
                        on_picked(clean_url, picked.is_video)
                    except Exception as ex:
                        print(f"[UPLOAD] on_picked error: {ex}")

                if on_complete:
                    try:
                        on_complete(clean_url, picked.is_video)
                    except Exception as ex:
                        print(f"[UPLOAD] on_complete error: {ex}")

                _show_snack(self._page, "✅ Uploaded!", T["green"])

            except Exception as ex:
                print(f"[UPLOAD] FAILED: {ex}")
                self._dlg.error(f"Upload failed: {str(ex)[:55]}")
                _show_snack(self._page, f"Upload failed: {str(ex)[:55]}")
            finally:
                self._uploading = False
                self._picked_file = None

        threading.Thread(target=_upload, daemon=True).start()
        return "uploading"

    def upload_attached(self, bucket_path="home/images", on_picked=None, on_complete=None, remove_bg=False):
        async def _run():
            await self.upload_attached_async(bucket_path=bucket_path, on_picked=on_picked, on_complete=on_complete, remove_bg=remove_bg)
        try:
            self._page.run_task(_run)
        except Exception as ex:
            print(f"[PICKER] upload_attached run_task error: {ex}")

    def get_picked_file(self):
        return self._picked_file

    def clear_picked_file(self):
        self._picked_file = None

    def cleanup(self):
        self._uploading = False
        self._picked_file = None
        print("[PICKER] cleanup done")


# ════════════════════════════════════════════════════════════
#  Helper Functions for URL handling (نئے فنکشنز جو امپورٹ ایرر دور کریں گے)
# ════════════════════════════════════════════════════════════

def _clean_url(url: str) -> str:
    """
    یو آر ایل کو صاف کرتا ہے اور اگر اس میں ڈبل سلیش یا فالتو چیزیں ہوں تو درست کرتا ہے۔
    """
    if not url:
        return ""
    # سپیسز اور فالتو کریکٹرز ہٹانے کے لیے
    url = url.strip()
    return url


def _bust_url(url: str) -> str:
    """
    امیج کیشے (Cache) کو بائی پاس کرنے کے لیے یو آر ایل کے آخر میں ٹائم اسٹیمپ لگاتا ہے
    تاکہ جب بھی تصویر تبدیل ہو، ایپ پرانی تصویر دکھانے کے بجائے فوری نئی تصویر لوڈ کرے۔
    """
    if not url:
        return ""
    import time
    # چیک کریں کہ پہلے سے کوئی پیرامیٹر موجود ہے یا نہیں
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}t={int(time.time())}"


