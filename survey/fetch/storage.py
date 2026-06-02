"""Per-source corpus storage layout.

Files are staged under ``<repo_root>/data/<source>/csv/`` (the same shape
the eurostat downloader uses), keyed by a sanitised basename derived from
the source URL. Collisions get a numeric suffix (``foo.csv``,
``foo__1.csv``, …) so we don't deduplicate or skip — every fetched file
lands on disk under a stable, human-readable name.

The ``<source>`` segment is the manifest ``origin`` (``data.gov``,
``data.gov.uk``, ``hf``, ``kaggle``, …) sanitised for filesystem use.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..config import REPO_ROOT


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_SOURCE_DIR_RE = re.compile(r"[^A-Za-z0-9_.]+")


def source_dir(origin: str) -> Path:
    """Return ``<repo>/data/<origin>/csv`` (created if needed)."""
    safe = _SOURCE_DIR_RE.sub("_", origin).strip("_") or "unknown"
    out = REPO_ROOT / "data" / safe / "csv"
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


def stage_path(origin: str, url: str) -> Path:
    """Return a fresh, non-colliding path under the per-source dir.

    Same basename twice → ``foo.csv``, ``foo__1.csv``, ``foo__2.csv``, …
    """
    base_dir = source_dir(origin)
    name = _basename_from_url(url)
    candidate = base_dir / name
    if not candidate.exists():
        return candidate
    stem, _, ext = name.rpartition(".")
    n = 1
    while True:
        suffixed = base_dir / f"{stem}__{n}.{ext}"
        if not suffixed.exists():
            return suffixed
        n += 1
