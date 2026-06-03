"""Tests for ``_download.fetch_one``: happy path, oversize abort, redirect rejection."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

from survey.fetch import _http
from survey.fetch._download import Candidate, Failure, Success, fetch_one
from survey.fetch.config import FetchOptions
from survey.fetch.storage import stage_path


def _opts(tmp_path: Path, *, per_file_cap: int = 200 * 1024 * 1024) -> FetchOptions:
    return FetchOptions(
        out_dir=tmp_path / "out",
        data_root=tmp_path / "raw",
        max_files=None,
        max_bytes=10**12,
        dry_run=False,
        concurrency=1,
        per_file_cap_bytes=per_file_cap,
        head_timeout_s=5,
        request_timeout_s=10,
    )


def _staging(tmp_path: Path):
    """Return an ``exclusive_stage`` callable bound to ``tmp_path / 'raw'``."""
    def stage(origin: str, url: str):
        return stage_path(origin, url, tmp_path / "raw")
    return stage


class _FakeResponse:
    """Minimal stand-in for the object returned by ``OpenerDirector.open``."""

    def __init__(self, body: bytes, headers: dict[str, str] | None = None):
        self._buf = io.BytesIO(body)
        self.headers = headers or {}

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            return self._buf.read()
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_one_happy_path(monkeypatch, tmp_path: Path) -> None:
    body = b"a,b,c\n1,2,3\n4,5,6\n"
    opener = MagicMock()
    opener.open.return_value = _FakeResponse(body, {"Content-Length": str(len(body))})
    monkeypatch.setattr(_http, "_OPENER", opener)

    cand = Candidate(
        url="https://example.com/data/file.csv",
        origin="data.gov",
        picked_reason="test",
        size_hint=len(body),
    )
    result = fetch_one(cand, opts=_opts(tmp_path), exclusive_stage=_staging(tmp_path))

    assert isinstance(result, Success), result
    assert result.bytes == len(body)
    assert result.body_path.exists()
    assert result.body_path.read_bytes() == body
    assert len(result.sha) == 64


def test_fetch_one_oversize_during_stream_aborts(monkeypatch, tmp_path: Path) -> None:
    """Body bigger than per_file_cap_bytes -> Failure + staged file unlinked."""
    body = b"x" * (5 * 1024 * 1024)  # 5 MiB
    opener = MagicMock()
    opener.open.return_value = _FakeResponse(body)
    monkeypatch.setattr(_http, "_OPENER", opener)
    # Force the GET path: HEAD reports unknown size, candidate carries no hint.
    monkeypatch.setattr(_http, "head_size", lambda *a, **k: None)

    opts = _opts(tmp_path, per_file_cap=1024)  # 1 KiB
    cand = Candidate(
        url="https://example.com/big.csv",
        origin="data.gov",
        picked_reason="test",
        size_hint=None,
    )
    result = fetch_one(cand, opts=opts, exclusive_stage=_staging(tmp_path))

    assert isinstance(result, Failure)
    # The ``ValueError`` raised by stream_to_file is caught as an HTTP error.
    assert "http_error" in result.reason or "ValueError" in result.reason
    # Staged file must be cleaned up.
    raw_dir = tmp_path / "raw" / "data.gov" / "csv"
    if raw_dir.exists():
        leftovers = list(raw_dir.iterdir())
        assert leftovers == [], f"unexpected leftover files: {leftovers}"


def test_fetch_one_too_large_via_head(monkeypatch, tmp_path: Path) -> None:
    """HEAD reports a size > per_file_cap_bytes -> Failure('too_large') without GET."""
    monkeypatch.setattr(_http, "head_size", lambda *a, **k: 999_999_999)
    opener = MagicMock()
    opener.open.side_effect = AssertionError("GET must not run")
    monkeypatch.setattr(_http, "_OPENER", opener)

    opts = _opts(tmp_path, per_file_cap=1024)
    cand = Candidate(
        url="https://example.com/x.csv",
        origin="data.gov",
        picked_reason="test",
        size_hint=None,
    )
    result = fetch_one(cand, opts=opts, exclusive_stage=_staging(tmp_path))
    assert isinstance(result, Failure)
    assert result.reason == "too_large"


def test_fetch_one_redirect_to_file_scheme_is_failure(monkeypatch, tmp_path: Path) -> None:
    """A safe-redirect rejection from the opener must surface as ``Failure``.

    We can't construct ``UnsafeRedirectError`` directly (HTTPError.reason is a
    read-only property in stdlib) so we raise the parent ``HTTPError`` shape
    that ``_OPENER.open`` would actually raise, which is the same code path
    ``fetch_one`` exercises.
    """
    import urllib.error
    opener = MagicMock()
    opener.open.side_effect = urllib.error.HTTPError(
        "file:///etc/passwd", 502, "unsafe redirect: non-http", {}, None
    )
    monkeypatch.setattr(_http, "_OPENER", opener)

    cand = Candidate(
        url="https://example.com/redirector.csv",
        origin="data.gov",
        picked_reason="test",
        size_hint=10,  # skip HEAD
    )
    result = fetch_one(cand, opts=_opts(tmp_path), exclusive_stage=_staging(tmp_path))
    assert isinstance(result, Failure)
    assert "http_error" in result.reason or "HTTPError" in result.reason


def test_fetch_one_non_csv_body_is_failure(monkeypatch, tmp_path: Path) -> None:
    """HTML body fetched at a .csv URL must produce ``Failure('not_csv')``."""
    body = b"<!DOCTYPE html><html>nope</html>"
    opener = MagicMock()
    opener.open.return_value = _FakeResponse(body)
    monkeypatch.setattr(_http, "_OPENER", opener)

    cand = Candidate(
        url="https://example.com/redirected.csv",
        origin="data.gov",
        picked_reason="test",
        size_hint=len(body),
    )
    result = fetch_one(cand, opts=_opts(tmp_path), exclusive_stage=_staging(tmp_path))
    assert isinstance(result, Failure)
    assert result.reason == "not_csv"
    raw_dir = tmp_path / "raw" / "data.gov" / "csv"
    if raw_dir.exists():
        assert list(raw_dir.iterdir()) == []
