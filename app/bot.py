from __future__ import annotations

import asyncio
import logging
import secrets
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import Settings
from app.db import Database
from app.downloader import DownloadError, MediaFormat, download_media, inspect_formats, validate_url

logger = logging.getLogger(__name__)


def _format_size(size: int | None) -> str:
    if not size:
        return "Unknown size"
    return f"{size / (1024 * 1024):.1f} MB"


def build_router(settings: Settings, db: Database) -> Router:
    router = Router(name="media-downloader")
    semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
    # Telegram callback data is short; keep full URLs and format IDs server-side.
    pending: dict[str, tuple[int, str, list[MediaFormat]]] = {}

    def is_allowed(user_id: int | None) -> bool:
        return user_id is not None and user_id in settings.allowed_user_ids

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not is_allowed(user_id):
            await message.answer("This is a private bot, and your account is not authorized.")
            return
        await db.touch_user(user_id)
        await message.answer(
            "Hello! Send a public Instagram, YouTube, or Kick link.\n"
            "Available formats and quality options will be shown after inspection.\n\n"
            "Only download content you are authorized to access."
        )

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not is_allowed(user_id):
            await message.answer("This is a private bot, and your account is not authorized.")
            return
        await message.answer(
            "Send a public Instagram, YouTube, or Kick link, then choose your preferred quality."
        )

    @router.message(F.text)
    async def receive_link(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not is_allowed(user_id):
            await message.answer("This is a private bot, and your account is not authorized.")
            return
        text = (message.text or "").strip()
        if text.startswith("/"):
            return
        try:
            url = validate_url(text)
        except DownloadError as exc:
            await message.answer(str(exc))
            return

        status = await message.answer("Checking the link and available formats…")
        try:
            async with semaphore:
                info, formats = await asyncio.to_thread(
                    inspect_formats, url, settings.max_duration_seconds
                )
        except DownloadError as exc:
            await status.edit_text(str(exc))
            return
        except Exception:
            logger.exception("Unexpected error while inspecting media")
            await status.edit_text("An unexpected error occurred while inspecting the link.")
            return

        token = secrets.token_urlsafe(6).replace("-", "a").replace("_", "b")[:10]
        pending[token] = (user_id, url, formats)
        rows = []
        for index, fmt in enumerate(formats):
            label = f"{fmt.label} · {_format_size(fmt.filesize)}"
            rows.append([InlineKeyboardButton(text=label[:60], callback_data=f"dl:{token}:{index}")])
        title = str(info.get("title") or "Media")[:150]
        await status.edit_text(
            f"<b>{_escape(title)}</b>\nChoose a format:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )

    @router.callback_query(F.data.startswith("dl:"))
    async def choose_format(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id
        if not is_allowed(user_id):
            await callback.answer("Your account is not authorized.", show_alert=True)
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 3:
            await callback.answer("Invalid request.", show_alert=True)
            return
        token, index_raw = parts[1], parts[2]
        item = pending.get(token)
        if item is None:
            await callback.answer("This selection has expired. Please send the link again.", show_alert=True)
            return
        owner_id, url, formats = item
        if owner_id != user_id:
            await callback.answer("This option belongs to another user.", show_alert=True)
            return
        try:
            format_index = int(index_raw)
            if format_index < 0:
                raise IndexError
            fmt = formats[format_index]
        except (ValueError, IndexError):
            await callback.answer("Invalid format.", show_alert=True)
            return

        await callback.answer("Download started.")
        if callback.message is None:
            return
        await callback.message.edit_text(f"Downloading: {fmt.label} …")
        job_id = await db.create_job(user_id, url, fmt.format_id)
        path: Path | None = None
        try:
            async with semaphore:
                path = await asyncio.to_thread(
                    download_media, url, fmt.format_id, settings.download_dir, settings.max_file_size_mb
                )
            if path.stat().st_size > settings.max_file_size_mb * 1024 * 1024:
                raise DownloadError(f"The file exceeds the {settings.max_file_size_mb} MB size limit.")
            caption = f"{path.name[:900]}\nDownloaded with MediaDownloader"
            if path.suffix.lower() in {".mp4", ".m4v", ".mov", ".webm"}:
                try:
                    await callback.message.answer_video(FSInputFile(path), caption=caption, supports_streaming=True)
                except TelegramBadRequest:
                    await callback.message.answer_document(FSInputFile(path), caption=caption)
            else:
                await callback.message.answer_document(FSInputFile(path), caption=caption)
            await db.finish_job(job_id, "done")
            await callback.message.edit_text("The download completed and the file was sent successfully.")
        except DownloadError as exc:
            await db.finish_job(job_id, "failed")
            await callback.message.edit_text(str(exc))
        except Exception:
            logger.exception("Download/send failed for job %s", job_id)
            await db.finish_job(job_id, "failed")
            await callback.message.edit_text(
                "The download or file delivery failed. Check the file size limit and the source link."
            )
        finally:
            if path is not None:
                path.unlink(missing_ok=True)
            pending.pop(token, None)

    return router


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
