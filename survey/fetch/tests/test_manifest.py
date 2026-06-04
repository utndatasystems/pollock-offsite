"""Unit tests for ``manifest`` (sha256, hash cache, ManifestWriter, atomic write)."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from survey.fetch import manifest
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


def _row(sha: str, path: str = "/tmp/x.csv") -> ManifestRow:
    return ManifestRow(
        origin="data.gov",
        url=f"https://example.com/{sha[:8]}.csv",
        sha256=sha,
        bytes=42,
        source="data.gov",
        picked_reason="test",
        fetched_at="2026-06-03T00:00:00Z",
        local_path=path,
    )


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

    with ManifestWriter(out) as mw:
        mw.add(_row("c" * 64))

    # The same cached set should now contain the just-added hash.
    assert "c" * 64 in load_known_hashes(out)


def test_manifest_writer_flushes_every_25(tmp_path: Path) -> None:
    """30 rows -> at least one batched flush during, all 30 persisted on exit."""
    out = tmp_path / "out"
    out.mkdir()
    p = manifest_path(out)

    with ManifestWriter(out, flush_every=25) as mw:
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
    with ManifestWriter(out, flush_every=25) as mw:
        for i in range(7):
            mw.add(_row(f"{i:064x}"))

    with open(manifest_path(out), newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 7


def test_append_rows_atomic_keeps_original_on_failure(tmp_path: Path) -> None:
    """If ``os.replace`` raises mid-write, the original file is untouched."""
    out = tmp_path / "out"
    out.mkdir()
    append_rows(out, [_row("d" * 64)])
    p = manifest_path(out)
    original = p.read_bytes()

    with patch.object(manifest.os, "replace", side_effect=OSError("simulated")):
        with pytest.raises(OSError):
            append_rows(out, [_row("e" * 64)])

    assert p.read_bytes() == original
    # And the temp file was cleaned up.
    leftovers = [c for c in p.parent.iterdir() if c.name.startswith(p.name + ".")]
    assert leftovers == []
