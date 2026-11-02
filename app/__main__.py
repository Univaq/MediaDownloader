import asyncio
import logging
import shutil

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot import build_router
from app.config import Settings
from app.db import Database


async def main() -> None:
    settings = Settings.from_env()
    missing_tools = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing_tools:
        raise RuntimeError(
            "Missing required system tools: " + ", ".join(missing_tools)
            + ". Install FFmpeg and ensure both commands are available on PATH."
        )
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db = Database(settings.database_path)
    await db.initialize()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(settings, db))
    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
