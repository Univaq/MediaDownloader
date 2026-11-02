import pytest

from app.downloader import DownloadError, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "https://www.instagram.com/reel/abc123/",
        "https://kick.com/somechannel",
    ],
)
def test_validate_supported_urls(url: str) -> None:
    assert validate_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://example.com/video",
        "https://youtube.com.evil.example/watch?v=x",
        "https://user:pass@youtube.com/watch?v=x",
        "not a url",
    ],
)
def test_reject_unsupported_urls(url: str) -> None:
    with pytest.raises(DownloadError):
        validate_url(url)


def test_download_failure_cleans_temporary_directory(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    class FailingYoutubeDL:
        def __init__(self, options: dict) -> None:
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def extract_info(self, url: str, download: bool = False):
            raise RuntimeError("simulated extraction failure")

    monkeypatch.setattr("app.downloader.yt_dlp.YoutubeDL", FailingYoutubeDL)

    from app.downloader import download_media

    with pytest.raises(DownloadError):
        download_media("https://youtu.be/example", "best", tmp_path, 45)

    assert list(tmp_path.iterdir()) == []
