from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    source_url TEXT NOT NULL,
                    format_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    finished_at TEXT
                )"""
            )

    async def touch_user(self, telegram_id: int) -> None:
        with self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO users(telegram_id) VALUES (?)", (telegram_id,))

    async def create_job(self, telegram_id: int, url: str, format_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO jobs(telegram_id, source_url, format_id, status) VALUES (?, ?, ?, 'queued')",
                (telegram_id, url, format_id),
            )
            return int(cursor.lastrowid)

    async def finish_job(self, job_id: int, status: str) -> None:
        if status not in {"done", "failed"}:
            raise ValueError("Invalid terminal job status")
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, job_id),
            )
