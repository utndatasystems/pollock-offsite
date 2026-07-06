"""Manifest writer / reader.

The manifest is a CSV under ``<out-dir>/manifest.csv`` with one row per
staged source file:

    origin,url,sha256,bytes,source,picked_reason,fetched_at,local_path

``origin``   — semantic origin (``data.gov``, ``data.gov.uk``,
                ``data.europa.eu``).
``url``      — absolute URL the body was fetched from.
``sha256``   — content hash of the raw downloaded bytes.
``bytes``    — size of the file on disk in bytes.
``source``   — catalog sub-source / dataset id when the backend tracks one;
                otherwise the same as ``origin``.
``picked_reason`` — provenance string built by the backend, of the form
                ``<source>:<title>`` truncated to 180 characters.
``fetched_at`` — ISO-8601 UTC timestamp.
``local_path`` — absolute path on disk.

The manifest is append-only and idempotent on ``sha256`` (re-runs that
encounter an already-known hash skip the file).
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ._state import State

MANIFEST_FIELDS = (
    "origin",
    "url",
    "sha256",
    "bytes",
    "source",
    "picked_reason",
    "fetched_at",
    "local_path",
)

# CSV-injection: a leading char in this set lets a spreadsheet treat the cell
# as a formula. Prepend a single quote when found in attacker-influenced fields.
_CSV_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass
class ManifestRow:
    """A single manifest entry; field meanings are documented at module level."""

    origin: str
    url: str
    sha256: str
    bytes: int
    source: str
    picked_reason: str
    fetched_at: str
    local_path: str


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def manifest_path(out_dir: Path) -> Path:
    return out_dir / "manifest.csv"


def _csv_safe(value: str) -> str:
    """Defang a CSV cell that could be parsed as a formula by a spreadsheet."""
    if isinstance(value, str) and value.startswith(_CSV_DANGEROUS_PREFIXES):
        return "'" + value
    return value


# Process-local cache for known hashes. Keyed by resolved out_dir to avoid
# cross-contamination between concurrent runs against different directories.
_KNOWN_HASHES_CACHE: dict[Path, set[str]] = {}


def load_known_hashes(out_dir: Path) -> set[str]:
    """Return the set of sha256s already in ``<out_dir>/manifest.csv``.

    Cached after first read; ``ManifestWriter.add`` keeps the cache in sync
    by inserting each row's hash. Re-reading the file is O(rows) and gets
    called from every backend's hot loop, so this matters at scale.
    """
    key = out_dir.resolve()
    cached = _KNOWN_HASHES_CACHE.get(key)
    if cached is not None:
        return cached
    p = manifest_path(out_dir)
    seen: set[str] = set()
    if p.exists():
        with open(p, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = (row.get("sha256") or "").strip()
                if s:
                    seen.add(s)
    _KNOWN_HASHES_CACHE[key] = seen
    return seen


def append_rows(out_dir: Path, rows: list[ManifestRow]) -> None:
    """Append ``rows`` to the manifest CSV.

    Opens the file in append mode and writes the header row only when the
    file does not already exist (or is empty). Per-flush cost is O(rows),
    not O(file).
    """
    if not rows:
        return
    p = manifest_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not p.exists() or p.stat().st_size == 0
    with open(p, "a", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=MANIFEST_FIELDS)
        if needs_header:
            writer.writeheader()
        for r in rows:
            d = asdict(r)
            d["url"] = _csv_safe(d.get("url", ""))
            d["picked_reason"] = _csv_safe(d.get("picked_reason", ""))
            writer.writerow(d)


class ManifestWriter:
    """Buffered manifest appender backed by ``State`` for the bytes counter.

    Use as a context manager. ``add(row)`` buffers; every ``flush_every``
    rows the buffer is appended. ``note_bytes(n)`` bumps the in-memory
    bytes total without persisting until exit. Exit flushes the remaining
    buffer and persists ``bytes_used`` to the shared ``State`` once.
    """

    def __init__(
        self, out_dir: Path, state: State, *, flush_every: int = 25
    ) -> None:
        self.out_dir = out_dir
        self._state = state
        self.flush_every = flush_every
        self._buffer: list[ManifestRow] = []
        try:
            self._bytes_at_start = int(state.get("bytes_used", 0) or 0)
        except (TypeError, ValueError):
            self._bytes_at_start = 0
        self._bytes_added = 0
        # Prime the hash cache so adds can keep it in sync cheaply.
        self._known_hashes = load_known_hashes(out_dir)

    def __enter__(self) -> "ManifestWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.flush()
        self._state.set("bytes_used", self._bytes_at_start + self._bytes_added)

    def add(self, row: ManifestRow) -> None:
        self._buffer.append(row)
        if row.sha256:
            self._known_hashes.add(row.sha256)
        if len(self._buffer) >= self.flush_every:
            self.flush()

    def note_bytes(self, n: int) -> None:
        self._bytes_added += int(n)

    def flush(self) -> None:
        if not self._buffer:
            return
        append_rows(self.out_dir, self._buffer)
        self._buffer.clear()

    @property
    def bytes_added(self) -> int:
        """Bytes ``note_bytes`` has been called with this run only."""
        return self._bytes_added

    @property
    def total_bytes(self) -> int:
        """Cumulative bytes downloaded into ``out_dir`` (previous runs + this run)."""
        return self._bytes_at_start + self._bytes_added
