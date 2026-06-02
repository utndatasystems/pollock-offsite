"""Compression-aware file IO for Tier 1 detectors.

Most CSVs are plain bytes on disk. Some corpora ship compressed:
Eurostat uses ``foo.csv.zstd``; Inside Airbnb uses ``foo.csv.gz``. The
detector pipeline needs to read these transparently — without
materialising decompressed copies — so this module wraps every form
behind a small helper API:

- ``is_compressed(path)``  — does the path look like a compressed CSV?
- ``logical_name(path)``   — the original ``foo.csv`` name (used for
                              filename-level detectors and output JSON
                              naming).
- ``read_all_bytes(path)`` — full uncompressed bytes (used for small
                              files only — capped by caller).
- ``read_head_bytes(path, n)`` — first ``n`` uncompressed bytes.
- ``open_decompressed(path)`` — context-managed binary stream of
                              uncompressed bytes (used by the head/tail
                              sampler).

Plain CSVs route straight to ``open(path, "rb")``; ``.zstd`` / ``.zst``
files stream through ``zstandard.ZstdDecompressor.stream_reader``;
``.gz`` / ``.gzip`` files stream through ``gzip.open``.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Iterator


_ZSTD_SUFFIXES = (".zstd", ".zst")
_GZIP_SUFFIXES = (".gz", ".gzip")


def _is_zstd(path: Path) -> bool:
    return path.suffix.lower() in _ZSTD_SUFFIXES


def _is_gzip(path: Path) -> bool:
    return path.suffix.lower() in _GZIP_SUFFIXES


def is_compressed(path: Path) -> bool:
    return _is_zstd(path) or _is_gzip(path)


def logical_name(path: Path) -> str:
    """``foo.csv.zstd`` / ``foo.csv.gz`` → ``foo.csv``; otherwise unchanged."""
    if is_compressed(path):
        return path.with_suffix("").name
    return path.name


@contextmanager
def open_decompressed(path: Path) -> Iterator[IO[bytes]]:
    if _is_zstd(path):
        import zstandard as zstd

        f = open(path, "rb")
        try:
            dctx = zstd.ZstdDecompressor()
            stream = dctx.stream_reader(f)
            try:
                yield stream
            finally:
                stream.close()
        finally:
            f.close()
    elif _is_gzip(path):
        import gzip

        f = gzip.open(path, "rb")
        try:
            yield f
        finally:
            f.close()
    else:
        f = open(path, "rb")
        try:
            yield f
        finally:
            f.close()


def read_head_bytes(path: Path, n: int) -> bytes:
    """First ``n`` uncompressed bytes (or fewer if the file is shorter)."""
    with open_decompressed(path) as f:
        return f.read(n)


def read_all_bytes(path: Path, cap: int | None = None) -> bytes:
    """Read the full uncompressed contents.

    Pass ``cap`` to put an upper bound on the bytes returned (the stream is
    closed at that point so we never materialise more than necessary).
    """
    with open_decompressed(path) as f:
        if cap is None:
            return f.read()
        # Read in chunks so we don't allocate the entire stream up front.
        chunks: list[bytes] = []
        remaining = cap
        while remaining > 0:
            block = f.read(min(1 << 20, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        return b"".join(chunks)


def file_size_compressed(path: Path) -> int:
    """Size of the file as it sits on disk (the compressed size for ``.zstd``)."""
    return os.path.getsize(path)


def estimated_uncompressed_size(path: Path, sample_bytes: int = 1 << 20) -> int:
    """Best-effort estimate of the decompressed size.

    For plain files this returns the file size on disk. For zstd files we
    decompress a small head sample and extrapolate from the compression
    ratio observed there. The result is only used to decide whether to
    take the head/tail-sampling code path; precision doesn't matter much.
    """
    on_disk = file_size_compressed(path)
    if not is_compressed(path):
        return on_disk

    if _is_gzip(path):
        # Last 4 bytes of a gzip member encode ISIZE (uncompressed size mod 2^32).
        # Good enough for our "is this big enough to head/tail sample" gate.
        try:
            with open(path, "rb") as f:
                f.seek(-4, os.SEEK_END)
                isize_bytes = f.read(4)
            if len(isize_bytes) == 4:
                return int.from_bytes(isize_bytes, "little")
        except OSError:
            pass
        return on_disk * 4  # crude fallback

    import zstandard as zstd

    # Read a sample of compressed bytes and decompress them.
    with open(path, "rb") as f:
        head = f.read(sample_bytes)
    try:
        dctx = zstd.ZstdDecompressor()
        decompressed_sample = dctx.decompress(head, max_output_size=sample_bytes * 32)
    except zstd.ZstdError:
        # Streaming variant (frame can't be decoded as a single block).
        try:
            dctx = zstd.ZstdDecompressor()
            decompressed_sample = dctx.stream_reader(__import__("io").BytesIO(head)).read(
                sample_bytes * 32
            )
        except Exception:
            return on_disk * 4  # crude fallback assumption: 4× ratio

    if not head:
        return on_disk
    ratio = len(decompressed_sample) / max(len(head), 1)
    return int(on_disk * ratio)
