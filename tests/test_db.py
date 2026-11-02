from pathlib import Path

import pytest

from app.db import Database


@pytest.mark.asyncio
async def test_database_tracks_users_and_jobs(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "bot.sqlite3")
    await database.initialize()
    await database.touch_user(12345)
    await database.touch_user(12345)

    job_id = await database.create_job(12345, "https://youtu.be/example", "best")
    await database.finish_job(job_id, "done")

    with database._connect() as connection:
        user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        job = connection.execute(
            "SELECT telegram_id, status, finished_at FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()

    assert user_count == 1
    assert job["telegram_id"] == 12345
    assert job["status"] == "done"
    assert job["finished_at"] is not None


@pytest.mark.asyncio
async def test_database_rejects_invalid_terminal_status(tmp_path: Path) -> None:
    database = Database(tmp_path / "bot.sqlite3")
    await database.initialize()
    with pytest.raises(ValueError, match="Invalid terminal job status"):
        await database.finish_job(1, "running")
