"""Unit tests for ``storage`` (basename derivation, O_EXCL collision handling)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from survey.fetch.storage import _basename_from_url, source_dir, stage_path


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com/data/file.csv", "file.csv"),
        ("https://example.com/data/file.tsv", "file.tsv"),
        # ``.csv.gz`` isn't in the recognised-extension list, so the writer
        # appends ``.csv`` to make the suffix unambiguous on disk.
        ("https://example.com/data/archive.csv.gz", "archive.csv.gz.csv"),
        ("https://example.com/data/snap.csv.zst", "snap.csv.zst"),
        # No extension --> .csv appended.
        ("https://example.com/data/anonymous", "anonymous.csv"),
        # Trailing slash --> placeholder name.
        ("https://example.com/", "file.csv"),
        # Query string and fragment stripped.
        ("https://example.com/data/file.csv?download=1#frag", "file.csv"),
        # URL-encoded path components decoded then sanitised.
        ("https://example.com/data/my%20file.csv", "my_file.csv"),
    ],
)
def test_basename_from_url(url: str, expected: str) -> None:
    assert _basename_from_url(url) == expected


def test_basename_trims_to_180_chars_keeping_extension() -> None:
    long_stem = "a" * 300
    name = _basename_from_url(f"https://example.com/{long_stem}.csv")
    assert len(name) <= 180
    assert name.endswith(".csv")


def test_source_dir_sanitises_origin(tmp_path: Path) -> None:
    out = source_dir("data.gov.uk", tmp_path)
    assert out.is_dir()
    assert out.parent.name == "data.gov.uk"
    assert out.name == "csv"


def test_source_dir_handles_unsafe_origin(tmp_path: Path) -> None:
    # Slashes / spaces collapse into underscores so we never escape ``root``.
    out = source_dir("weird/origin name", tmp_path)
    assert tmp_path in out.parents
    assert "/" not in out.parent.name


def test_stage_path_collision_suffix(tmp_path: Path) -> None:
    """A second call against the same URL gets ``__1`` suffix."""
    url = "https://example.com/data/file.csv"
    p1, fh1 = stage_path("origin", url, tmp_path)
    fh1.write(b"first")
    fh1.close()

    p2, fh2 = stage_path("origin", url, tmp_path)
    fh2.write(b"second")
    fh2.close()

    assert p1 != p2
    assert p1.name == "file.csv"
    assert p2.name == "file__1.csv"
    assert p1.read_bytes() == b"first"
    assert p2.read_bytes() == b"second"


def test_stage_path_returns_open_handle(tmp_path: Path) -> None:
    path, fh = stage_path("origin", "https://example.com/x.csv", tmp_path)
    try:
        # Handle is open, writable, and points at the same on-disk path.
        assert path.exists()
        fh.write(b"hello")
    finally:
        fh.close()
    assert path.read_bytes() == b"hello"


def test_stage_path_o_excl_race(tmp_path: Path) -> None:
    """Two threads racing the same URL must end up with distinct files.

    Exercises the O_EXCL retry: the prior code's ``if not exists`` TOCTOU
    would have let both threads pick the same path.
    """
    url = "https://example.com/data/race.csv"

    def call() -> Path:
        path, fh = stage_path("origin", url, tmp_path)
        try:
            fh.write(b"x")
        finally:
            fh.close()
        return path

    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = [ex.submit(call) for _ in range(2)]
        paths = sorted(f.result() for f in futures)

    assert len(paths) == 2
    assert paths[0] != paths[1]
    names = {p.name for p in paths}
    assert names == {"race.csv", "race__1.csv"}
