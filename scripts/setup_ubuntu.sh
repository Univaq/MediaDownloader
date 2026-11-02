#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

if [[ "${EUID}" -eq 0 ]]; then
  echo 'Run this setup script as a normal user with sudo access, not as root.' >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ffmpeg git
PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$(python3 -c 'import sys; print(sys.version_info >= (3, 11))')" != "True" ]]; then
  echo "Python 3.11 or newer is required; found $PYTHON_VERSION." >&2
  exit 1
fi
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env
  echo 'Created .env. Edit BOT_TOKEN and ALLOWED_USER_IDS before starting.'
fi
chmod 600 .env
mkdir -p data downloads
printf '\nDependencies installed. Next:\n  nano %q/.env\n  %q/.venv/bin/python -m app\n' "$APP_DIR" "$APP_DIR"
