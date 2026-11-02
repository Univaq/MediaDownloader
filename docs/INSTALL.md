# Installation and prerequisites

## Required on every platform

- Python 3.12 recommended (Python 3.11+ supported)
- FFmpeg including `ffprobe`, available on `PATH`
- A Telegram bot token created with [@BotFather](https://t.me/BotFather)
- Your numeric Telegram user ID for the allowlist
- Network access to Telegram and the media source

## Windows / PyCharm

1. Install Python 3.12 and ensure the Python Launcher (`py`) is available.
2. Install FFmpeg. One option in PowerShell is `winget install Gyan.FFmpeg`; restart the terminal after installation.
3. Clone the repository and open the folder in PyCharm.
4. In the PyCharm terminal, run `Set-ExecutionPolicy -Scope Process Bypass` if activation scripts are blocked, then run `./scripts/setup_windows.ps1`.
5. Edit `.env`: set `BOT_TOKEN` and replace `ALLOWED_USER_IDS` with your numeric Telegram user ID(s), comma-separated.
6. Start the bot with `./.venv/Scripts/python.exe -m app`.
7. In Telegram, open your bot and send `/start` from an allowlisted account.

Manual installation alternative:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
ffmpeg -version
```

## Ubuntu / VPS

Run as a regular sudo-enabled user from the cloned repository:

```bash
bash scripts/setup_ubuntu.sh
nano .env
.venv/bin/python -m app
```

For production, use a dedicated unprivileged service account and systemd:

```bash
sudo useradd --system --no-create-home --home-dir /opt/media-downloader-bot --shell /usr/sbin/nologin mediadl
sudo install -d -o mediadl -g mediadl /opt/media-downloader-bot
sudo -u mediadl git clone https://github.com/Univaq/MediaDownloader.git /opt/media-downloader-bot
sudo -u mediadl python3 -m venv /opt/media-downloader-bot/.venv
sudo -u mediadl /opt/media-downloader-bot/.venv/bin/python -m pip install --upgrade pip
sudo -u mediadl /opt/media-downloader-bot/.venv/bin/python -m pip install -r /opt/media-downloader-bot/requirements.txt
sudo -u mediadl mkdir -p /opt/media-downloader-bot/data /opt/media-downloader-bot/downloads
sudo -u mediadl cp /opt/media-downloader-bot/.env.example /opt/media-downloader-bot/.env
sudoedit /opt/media-downloader-bot/.env
sudo chown mediadl:mediadl /opt/media-downloader-bot/.env
sudo chmod 600 /opt/media-downloader-bot/.env
sudo install -m 644 /opt/media-downloader-bot/deploy/media-downloader-bot.service /etc/systemd/system/media-downloader-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now media-downloader-bot
sudo systemctl status media-downloader-bot
sudo journalctl -u media-downloader-bot -f
```

Set `BOT_TOKEN` and `ALLOWED_USER_IDS` in `.env` before starting the service. The service unit assumes the installation path and account shown above. Do not run the bot as root.

## Configuration

- `BOT_TOKEN`: secret token from BotFather; never commit it or send it in chat.
- `ALLOWED_USER_IDS`: comma-separated numeric Telegram user IDs allowed to use the bot.
- `DATABASE_PATH`: SQLite database file path.
- `DOWNLOAD_DIR`: temporary download directory.
- `MAX_FILE_SIZE_MB`: maximum downloaded file size in MiB. The default is 45 MiB to stay below Telegram's upload limit.
- `MAX_DURATION_SECONDS`: maximum source duration.
- `MAX_CONCURRENT_DOWNLOADS`: maximum concurrent inspection/download operations.
- `LOG_LEVEL`: Python logging level, e.g. `INFO` or `DEBUG`.

## Verify the installation

```bash
ffmpeg -version
python -m pip check
python -m pytest
python -m ruff check .
```

Only download content you own or are authorized to download. Some sites may restrict access or change their extraction behavior. Never add cookies or account credentials to this repository.
