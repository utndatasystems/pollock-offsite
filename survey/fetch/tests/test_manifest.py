"""Unit tests for ``manifest`` (sha256, hash cache, ManifestWriter, append-mode)."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from survey.fetch import manifest
from survey.fetch._state import State
from survey.fetch.manifest import (
    ManifestRow,
    ManifestWriter,
    append_rows,
    load_known_hashes,
    manifest_path,
    sha256_file,
)


@pytest.fixture(autouse=True)
def _reset_hash_cache():
    """Reset the per-process hash cache so tests don't bleed."""
    manifest._KNOWN_HASHES_CACHE.clear()
    yield
    manifest._KNOWN_HASHES_CACHE.clear()


def _row(sha: str, path: str = "/tmp/x.csv", **overrides) -> ManifestRow:
    base = dict(
        origin="data.gov",
        url=f"https://example.com/{sha[:8]}.csv",
        sha256=sha,
        bytes=42,
        source="data.gov",
        picked_reason="test",
        fetched_at="2026-06-03T00:00:00Z",
        local_path=path,
    )
    base.update(overrides)
    return ManifestRow(**base)


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    payload = b"hello,world\n1,2\n3,4\n"
    p = tmp_path / "a.csv"
    p.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()
    assert sha256_file(p) == expected


def test_load_known_hashes_caches(tmp_path: Path) -> None:
    """Cache survives manifest mutations done outside ``ManifestWriter``."""
    out = tmp_path / "out"
    out.mkdir()
    append_rows(out, [_row("a" * 64)])

    first = load_known_hashes(out)
    assert "a" * 64 in first

    # Mutating the file directly must NOT cause a re-read; the cache is
    # process-local and only invalidated by ManifestWriter.add().
    append_rows(out, [_row("b" * 64)])

    second = load_known_hashes(out)
    assert second is first  # same object: cache hit
    assert "b" * 64 not in second  # stale by design


def test_manifest_writer_updates_cache(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    cached = load_known_hashes(out)
    assert cached == set()

    with ManifestWriter(out, State(out)) as mw:
        mw.add(_row("c" * 64))

    # The same cached set should now contain the just-added hash.
    assert "c" * 64 in load_known_hashes(out)


def test_manifest_writer_flushes_every_25(tmp_path: Path) -> None:
    """30 rows -> at least one batched flush during, all 30 persisted on exit."""
    out = tmp_path / "out"
    out.mkdir()
    p = manifest_path(out)

    with ManifestWriter(out, State(out), flush_every=25) as mw:
        for i in range(25):
            mw.add(_row(f"{i:064x}"))
        # After 25 adds, the 25-row batch should already be flushed to disk.
        assert p.exists()
        with open(p, newline="") as f:
            mid_count = sum(1 for _ in csv.DictReader(f))
        assert mid_count == 25

        for i in range(25, 30):
            mw.add(_row(f"{i:064x}"))

    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 30


def test_manifest_writer_finalises_remainder(tmp_path: Path) -> None:
    """Fewer than ``flush_every`` rows still land on ``__exit__``."""
    out = tmp_path / "out"
    out.mkdir()
    with ManifestWriter(out, State(out), flush_every=25) as mw:
        for i in range(7):
            mw.add(_row(f"{i:064x}"))

    with open(manifest_path(out), newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 7


def test_append_rows_creates_header_once(tmp_path: Path) -> None:
    """Two append calls produce a single header line and both rows."""
    out = tmp_path / "out"
    out.mkdir()
    append_rows(out, [_row("d" * 64)])
    append_rows(out, [_row("e" * 64)])
    p = manifest_path(out)
    text = p.read_text()
    assert text.count("origin,url,sha256") == 1
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    assert {r["sha256"] for r in rows} == {"d" * 64, "e" * 64}


def test_csv_injection_escape(tmp_path: Path) -> None:
    """Cells starting with formula triggers are prefixed with a single quote."""
    out = tmp_path / "out"
    out.mkdir()
    malicious = "=cmd|'/c calc'!A0"
    append_rows(
        out,
        [_row("f" * 64, picked_reason=malicious, url="=danger://x")],
    )
    with open(manifest_path(out), newline="") as f:
        row = next(csv.DictReader(f))
    assert row["picked_reason"] == "'" + malicious
    assert row["url"].startswith("'=")


def test_bytes_used_round_trips_via_state(tmp_path: Path) -> None:
    """ManifestWriter persists bytes_used into the shared State, not a sidecar."""
    out = tmp_path / "out"
    out.mkdir()
    state = State(out)
    with ManifestWriter(out, state) as mw:
        mw.add(_row("a" * 64))
        mw.note_bytes(123)
    assert State(out).get("bytes_used") == 123
    # Second writer continues from the prior total.
    state2 = State(out)
    with ManifestWriter(out, state2) as mw:
        mw.note_bytes(7)
    assert State(out).get("bytes_used") == 130
    # Legacy sidecar should not exist.
    assert not (out / ".fetch_state.json").exists()
