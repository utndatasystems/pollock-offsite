"""Shared fixtures for ``survey.fetch`` tests.

Keeps the test modules free of plumbing: temp out-dirs, a fake opener that
replaces ``_http._OPENER`` so no test ever touches the network, and a tiny
helper for shaping the ``urlopen`` response object the stdlib expects.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def tmp_out_dir(tmp_path: Path) -> Path:
    """A clean out-dir with manifest/state paths preconfigured.

    The directory exists; ``manifest.csv`` and ``.pollock_survey_state.json``
    are *not* pre-created so tests can assert their initial absence.
    """
    out = tmp_path / "out"
    out.mkdir()
    return out


class _FakeResponse:
    """Minimal stand-in for the object returned by ``OpenerDirector.open``.

    Behaves enough like ``http.client.HTTPResponse`` for ``_http.get_bytes`` /
    ``_http.head_size`` / ``_http.stream_to_file`` to do their thing.
    """

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
        self._buf.close()
        return False


@pytest.fixture
def mock_opener(monkeypatch):
    """Patch ``_http._OPENER`` with a programmable mock.

    Returns a tuple ``(opener_mock, set_response)``. ``set_response(body, headers=...)``
    installs the next response; ``set_response(exc=...)`` raises instead. Callers
    can also set ``opener_mock.open.side_effect`` directly for per-call routing.
    """
    from survey.fetch import _http

    opener = MagicMock()
    monkeypatch.setattr(_http, "_OPENER", opener)

    def set_response(body: bytes = b"", headers: dict[str, str] | None = None,
                     exc: BaseException | None = None):
        if exc is not None:
            opener.open.side_effect = exc
        else:
            opener.open.return_value = _FakeResponse(body, headers)
            opener.open.side_effect = None

    return opener, set_response


@pytest.fixture
def fake_response_factory():
    """Return a callable that produces ``_FakeResponse`` instances on demand."""
    return _FakeResponse
