from __future__ import annotations

import logging
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

logger = logging.getLogger(__name__)

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
        raise DownloadError("Please provide a valid HTTP or HTTPS link.")
    host = parsed.hostname.lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise DownloadError("Only Instagram, YouTube, and Kick links are currently supported.")
    if parsed.username or parsed.password:
        raise DownloadError("URLs containing embedded login credentials are not allowed.")
    return candidate


def _ydl_options(
    *,
    cookies_file: Path | None,
    socket_timeout_seconds: int,
    skip_download: bool,
) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": socket_timeout_seconds,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 2,
        "file_access_retries": 2,
        "cachedir": False,
        "skip_download": skip_download,
    }
    if cookies_file is not None:
        if not cookies_file.is_file():
            raise DownloadError("The configured YouTube cookies file does not exist.")
        options["cookiefile"] = str(cookies_file)
    return options


def _extract_info(
    url: str,
    cookies_file: Path | None,
    socket_timeout_seconds: int,
) -> dict:
    try:
        with yt_dlp.YoutubeDL(
            _ydl_options(
                cookies_file=cookies_file,
                socket_timeout_seconds=socket_timeout_seconds,
                skip_download=True,
            )
        ) as ydl:
            info = ydl.extract_info(validate_url(url), download=False)
            if not isinstance(info, dict):
                raise DownloadError("The source did not return usable media information.")
            return info
    except DownloadError:
        raise
    except Exception as exc:
        logger.exception("Media inspection failed for %s", url)
        message = str(exc).lower()
        if "sign in to confirm" in message or "cookies" in message:
            raise DownloadError(
                "The source requires authentication. Configure an authorized cookies file and try again."
            ) from exc
        if "timed out" in message or "timeout" in message:
            raise DownloadError("The source did not respond in time. Please try again.") from exc
        raise DownloadError(
            "Could not retrieve media information. The link may be private, restricted, or unsupported."
        ) from exc


def inspect_formats(
    url: str,
    max_duration_seconds: int,
    cookies_file: Path | None = None,
    socket_timeout_seconds: int = 30,
) -> tuple[dict, list[MediaFormat]]:
    info = _extract_info(url, cookies_file, socket_timeout_seconds)
    duration = info.get("duration")
    if duration is not None and duration > max_duration_seconds:
        raise DownloadError(
            f"Media duration exceeds the configured limit ({max_duration_seconds // 60} minutes)."
        )

    formats: list[MediaFormat] = []
    seen: set[tuple[str, str]] = set()
    for item in info.get("formats") or []:
        format_id = str(item.get("format_id") or "")
        if not format_id:
            continue
        has_video = item.get("vcodec") not in (None, "none")
        has_audio = item.get("acodec") not in (None, "none")
        if not has_video and not has_audio:
            continue

        height = item.get("height")
        height = int(height) if isinstance(height, (int, float)) and height > 0 else None
        ext = str(item.get("ext") or "mp4")
        size = item.get("filesize") or item.get("filesize_approx")
        size = int(size) if isinstance(size, (int, float)) and size > 0 else None

        if has_video:
            label = f"{height or 'Best'}p video" + (" + audio" if not has_audio else "")
            selector = f"{format_id}+bestaudio/best" if not has_audio else format_id
        else:
            label = f"Audio · {ext}"
            selector = format_id

        key = (selector, label)
        if key in seen:
            continue
        seen.add(key)
        formats.append(
            MediaFormat(selector, label, ext, height, size, has_video, has_audio)
        )

    # Some live-stream extractors expose a usable default selector without a normal format list.
    if not formats and (info.get("url") or info.get("formats") == [] or "formats" not in info):
        formats.append(MediaFormat("best", "Best available quality", "mp4", None, None, True, True))

    # Keep the best representative for each video height, plus one audio-only option per extension.
    selected: dict[str, MediaFormat] = {}
    for fmt in sorted(
        formats,
        key=lambda item: (
            item.height or 0,
            item.has_audio,
            item.filesize or 0,
        ),
        reverse=True,
    ):
        key = f"v{fmt.height}" if fmt.has_video else f"a{fmt.ext}"
        selected.setdefault(key, fmt)

    result = list(selected.values())
    result.sort(key=lambda item: (not item.has_video, -(item.height or 0), item.ext))
    if not result:
        logger.warning(
            "No usable formats returned: extractor=%s media_id=%s format_count=%s",
            info.get("extractor_key"),
            info.get("id"),
            len(info.get("formats") or []),
        )
        raise DownloadError(
            "No downloadable formats were returned by the source. The stream may be offline or restricted."
        )
    return info, result[:10]


def download_media(
    url: str,
    format_id: str,
    output_dir: Path,
    max_file_size_mb: int,
    cookies_file: Path | None = None,
    socket_timeout_seconds: int = 30,
) -> Path:
    if cookies_file is not None and not cookies_file.is_file():
        raise DownloadError("The configured YouTube cookies file does not exist.")
    output_dir.mkdir(parents=True, exist_ok=True)
    job_dir = Path(tempfile.mkdtemp(prefix="job-", dir=output_dir))
    safe_format = re.sub(r"[^A-Za-z0-9_+./-]", "", format_id)
    if not safe_format or safe_format != format_id:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise DownloadError("The selected format is invalid.")

    template = str(job_dir / "%(title).80s-%(id)s.%(ext)s")
    options = _ydl_options(
        cookies_file=cookies_file,
        socket_timeout_seconds=socket_timeout_seconds,
        skip_download=False,
    )
    options.update(
        {
            "format": safe_format,
            "outtmpl": template,
            "restrictfilenames": True,
            "max_filesize": max_file_size_mb * 1024 * 1024,
            "merge_output_format": "mp4",
            "overwrites": False,
            "continuedl": True,
        }
    )

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(validate_url(url), download=True)
            if not isinstance(info, dict):
                raise DownloadError("The source did not return a completed download.")

            filename = Path(ydl.prepare_filename(info))
            candidates = [
                filename,
                filename.with_suffix(".mp4"),
                filename.with_suffix(".mkv"),
                filename.with_suffix(".webm"),
                filename.with_suffix(".m4a"),
            ]
            path = next((candidate for candidate in candidates if candidate.is_file()), None)
            if path is None:
                matches = [
                    item for item in job_dir.iterdir()
                    if item.is_file() and not item.name.endswith((".part", ".ytdl"))
                ]
                path = max(matches, key=lambda item: item.stat().st_size) if matches else None
            if path is None:
                raise DownloadError("The download ended, but no output file was created.")

            max_bytes = max_file_size_mb * 1024 * 1024
            if path.stat().st_size > max_bytes:
                raise DownloadError(f"The file exceeds the maximum allowed size of {max_file_size_mb} MB.")
            if path.stat().st_size == 0:
                raise DownloadError("The source returned an empty file. Please try another format.")
            return path

    except DownloadError:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        logger.exception("Media download failed for %s with format %s", url, safe_format)
        message = str(exc).lower()
        if "max-filesize" in message or "file is larger" in message:
            raise DownloadError(f"The file size exceeds the {max_file_size_mb} MB limit.") from exc
        if "requested format is not available" in message or "format is not available" in message:
            raise DownloadError(
                "That quality is no longer available. Send the link again and choose another quality."
            ) from exc
        if "sign in to confirm" in message or "cookies" in message:
            raise DownloadError(
                "The source requires authentication. Configure an authorized cookies file and try again."
            ) from exc
        if "timed out" in message or "timeout" in message:
            raise DownloadError("The download timed out while waiting for the source. Please try again.") from exc
        raise DownloadError("The download failed. Check the link, source availability, and selected quality.") from exc
