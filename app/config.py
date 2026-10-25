from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    allowed_user_ids: frozenset[int]
    database_path: Path = Path("data/bot.sqlite3")
    download_dir: Path = Path("downloads")
    max_file_size_mb: int = 49
    max_duration_seconds: int = 10_800
    max_concurrent_downloads: int = 2
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token or token == "replace_with_botfather_token":
            raise ValueError("Set BOT_TOKEN in your .env file before starting the bot.")

        raw_ids = os.getenv("ALLOWED_USER_IDS", "").strip()
        ids: set[int] = set()
        for item in raw_ids.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                user_id = int(item)
            except ValueError as exc:
                raise ValueError("ALLOWED_USER_IDS must be comma-separated numeric Telegram IDs.") from exc
            if user_id <= 0:
                raise ValueError("Telegram user IDs must be positive integers.")
            ids.add(user_id)
        if not ids:
            raise ValueError("Set at least one Telegram user ID in ALLOWED_USER_IDS.")

        return cls(
            bot_token=token,
            allowed_user_ids=frozenset(ids),
            database_path=Path(os.getenv("DATABASE_PATH", "data/bot.sqlite3")),
            download_dir=Path(os.getenv("DOWNLOAD_DIR", "downloads")),
            max_file_size_mb=_positive_int("MAX_FILE_SIZE_MB", 49),
            max_duration_seconds=_positive_int("MAX_DURATION_SECONDS", 10_800),
            max_concurrent_downloads=_positive_int("MAX_CONCURRENT_DOWNLOADS", 2),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value
