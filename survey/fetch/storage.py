"""Per-source corpus storage layout.

Files are staged under ``<root>/<source>/csv/`` (the same shape
the eurostat downloader uses), keyed by a sanitised basename derived from
the source URL. Collisions get a numeric suffix (``foo.csv``,
``foo__1.csv``, …) so we don't deduplicate or skip — every fetched file
lands on disk under a stable, human-readable name.

The ``<source>`` segment is the manifest ``origin`` (``data.gov``,
``data.gov.uk``, ``hf``, ``kaggle``, …) sanitised for filesystem use.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import BinaryIO
from urllib.parse import unquote, urlparse

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_SOURCE_DIR_RE = re.compile(r"[^A-Za-z0-9_.]+")


def source_dir(origin: str, root: Path) -> Path:
    """Return ``<root>/<origin>/csv`` (created if needed)."""
    safe = _SOURCE_DIR_RE.sub("_", origin).strip("_") or "unknown"
    out = root / safe / "csv"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _basename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = unquote((parsed.path.rsplit("/", 1)[-1] if parsed.path else "")) or "file"
    name = name.split("?", 1)[0].split("#", 1)[0]
    name = _SAFE_NAME_RE.sub("_", name).strip("._-") or "file"
    lower = name.lower()
    if not lower.endswith((".csv", ".tsv", ".csv.zstd", ".csv.zst", ".tsv.zstd", ".tsv.zst")):
        name = f"{name}.csv"
    if len(name) > 180:
        # Keep the extension, trim the stem.
        stem, _, ext = name.rpartition(".")
        name = (stem[: 180 - len(ext) - 1]).rstrip("_") + "." + ext
    return name


def stage_path(origin: str, url: str, root: Path) -> tuple[Path, BinaryIO]:
    """Reserve a fresh, non-colliding path and return ``(path, open_handle)``.

    Uses ``O_WRONLY | O_CREAT | O_EXCL`` so two threads racing the same
    basename are guaranteed distinct files (``foo.csv``, ``foo__1.csv``, …).
    The handle is opened in binary write mode; callers should use it via
    a ``with`` block to close deterministically.
    """
    base_dir = source_dir(origin, root)
    name = _basename_from_url(url)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY  # type: ignore[attr-defined]

    candidate = base_dir / name
    try:
        fd = os.open(candidate, flags, 0o644)
        return candidate, os.fdopen(fd, "wb")
    except FileExistsError:
        pass

    stem, _, ext = name.rpartition(".")
    n = 1
    while True:
        suffixed = base_dir / f"{stem}__{n}.{ext}"
        try:
            fd = os.open(suffixed, flags, 0o644)
            return suffixed, os.fdopen(fd, "wb")
        except FileExistsError:
            n += 1
