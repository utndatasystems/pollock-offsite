"""Per-backend smoke tests.

For each full backend (``data.gov``, ``data.gov.uk``, ``data.europa.eu``) we
mock ``_http._OPENER`` to return canned search-endpoint responses then a tiny
CSV body, drive ``backend.run(opts)`` against a tmp dir, and assert that:

- ``manifest.csv`` exists with at least one row,
- ``.pollock_survey_state.json`` got the cursor key set.

For the stub backends we just assert that ``run`` returns ``2``.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from survey.fetch import _http, manifest as manifest_mod
from survey.fetch import ckan, data_europa_eu, datagov, hf, inside_airbnb, kaggle
from survey.fetch._state import State
from survey.fetch.config import CkanOptions, DataEuropaEuOptions, DataGovOptions, FetchOptions


CSV_BODY = b"col1,col2,col3\n1,2,3\n4,5,6\n"


class _FakeResponse:
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


@pytest.fixture(autouse=True)
def _reset_hash_cache():
    manifest_mod._KNOWN_HASHES_CACHE.clear()
    yield
    manifest_mod._KNOWN_HASHES_CACHE.clear()


def _base_opts(tmp_path: Path) -> FetchOptions:
    return FetchOptions(
        out_dir=tmp_path / "out",
        data_root=tmp_path / "out" / "raw",
        max_files=1,
        max_bytes=10**9,
        dry_run=False,
        concurrency=1,
        per_file_cap_bytes=10**6,
        head_timeout_s=2,
        request_timeout_s=5,
    )


def _route(routes: dict[str, bytes]):
    """Return a side_effect callable that picks a response based on URL prefix."""
    def side_effect(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        for prefix, body in routes.items():
            if prefix in url:
                return _FakeResponse(body)
        return _FakeResponse(b"")
    return side_effect


def test_datagov_smoke(monkeypatch, tmp_path: Path) -> None:
    csv_url = "https://example.com/data/datagov_x.csv"
    search_payload = {
        "after": None,
        "results": [
            {
                "dcat": {
                    "title": "Sample data.gov dataset",
                    "distribution": [
                        {
                            "downloadURL": csv_url,
                            "format": "csv",
                            "mediaType": "text/csv",
                            "byteSize": len(CSV_BODY),
                            "title": "sample.csv",
                        }
                    ],
                }
            }
        ],
    }
    opener = MagicMock()
    opener.open.side_effect = _route(
        {
            "catalog.data.gov/search": json.dumps(search_payload).encode(),
            csv_url: CSV_BODY,
        }
    )
    monkeypatch.setattr(_http, "_OPENER", opener)
    monkeypatch.setattr(_http, "head_size", lambda *a, **k: len(CSV_BODY))

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    opts = DataGovOptions(base=_base_opts(tmp_path), query="csv")
    rc = datagov.run(opts)
    assert rc == 0

    p = manifest_mod.manifest_path(out_dir)
    assert p.exists()
    rows = p.read_text().splitlines()
    assert len(rows) >= 2  # header + 1
    assert "data.gov" in rows[1]

    state = State(out_dir)
    cursors = state.get("datagov_cursors")
    # No "after" cursor in the canned payload -> backend pops it.
    assert cursors is None or cursors == {} or "csv" not in cursors


def test_data_gov_uk_smoke(monkeypatch, tmp_path: Path) -> None:
    csv_url = "https://example.com/data/uk_x.csv"

    def package_search_payload(start: int) -> dict:
        if start > 0:
            return {"success": True, "result": {"results": [], "count": 1}}
        return {
            "success": True,
            "result": {
                "count": 1,
                "results": [
                    {
                        "title": "UK package",
                        "resources": [
                            {
                                "url": csv_url,
                                "format": "csv",
                                "name": "file.csv",
                                "size": len(CSV_BODY),
                            }
                        ],
                    }
                ],
            },
        }

    def side_effect(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "package_search" in url:
            start = 0
            if "start=" in url:
                try:
                    start = int(url.split("start=")[1].split("&")[0])
                except ValueError:
                    start = 0
            return _FakeResponse(json.dumps(package_search_payload(start)).encode())
        if csv_url in url:
            return _FakeResponse(CSV_BODY)
        return _FakeResponse(b"")

    opener = MagicMock()
    opener.open.side_effect = side_effect
    monkeypatch.setattr(_http, "_OPENER", opener)
    monkeypatch.setattr(_http, "head_size", lambda *a, **k: len(CSV_BODY))

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    opts = CkanOptions(
        base=_base_opts(tmp_path),
        source="data.gov.uk",
        endpoint="https://ckan.publishing.service.gov.uk",
    )
    rc = ckan.run(opts)
    assert rc == 0

    p = manifest_mod.manifest_path(out_dir)
    assert p.exists()
    rows = p.read_text().splitlines()
    assert len(rows) >= 2
    assert "data.gov.uk" in rows[1]

    state = State(out_dir)
    cursors = state.get("ckan_cursors") or {}
    assert "data.gov.uk" in cursors


def test_data_europa_eu_smoke(monkeypatch, tmp_path: Path) -> None:
    csv_url = "https://example.com/data/eu_x.csv"
    search_payload = {
        "result": {
            "count": 1,
            "results": [
                {
                    "id": "abc",
                    "title": {"en": "EU dataset"},
                    "distributions": [
                        {
                            "format": {"id": "CSV"},
                            "access_url": [csv_url],
                            "byte_size": len(CSV_BODY),
                        }
                    ],
                }
            ],
        }
    }
    opener = MagicMock()
    opener.open.side_effect = _route(
        {
            "data.europa.eu/api/hub/search": json.dumps(search_payload).encode(),
            csv_url: CSV_BODY,
        }
    )
    monkeypatch.setattr(_http, "_OPENER", opener)
    monkeypatch.setattr(_http, "head_size", lambda *a, **k: len(CSV_BODY))

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    opts = DataEuropaEuOptions(base=_base_opts(tmp_path))
    rc = data_europa_eu.run(opts)
    assert rc == 0

    p = manifest_mod.manifest_path(out_dir)
    assert p.exists()
    rows = p.read_text().splitlines()
    assert len(rows) >= 2
    assert "data.europa.eu" in rows[1]

    state = State(out_dir)
    # ``count`` == 1 with page-size 1000 -> backend resets cursor to 0.
    assert state.get("data_europa_eu_next_page") in (0, None)


@pytest.mark.parametrize("backend", [inside_airbnb, hf, kaggle])
def test_stub_backends_exit_2(backend, tmp_path: Path) -> None:
    opts = _base_opts(tmp_path)
    rc = backend.run(opts)
    assert rc == 2
