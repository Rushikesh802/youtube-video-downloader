"""
SSRF-safe URL validation service.

Enforces a strict allowlist of permitted provider domains and rejects URLs
that resolve to loopback, private, link-local, or cloud metadata address
ranges — protecting against Server-Side Request Forgery attacks.
"""
import ipaddress
import re
import socket
from urllib.parse import urlparse

from app.core.exceptions import SSRFException
from app.core.logging import logger

# ─── Provider allowlist ───────────────────────────────────────────────────────
# Only URLs whose netloc matches one of these domains are accepted.
# Subdomains are also permitted (e.g., www.youtube.com).
ALLOWED_PROVIDER_DOMAINS: set[str] = {
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "dailymotion.com",
    "twitch.tv",
}

# ─── Forbidden IP networks (RFC 1918, loopback, link-local, metadata) ─────────
_FORBIDDEN_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    # Loopback
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    # Private (RFC 1918)
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # Link-local
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
    # AWS/GCP/Azure IMDS endpoints
    ipaddress.ip_network("169.254.169.254/32"),
    # Unique local addresses
    ipaddress.ip_network("fc00::/7"),
    # Unspecified
    ipaddress.ip_network("0.0.0.0/8"),
]

_URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)"
    r"+[a-zA-Z]{2,63}"
    r"(?::\d{1,5})?"
    r"(?:/[^\s]*)?$"
)


def _is_forbidden_ip(host: str) -> bool:
    """Return True if the resolved host falls within any forbidden network range."""
    try:
        addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        return True  # Cannot resolve → deny

    for family, _, _, _, sockaddr in addr_info:
        raw_ip = sockaddr[0]
        try:
            addr = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        for forbidden in _FORBIDDEN_NETWORKS:
            if addr in forbidden:
                return True
    return False


def _extract_provider(netloc: str) -> str | None:
    """
    Return the matching allowed provider domain for a given netloc, or None.

    e.g. 'www.youtube.com' → 'youtube.com'
         'youtu.be' → 'youtu.be'
    """
    netloc_lower = netloc.lower().split(":")[0]  # strip optional port
    for domain in ALLOWED_PROVIDER_DOMAINS:
        if netloc_lower == domain or netloc_lower.endswith("." + domain):
            return domain
    return None


def validate_url(url: str) -> str:
    """
    Validate a user-supplied URL for safe processing.

    Steps:
    1. Basic syntax check.
    2. HTTPS scheme enforcement.
    3. Allowlist provider domain check.
    4. SSRF guard — DNS resolution against forbidden IP ranges.

    Returns:
        The matched provider domain string (e.g., 'youtube.com').

    Raises:
        SSRFException: If any validation step fails.
    """
    url = url.strip()

    # 1. Structural syntax check
    if not _URL_PATTERN.match(url):
        raise SSRFException("Malformed or unsupported URL format.")

    parsed = urlparse(url)

    # 2. Scheme enforcement
    if parsed.scheme not in ("http", "https"):
        raise SSRFException("Only HTTP and HTTPS URLs are accepted.")

    netloc = parsed.netloc or ""
    if not netloc:
        raise SSRFException("URL is missing a valid host.")

    # 3. Provider allowlist check
    provider = _extract_provider(netloc)
    if provider is None:
        raise SSRFException(
            f"The domain '{netloc}' is not in the list of authorized media providers."
        )

    # 4. SSRF guard — resolve host and check IP ranges
    hostname = parsed.hostname or ""
    if not hostname:
        raise SSRFException("Could not extract hostname from URL.")

    # Reject raw IP literals in the URL itself (both IPv4 and IPv6)
    try:
        ip_literal = ipaddress.ip_address(hostname)
        for forbidden in _FORBIDDEN_NETWORKS:
            if ip_literal in forbidden:
                raise SSRFException("URL host resolves to a restricted IP address range.")
    except ValueError:
        pass  # Not a raw IP literal — proceed to DNS resolution

    if _is_forbidden_ip(hostname):
        raise SSRFException(
            "URL host resolves to a private, loopback, or restricted IP address range."
        )

    logger.debug("URL validated successfully: provider=%s url=%s", provider, url)
    return provider
