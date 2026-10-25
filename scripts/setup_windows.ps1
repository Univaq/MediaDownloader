$ErrorActionPreference = 'Stop'

Write-Host '== MediaDownloader: Windows setup ==' -ForegroundColor Cyan
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python Launcher not found. Install Python 3.12 from https://www.python.org/downloads/windows/ and enable Add Python to PATH.'
}
py -3.12 --version
if (-not (Test-Path '.venv')) { py -3.12 -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-dev.txt
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning 'FFmpeg is not on PATH. Install it (for example: winget install Gyan.FFmpeg), then reopen the terminal and verify: ffmpeg -version'
} else {
    ffmpeg -version | Select-Object -First 1
}
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env from .env.example. Edit BOT_TOKEN and ALLOWED_USER_IDS before running.' -ForegroundColor Yellow
} else {
    Write-Host '.env already exists; leaving it unchanged.'
}
Write-Host 'Setup finished. Edit .env, then run: .\.venv\Scripts\python.exe -m app' -ForegroundColor Green
