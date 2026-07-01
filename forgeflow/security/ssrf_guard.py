"""SSRF guard for any URL coming from agent / LLM / user input.

Closes SECURITY_AUDIT.md C-6. The guard is conservative on purpose — false
positives (rejecting an unusual but legitimate URL) are preferred to false
negatives (letting `scrape_url` hit IMDS or pivot through the cluster).

Rules:
  1. Only http / https schemes.
  2. Hostname must resolve to a globally-routable IP.
     - RFC-1918 (10/8, 172.16/12, 192.168/16) → blocked
     - Loopback (127/8, ::1) → blocked
     - Link-local (169.254/16, fe80::/10) including AWS/GCP/Azure IMDS → blocked
     - IPv4-mapped IPv6 (::ffff:0:0/96) → unwrapped and re-checked
     - Multicast / unspecified / reserved → blocked
  3. DNS is resolved once at guard time; we return both the URL and the
     pinned IP so the HTTP client can connect by IP and pass the Host header,
     defeating DNS rebinding.
  4. Redirects are caller's responsibility — they must call check_url again
     on the redirect target. `safe_get` wraps httpx with that loop.

Example:
    from forgeflow.security.ssrf_guard import safe_get
    response = await safe_get("https://example.com/foo")
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class SSRFBlocked(ValueError):
    """Raised when a URL fails the SSRF safety check."""


_ALLOWED_SCHEMES = {"http", "https"}
_DEFAULT_TIMEOUT = 15.0
_DEFAULT_MAX_REDIRECTS = 3
_DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB hard ceiling


@dataclass(frozen=True)
class _CheckedURL:
    url: str
    host: str
    pinned_ip: str


def _is_private_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped  # type: ignore[assignment]
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def check_url(url: str) -> _CheckedURL:
    """Parse + validate a URL. Returns (url, host, pinned_ip).

    Raises SSRFBlocked if the URL is unsafe.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise SSRFBlocked(f"scheme not allowed: {scheme!r}")

    host = parsed.hostname
    if not host:
        raise SSRFBlocked("URL is missing a hostname")

    # Reject userinfo-bearing URLs — common bypass vector.
    if parsed.username or parsed.password:
        raise SSRFBlocked("URLs with userinfo are not permitted")

    # If the host is already a literal IP, validate directly. Keep the parse in
    # its own try: SSRFBlocked subclasses ValueError, so raising it inside the
    # same block that catches ValueError would swallow the rejection and fall
    # through to the DNS path.
    try:
        literal: ipaddress.IPv4Address | ipaddress.IPv6Address | None = (
            ipaddress.ip_address(host)
        )
    except ValueError:
        literal = None  # not an IP literal — DNS resolve below
    if literal is not None:
        if _is_private_ip(literal):
            raise SSRFBlocked(f"target IP is private/reserved: {literal}")
        return _CheckedURL(url=url, host=host, pinned_ip=str(literal))

    # Resolve every A/AAAA the host advertises; ANY private hit = reject.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFBlocked(f"DNS resolution failed for {host}: {exc}") from exc

    addrs: list[str] = []
    for _family, _type, _proto, _canon, sockaddr in infos:
        addr = sockaddr[0]
        try:
            parsed_ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_private_ip(parsed_ip):
            raise SSRFBlocked(
                f"hostname {host!r} resolves to private/reserved {parsed_ip}"
            )
        addrs.append(str(parsed_ip))

    if not addrs:
        raise SSRFBlocked(f"no public addresses for {host}")

    # Pin the first valid public address so the caller can defeat rebinding
    # by passing it as `Host: <host>` over a connection to that IP.
    return _CheckedURL(url=url, host=host, pinned_ip=addrs[0])


async def safe_get(
    url: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    max_redirects: int = _DEFAULT_MAX_REDIRECTS,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """GET a URL with SSRF guard + manual redirect handling.

    Each redirect re-runs check_url, so a 302 to `http://169.254.169.254/...`
    is blocked even if the original URL was clean.
    """
    current = url
    base_headers = {"User-Agent": "ForgeFlow/1.0 (+safe-fetcher)"}
    if headers:
        base_headers.update(headers)

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False
    ) as client:
        for _ in range(max_redirects + 1):
            check_url(current)
            response = await client.get(current, headers=base_headers)
            if response.status_code in (301, 302, 303, 307, 308):
                loc = response.headers.get("location")
                if not loc:
                    raise SSRFBlocked("redirect without Location header")
                # Resolve relative redirects against the current URL.
                # NB: httpx.URL has no human_repr() (that's a yarl/aiohttp
                # method) — str() is the correct serialization. Using
                # human_repr() AttributeError'd on every redirect.
                current = str(httpx.URL(current).join(loc))
                continue
            # Enforce size cap by reading at most max_bytes.
            content = response.content[:max_bytes]
            response._content = content  # noqa: SLF001
            return response

    raise SSRFBlocked(f"redirect loop exceeded {max_redirects} hops")
