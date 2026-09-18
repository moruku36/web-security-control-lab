"""Target URL safety validator for Web Security Control Lab Scanner."""

import ipaddress
from urllib.parse import urlparse

PERMITTED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "[::1]",
    "web-security-control-lab-app",
}

REFUSAL_MESSAGE = (
    "Refusing target. Web Security Control Lab only scans explicitly permitted local lab targets."
)


def is_safe_target(target_url: str) -> bool:
    """
    Validate that target URL is strictly constrained to local lab targets.
    Fail-Closed: Any unrecognized host, external IP, or remote hostname returns False.
    """
    if not target_url or not isinstance(target_url, str):
        return False

    try:
        parsed = urlparse(target_url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        hostname = hostname.lower().strip("[]")

        # Explicitly allowed hostname list
        if hostname in ("localhost", "web-security-control-lab-app"):
            return True

        # Check IP address
        try:
            ip = ipaddress.ip_address(hostname)
            # Only loopback is permitted
            return ip.is_loopback
        except ValueError:
            # Not an IP and not in local hostnames
            return False

    except Exception:
        return False


def validate_target_url(target_url: str) -> str:
    """
    Validate target URL and raise ValueError if target is not permitted.
    Returns normalized target URL if valid.
    """
    if not is_safe_target(target_url):
        raise ValueError(REFUSAL_MESSAGE)
    return target_url.rstrip("/")
