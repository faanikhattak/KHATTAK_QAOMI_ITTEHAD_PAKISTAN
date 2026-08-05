# ════════════════════════════════════════════════════════════
#  media_compress.py  —  Khattak Qomi Etehad
#  Compress images (Pillow) and videos (ffmpeg) BEFORE upload
#  to reduce bandwidth + Supabase storage usage.
#
#  NOTE (IMPORTANT — desktop vs mobile):
#   - Image compression (Pillow) works on ALL platforms
#     (Windows/Mac/Linux/Android/iOS) since it's pure Python.
#   - Video compression uses the external `ffmpeg` binary via
#     subprocess. This ONLY works where ffmpeg is installed and
#     on PATH — i.e. Windows/Mac/Linux desktop builds. On mobile
#     (Android/iOS) there is no ffmpeg binary available unless you
#     separately bundle/compile one, which Flet does not do for
#     you. On mobile, compress_video_bytes() will safely skip and
#     upload the original video (no crash — just no compression).
# ════════════════════════════════════════════════════════════

import io
import os
import shutil
import subprocess
import tempfile
from typing import Tuple

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ── Tunable limits ──────────────────────────────────────────
IMAGE_MAX_DIMENSION = 1600        # longest side in px, after resize
IMAGE_JPEG_QUALITY  = 78          # 0-100, higher = better quality/bigger
IMAGE_MAX_BYTES     = 1_500_000   # ~1.5 MB soft cap — re-compress if bigger

VIDEO_MAX_HEIGHT    = 720         # px, keeps aspect ratio
VIDEO_CRF           = 28          # quality: lower = better/bigger, 23 default
VIDEO_AUDIO_BITRATE = "96k"

# On Android/iOS APK builds there is no ffmpeg binary shipped with Flet,
# so compress_video_bytes() silently skips compression there (see module
# docstring). As a safety net for mobile, reject videos above this size
# instead of uploading a huge uncompressed file. Desktop builds (where
# ffmpeg IS available) are never affected by this cap.
MAX_VIDEO_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _has_alpha(img: "Image.Image") -> bool:
    if img.mode in ("RGBA", "LA"):
        return True
    if img.mode == "P" and "transparency" in img.info:
        return True
    return False


def compress_image_bytes(
    data: bytes,
    filename: str,
    max_dimension: int = IMAGE_MAX_DIMENSION,
    quality: int = IMAGE_JPEG_QUALITY,
) -> Tuple[bytes, str]:
    """
    Resize + re-encode image bytes to reduce file size.
    Returns (compressed_bytes, new_filename).
    Falls back to the original bytes if Pillow isn't installed or
    compression fails for any reason — upload never breaks because
    of this step.

    IMPORTANT: images with an alpha channel (e.g. a background-removed
    logo) are encoded as WEBP, not JPEG. JPEG has no alpha channel at
    all — saving a transparent image as JPEG silently flattens it onto
    an opaque background, which was the cause of "background isn't
    transparent" after upload even though the removal step itself
    worked fine. WEBP keeps the alpha channel and still compresses
    well; opaque images are unaffected and still go out as JPEG.
    """
    if not HAS_PIL:
        print("[COMPRESS] Pillow not installed — skipping image compression")
        return data, filename

    try:
        img = Image.open(io.BytesIO(data))
        has_alpha = _has_alpha(img)

        if has_alpha:
            img = img.convert("RGBA")  # keep transparency
        else:
            img = img.convert("RGB")  # drops alpha/palette, needed for JPEG

        w, h = img.size
        longest = max(w, h)
        if longest > max_dimension:
            scale = max_dimension / longest
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        def _encode(q):
            buf = io.BytesIO()
            if has_alpha:
                img.save(buf, format="WEBP", quality=q, method=6)
            else:
                img.save(buf, format="JPEG", quality=q, optimize=True)
            return buf

        q = quality
        out = _encode(q)

        # If still above soft cap, step quality down a few times
        tries = 0
        while out.tell() > IMAGE_MAX_BYTES and q > 40 and tries < 3:
            q -= 15
            out = _encode(q)
            tries += 1

        compressed = out.getvalue()
        base = filename.rsplit(".", 1)[0] if "." in filename else filename
        ext = "webp" if has_alpha else "jpg"
        new_name = f"{base}.{ext}"

        saved_pct = 100 - int(len(compressed) / max(len(data), 1) * 100)
        print(f"[COMPRESS] Image {filename}: {len(data)} -> {len(compressed)} bytes ({saved_pct}% smaller, alpha={has_alpha})")

        return compressed, new_name

    except Exception as ex:
        print(f"[COMPRESS] Image compression failed, using original: {ex}")
        return data, filename


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def ffmpeg_available() -> bool:
    """
    Public check for callers (e.g. media_picker.py) that need to know
    BEFORE compressing whether ffmpeg will actually run. Returns False
    on Android/iOS APK/IPA builds since no ffmpeg binary ships there —
    callers should use this to enforce MAX_VIDEO_UPLOAD_BYTES on mobile.
    """
    return _ffmpeg_available()


def compress_video_bytes(
    data: bytes,
    filename: str,
    max_height: int = VIDEO_MAX_HEIGHT,
    crf: int = VIDEO_CRF,
) -> Tuple[bytes, str]:
    """
    Downscale + re-encode video bytes via ffmpeg (H.264 + AAC).
    Requires the `ffmpeg` binary on PATH (desktop only — see module
    docstring). Falls back to the original bytes if ffmpeg is missing
    or the conversion fails, so upload never breaks.
    """
    if not _ffmpeg_available():
        print("[COMPRESS] ffmpeg not found on PATH — skipping video compression")
        return data, filename

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp4"
    base = filename.rsplit(".", 1)[0] if "." in filename else filename
    new_name = f"{base}.mp4"

    tmp_dir = tempfile.mkdtemp(prefix="media_compress_")
    in_path = os.path.join(tmp_dir, f"input.{ext}")
    out_path = os.path.join(tmp_dir, "output.mp4")

    try:
        with open(in_path, "wb") as fh:
            fh.write(data)

        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-vf", f"scale=-2:'min({max_height},ih)'",
            "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
            "-c:a", "aac", "-b:a", VIDEO_AUDIO_BITRATE,
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)

        if result.returncode != 0 or not os.path.exists(out_path):
            err_msg = result.stderr.decode(errors="ignore")[-300:]
            print(f"[COMPRESS] ffmpeg failed: {err_msg}")
            return data, filename

        with open(out_path, "rb") as fh:
            compressed = fh.read()

        saved_pct = 100 - int(len(compressed) / max(len(data), 1) * 100)
        print(f"[COMPRESS] Video {filename}: {len(data)} -> {len(compressed)} bytes ({saved_pct}% smaller)")

        return compressed, new_name

    except Exception as ex:
        print(f"[COMPRESS] Video compression failed, using original: {ex}")
        return data, filename
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def compress_media_bytes(data: bytes, filename: str, is_video: bool = False) -> Tuple[bytes, str]:
    """Single entry point — dispatches to image or video compressor."""
    if is_video:
        return compress_video_bytes(data, filename)
    return compress_image_bytes(data, filename)



