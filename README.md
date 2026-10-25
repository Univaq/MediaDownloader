# MediaDownloader

A private Telegram media downloader bot for Instagram, YouTube, and Kick, built with Python, aiogram 3, yt-dlp, FFmpeg, and SQLite.

> Use this bot only for media you own or are authorized to download. Respect platform terms, copyright, and local law. This project does not bypass DRM, private-account restrictions, or paywalls.

## Features

- Telegram user-ID allowlist
- Format and quality selection before downloading
- Downloads supported by the installed yt-dlp version
- Configurable file-size, duration, and concurrency limits
- SQLite persistence
- Local development and Ubuntu systemd deployment

## Requirements

- Python 3.11+ (3.12 recommended)
- FFmpeg and ffprobe on PATH
- Telegram bot token from @BotFather

## Setup

1. Clone this repository and open it in PyCharm.
2. Create and activate a virtual environment.
3. In the PyCharm terminal, run `Set-ExecutionPolicy -Scope Process Bypass` if needed, then run `./scripts/setup_windows.ps1`.
4. Edit `.env` and configure `BOT_TOKEN` and `ALLOWED_USER_IDS`.
5. Verify FFmpeg with `ffmpeg -version`.
6. Run `./.venv/Scripts/python.exe -m app`.

See [the complete installation guide](docs/INSTALL.md). Separate dependency lists are provided in `requirements.txt` and `requirements-dev.txt`.

Example configuration:

```dotenv
BOT_TOKEN=replace_me
ALLOWED_USER_IDS=123456789
DATABASE_PATH=data/bot.sqlite3
DOWNLOAD_DIR=downloads
MAX_FILE_SIZE_MB=49
MAX_DURATION_SECONDS=10800
MAX_CONCURRENT_DOWNLOADS=2
TELEGRAM_UPLOAD_LIMIT_MB=49
LOG_LEVEL=INFO
```

`ALLOWED_USER_IDS` is a comma-separated list of numeric Telegram user IDs. Never commit `.env` or share your bot token.

## Ubuntu

Run `bash scripts/setup_ubuntu.sh` as a normal sudo-enabled user from the repository. Edit `.env`, then run `.venv/bin/python -m app` to test. For production, review `deploy/media-downloader-bot.service`, create the dedicated `mediadl` user, adjust ownership and paths, and only then enable systemd. See [the complete installation guide](docs/INSTALL.md).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Notes

Some sites change extraction behavior or restrict access. Large files require significant disk, CPU, bandwidth, and upload time. Keep yt-dlp and FFmpeg updated and use this bot only for content you are authorized to download.

## License

MIT. See `LICENSE`.
