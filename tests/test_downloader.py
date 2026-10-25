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
