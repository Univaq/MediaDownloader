import pytest

from app.config import Settings


def test_settings_requires_token_and_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLOWED_USER_IDS", raising=False)
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        Settings.from_env()


def test_settings_parses_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.setenv("BOT_TOKEN", "123:token")
    monkeypatch.setenv("ALLOWED_USER_IDS", "12345, 67890")
    settings = Settings.from_env()
    assert settings.allowed_user_ids == frozenset({12345, 67890})
