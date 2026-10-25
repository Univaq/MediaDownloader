from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com",
    "instagram.com", "www.instagram.com", "m.instagram.com",
    "kick.com", "www.kick.com", "clips.kick.com",
}


class DownloadError(RuntimeError):
    """Expected error shown safely to a bot user."""


@dataclass(frozen=True, slots=True)
class MediaFormat:
    format_id: str
    label: str
    ext: str
    height: int | None
    filesize: int | None
    has_video: bool
    has_audio: bool


def validate_url(url: str) -> str:
    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise DownloadError("لطفاً یک لینک معتبر با http یا https بفرست.")
    host = parsed.hostname.lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise DownloadError("فعلاً فقط لینک‌های Instagram، YouTube و Kick پشتیبانی می‌شوند.")
    if parsed.username or parsed.password:
        raise DownloadError("لینک دارای اطلاعات ورود قابل قبول نیست.")
    return candidate


def _extract_info(url: str) -> dict:
    options = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(validate_url(url), download=False)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError("اطلاعات رسانه دریافت نشد؛ ممکن است لینک خصوصی یا پشتیبانی‌نشده باشد.") from exc


def inspect_formats(url: str, max_duration_seconds: int) -> tuple[dict, list[MediaFormat]]:
    info = _extract_info(url)
    duration = info.get("duration")
    if duration is not None and duration > max_duration_seconds:
        raise DownloadError(f"مدت ویدیو از حد مجاز ({max_duration_seconds // 60} دقیقه) بیشتر است.")
    formats: list[MediaFormat] = []
    for item in info.get("formats", []):
        if not item.get("url"):
            continue
        has_video = item.get("vcodec") not in (None, "none")
        has_audio = item.get("acodec") not in (None, "none")
        if not has_video and not has_audio:
            continue
        height = item.get("height")
        ext = str(item.get("ext") or "mp4")
        format_id = str(item.get("format_id") or "best")
        size = item.get("filesize") or item.get("filesize_approx")
        if has_video and not has_audio:
            label = f"{height or '?'}p video + audio (merge)"
        elif has_video:
            label = f"{height or '?'}p video"
        else:
            label = f"Audio · {ext}"
        formats.append(MediaFormat(format_id, label, ext, height, size, has_video, has_audio))

    # Prefer a compact menu; keep one best progressive format per height and useful audio formats.
    selected: dict[str, MediaFormat] = {}
    for fmt in sorted(formats, key=lambda f: (f.height or 0, f.has_audio, f.filesize or 0), reverse=True):
        key = f"v{fmt.height}" if fmt.has_video else f"a{fmt.ext}"
        selected.setdefault(key, fmt)
    result = list(selected.values())
    result.sort(key=lambda f: (not f.has_video, -(f.height or 0), f.ext))
    if not result:
        raise DownloadError("هیچ فرمت قابل دانلودی برای این لینک پیدا نشد.")
    return info, result[:10]


def download_media(url: str, format_id: str, output_dir: Path, max_file_size_mb: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_format = re.sub(r"[^A-Za-z0-9_+./-]", "", format_id)
    if not safe_format:
        raise DownloadError("فرمت انتخاب‌شده معتبر نیست.")
    template = str(output_dir / "%(title).80s-%(id)s.%(ext)s")
    options = {
        "format": safe_format,
        "outtmpl": template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "max_filesize": max_file_size_mb * 1024 * 1024,
        "merge_output_format": "mp4",
        "overwrites": False,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(validate_url(url), download=True)
            filename = Path(ydl.prepare_filename(info))
            # yt-dlp may merge streams to a different extension.
            candidates = [filename, filename.with_suffix(".mp4"), filename.with_suffix(".mkv"), filename.with_suffix(".webm")]
            path = next((p for p in candidates if p.is_file()), None)
            if path is None:
                matches = list(output_dir.glob(f"*{info.get('id', '')}*"))
                path = next((p for p in matches if p.is_file()), None)
            if path is None:
                raise DownloadError("دانلود تمام شد اما فایل خروجی پیدا نشد.")
            if path.stat().st_size > max_file_size_mb * 1024 * 1024:
                path.unlink(missing_ok=True)
                raise DownloadError(f"فایل از سقف مجاز {max_file_size_mb} مگابایت بزرگ‌تر است.")
            return path
    except DownloadError:
        raise
    except Exception as exc:
        message = str(exc).lower()
        if "max-filesize" in message or "file is larger" in message:
            raise DownloadError(f"حجم فایل از سقف {max_file_size_mb} مگابایت بیشتر است.") from exc
        raise DownloadError("دانلود ناموفق بود. لینک را بررسی کن و دوباره تلاش کن.") from exc
