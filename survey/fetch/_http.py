"""Shared HTTP primitives for fetch backends.

Replaces the per-backend ``_http_get`` / ``_http_head_size`` /
``_stream_to_disk`` duplicates. Adds two new safety properties the old
copies didn't have:

- A ``SafeHTTPRedirectHandler`` that rejects redirects to non-``http(s)``
  schemes, redirects to URLs with userinfo, and redirects whose target
  fails the SSRF screen (``_filters.is_safe_http_url``). The default
  handler in stdlib follows ``file:`` / ``ftp:`` redirects, which we do
  not want to expose to hostile catalogs.
- ``stream_to_file`` enforces a per-file byte cap *during* the read, so a
  hostile server can't feed us a 32 GB body that we then discard. The
  partial output file is unlinked on any failure path.

All getters share a single canonical exception set so callers can write
one ``except`` clause::

    HTTP_ERRORS = (URLError, HTTPError, HTTPException, ValueError,
                   TimeoutError, OSError)
"""

from __future__ import annotations

import hashlib
import http.client
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import BinaryIO

from . import _filters

_DEFAULT_USER_AGENT = (
    "pollock-survey/0.1 (+https://github.com/HPI-Information-Systems/Pollock)"
)
USER_AGENT = os.environ.get("POLLOCK_SURVEY_USER_AGENT") or _DEFAULT_USER_AGENT

_DEFAULT_TIMEOUT = 60
_DEFAULT_HEAD_TIMEOUT = 15
_DEFAULT_CHUNK_BYTES = 64 * 1024

HTTP_ERRORS: tuple[type[BaseException], ...] = (
    urllib.error.URLError,
    urllib.error.HTTPError,
    http.client.HTTPException,
    ValueError,
    TimeoutError,
    OSError,
)


class UnsafeRedirectError(urllib.error.HTTPError):
    """Raised by ``SafeHTTPRedirectHandler`` when a redirect target is rejected."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(url, 502, f"unsafe redirect: {reason}", {}, None)
        self.reason = reason


class SafeHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that try to escape http(s) or hit private hosts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _filters.is_safe_http_url(newurl):
            raise UnsafeRedirectError(newurl, "fails SSRF screen")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(SafeHTTPRedirectHandler())


def build_opener() -> urllib.request.OpenerDirector:
    """Return a fresh opener with the safe redirect handler installed."""
    return urllib.request.build_opener(SafeHTTPRedirectHandler())


def _request(url: str, *, method: str | None = None) -> urllib.request.Request:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if method:
        return urllib.request.Request(url, headers=headers, method=method)
    return urllib.request.Request(url, headers=headers)


def get_bytes(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> tuple[bytes, str]:
    """Fetch a URL fully into memory. Returns ``(body, lower-cased-content-type)``."""
    if not _filters.is_safe_http_url(url):
        raise ValueError(f"unsafe URL: {url!r}")
    with _OPENER.open(_request(url), timeout=timeout) as resp:
        return resp.read(), (resp.headers.get("Content-Type") or "").lower()


def get_text(
    url: str, *, timeout: int = _DEFAULT_TIMEOUT, encoding: str = "utf-8"
) -> str:
    """Fetch a URL and decode as text. Use this for HTML/JSON pages, not CSVs."""
    body, _ = get_bytes(url, timeout=timeout)
    return body.decode(encoding)


def head_size(url: str, *, timeout: int = _DEFAULT_HEAD_TIMEOUT) -> int | None:
    """HEAD the URL and return Content-Length, or ``None`` if unavailable.

    Soft-fails (returns ``None``) on any HTTP/network error. Callers should
    treat ``None`` as "unknown size" and decide whether to GET anyway.
    """
    if not _filters.is_safe_http_url(url):
        return None
    try:
        with _OPENER.open(_request(url, method="HEAD"), timeout=timeout) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl is not None else None
    except HTTP_ERRORS:
        return None


def stream_to_file(
    url: str,
    output: Path | BinaryIO,
    *,
    max_bytes: int,
    timeout: int = _DEFAULT_TIMEOUT,
    chunk: int = _DEFAULT_CHUNK_BYTES,
) -> tuple[int, str]:
    """Stream ``url`` to ``output``, hashing on the fly.

    ``output`` may be a ``Path`` (we open + manage it) or an already-open
    binary file handle (we write but don't close — useful for the O_EXCL
    handles returned by ``storage.stage_path``).

    Aborts with ``ValueError`` and unlinks the partial output if the running
    total would exceed ``max_bytes``. Aborts and unlinks on any HTTP error.
    Returns ``(bytes_written, sha256_hexdigest)`` on success.
    """
    if not _filters.is_safe_http_url(url):
        raise ValueError(f"unsafe URL: {url!r}")

    own_file = isinstance(output, Path)
    path: Path | None = output if own_file else None
    if own_file:
        assert path is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        f: BinaryIO = open(path, "wb")
    else:
        f = output  # type: ignore[assignment]

    h = hashlib.sha256()
    total = 0
    try:
        with _OPENER.open(_request(url), timeout=timeout) as resp:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                total += len(buf)
                if total > max_bytes:
                    raise ValueError(
                        f"body exceeded max_bytes={max_bytes:,} at {total:,}"
                    )
                f.write(buf)
                h.update(buf)
    except BaseException:
        if own_file:
            f.close()
            if path is not None and path.exists():
                path.unlink()
        else:
            try:
                f.flush()
            except Exception:
                pass
        raise
    else:
        if own_file:
            f.close()
    return total, h.hexdigest()
