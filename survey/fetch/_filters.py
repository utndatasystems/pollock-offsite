"""Shared content / URL filters used by every fetch backend.

The canonical version of ``looks_like_csv`` was the zip-aware copy in
``data_europa_eu.py`` — every other backend silently lacked the zip
rejection and would happily feed a ``application/zip`` body into the
manifest. Centralising it here closes that drift.

``is_safe_http_url`` is a real SSRF screen, not just a scheme check:

- Only ``http``/``https`` schemes are accepted.
- A non-empty netloc is required, with no whitespace or control chars.
- Userinfo (``user:pass@``) is rejected — catalogs never need it and the
  pattern is a common phishing / SSRF foot-gun.
- IP literals in private / loopback / link-local / multicast / reserved
  ranges are rejected.
- Common local-network hostnames (``localhost``, ``*.local``, ``*.internal``)
  are rejected by name.

Hostname → IP resolution is intentionally *not* performed here. Doing it
would slow every URL check by a DNS round-trip and introduce a TOCTOU
between the screen and the actual ``urlopen``. The redirect handler in
``_http.SafeHTTPRedirectHandler`` re-applies this screen on every hop,
which closes the simple open-redirect attack surface; DNS-rebinding
remains out of scope and should be handled at the network layer.
"""

from __future__ import annotations

import ipaddress
import urllib.parse

CSV_SUFFIXES: tuple[str, ...] = (
    ".csv",
    ".tsv",
    ".csv.gz",
    ".csv.gzip",
    ".csv.zst",
    ".csv.zstd",
    ".tsv.gz",
    ".tsv.gzip",
    ".tsv.zst",
    ".tsv.zstd",
)

_LOCAL_HOSTNAMES = frozenset({"localhost", "ip6-localhost", "ip6-loopback"})
_LOCAL_SUFFIXES = (".localhost", ".local", ".internal", ".intranet", ".lan")


def looks_like_csv(body: bytes, content_type: str) -> bool:
    """Best-effort filter to drop HTML / JSON / XML / zip responses.

    Many catalog-listed CSV URLs redirect to a "page moved" HTML stub or
    return a JSON metadata wrapper or a ZIP archive. None of those should
    enter the manifest as CSV. False positives are possible (a CSV that
    happens to start with ``{``) but rare enough to ignore.
    """
    ct = content_type.lower() if content_type else ""
    if "text/html" in ct or "application/json" in ct:
        return False
    if "application/xml" in ct or "text/xml" in ct:
        return False
    if "application/zip" in ct or "application/x-zip" in ct:
        return False
    head = body[:1024].lstrip()
    if head.startswith((b"<!DOCTYPE", b"<html", b"<HTML", b"<?xml", b"<!--")):
        return False
    if head.startswith(b"{") and b'"' in head[:200]:
        return False
    if head.startswith(b"PK\x03\x04"):  # zip magic
        return False
    return True


def _host_is_safe(host: str) -> bool:
    """Return True iff ``host`` is neither a private IP literal nor a local name."""
    h = host.strip().rstrip(".").lower()
    if not h:
        return False
    # IPv6 zone IDs (``fe80::1%eth0``) are scoped link-local; reject them
    # even if the address text alone wouldn't parse as is_link_local.
    if "%" in h:
        return False
    if h in _LOCAL_HOSTNAMES:
        return False
    if any(h.endswith(suf) for suf in _LOCAL_SUFFIXES):
        return False
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return True
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def is_safe_http_url(url: str) -> bool:
    """Reject URLs that aren't safe to send to ``urllib.request.urlopen``.

    Used both at candidate-extraction time (catch malformed catalog
    entries) and inside the redirect handler (catch hostile redirects).
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    if any(c.isspace() or ord(c) < 0x20 for c in parsed.netloc):
        return False
    if parsed.username is not None or parsed.password is not None:
        return False
    host = parsed.hostname or ""
    if not host:
        return False
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return _host_is_safe(host)
