"""Unit tests for the SSRF-safe URL validator."""
import pytest
from app.core.exceptions import SSRFException
from app.services.url_validator import validate_url


# ─── Valid allowed URLs ────────────────────────────────────────────────────────

@pytest.mark.parametrize("url, expected_provider", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube.com"),
    ("https://youtu.be/dQw4w9WgXcQ", "youtu.be"),
    ("https://vimeo.com/12345678", "vimeo.com"),
    ("https://youtube.com/watch?v=abc123", "youtube.com"),
])
def test_valid_allowed_urls(url: str, expected_provider: str):
    provider = validate_url(url)
    assert provider == expected_provider


# ─── Rejected: disallowed domains ─────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://evil.com/malware.mp4",
    "https://notallowed.io/video",
    "https://youtube.attacker.com/watch?v=xyz",   # subdomain trick
    "https://totallynotyoutube.com/",
])
def test_disallowed_domains_rejected(url: str):
    with pytest.raises(SSRFException):
        validate_url(url)


# ─── Rejected: invalid schemes ────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "ftp://youtube.com/video",
    "file:///etc/passwd",
    "javascript:alert(1)",
])
def test_invalid_schemes_rejected(url: str):
    with pytest.raises(SSRFException):
        validate_url(url)


# ─── Rejected: malformed URLs ─────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "",
    "not a url at all",
    "   ",
    "http://",
])
def test_malformed_urls_rejected(url: str):
    with pytest.raises(SSRFException):
        validate_url(url)


# ─── Format / resolution allowlist ────────────────────────────────────────────

from app.services.format_service import assert_format_allowed
from app.core.exceptions import BadRequestException


@pytest.mark.parametrize("format, resolution", [
    ("mp4", "720p"),
    ("mp4", "1080p"),
    ("mp4", "480p"),
    ("mp4", "360p"),
    ("webm", "720p"),
    ("mp3", "audio_only"),
])
def test_valid_format_resolution_combos(format: str, resolution: str):
    assert_format_allowed(format, resolution)   # must not raise


@pytest.mark.parametrize("format, resolution", [
    ("mp4", "audio_only"),       # audio_only is only for mp3
    ("mp3", "720p"),             # mp3 must be audio_only
    ("avi", "720p"),             # avi not in allowlist
    ("mp4", "4k"),               # 4k not in allowlist
    ("flac", "audio_only"),      # flac not in allowlist
])
def test_invalid_format_resolution_combos_rejected(format: str, resolution: str):
    with pytest.raises(BadRequestException):
        assert_format_allowed(format, resolution)
