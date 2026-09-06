"""HTTP-edge guards. Python `run_pipeline` is unchanged."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_BLOCKED_HOSTS = {
    "metadata.google.internal",
    "metadata.google.com",
    "metadata.goog",
}
_BLOCKED_IPS = {
    ipaddress.ip_address("169.254.169.254"),
}
# Bare words people type in the URL bar. Chromium cannot resolve them.
_HOST_ALIASES = {
    "wiki": "https://en.wikipedia.org",
    "wikipedia": "https://en.wikipedia.org",
    "github": "https://github.com",
    "youtube": "https://www.youtube.com",
    "netflix": "https://www.netflix.com/browse",
    "mdn": "https://developer.mozilla.org",
}
_LOCAL_HOSTS = {"localhost", "localhost.localdomain"}


def job_id_ok(job_id: str) -> bool:
    return bool(_JOB_ID.fullmatch(job_id))


def canonicalize_job_url(url: str) -> str:
    """Turn 'wiki' / 'https://wikipedia/' into a hostname Chromium can resolve."""
    raw = (url or "").strip()
    if not raw:
        return raw
    if "://" not in raw and not raw.startswith("/"):
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if host in _HOST_ALIASES:
        return _HOST_ALIASES[host]
    return raw


def check_job_url(url: str) -> str:
    """http(s) only. Localhost is allowed (playground). Metadata IPs are not."""
    raw = canonicalize_job_url(url)
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must be http or https")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("url host required")
    if host in _BLOCKED_HOSTS or host.endswith(".internal"):
        raise ValueError("url host not allowed")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is None:
        if (
            "." not in host
            and host not in _LOCAL_HOSTS
            and not host.endswith(".localhost")
        ):
            raise ValueError(
                f"{host!r} is not a DNS name; use a full domain like en.wikipedia.org"
            )
        return raw
    if ip in _BLOCKED_IPS or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        raise ValueError("url host not allowed")
    return raw
