"""Manifest writer / reader.

The manifest is a CSV under ``<out-dir>/manifest.csv`` with one row per
staged source file:

    origin,url,sha256,bytes,source,picked_reason,fetched_at,local_path

``origin``   — semantic origin (``data.gov``, ``data.gov.uk``, ``github``,
                ``hf``, ``kaggle``, ``local``).
``url``      — absolute URL or ``file://`` URI for local mode.
``sha256``   — content hash of the *raw* (compressed) bytes.
``bytes``    — size of the raw (compressed) file in bytes.
``source``   — sub-source / dataset id when meaningful (e.g. eurostat).
``picked_reason`` — why this file was selected (e.g. ``random``,
                ``big-wide-rows``, ``local-walk``).
``fetched_at`` — ISO-8601 UTC timestamp.
``local_path`` — absolute path on disk.

The manifest is append-only and idempotent on ``sha256`` (re-runs that
encounter an already-known hash skip the file).
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

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


@dataclass
class ManifestRow:
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


def fetch_state_path(out_dir: Path) -> Path:
    return out_dir / ".fetch_state.json"


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


def _atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` via a sibling tempfile + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def load_bytes_used(out_dir: Path) -> int:
    p = fetch_state_path(out_dir)
    if not p.exists():
        return 0
    try:
        with open(p) as f:
            return int(json.load(f).get("bytes_used", 0))
    except Exception:
        return 0


def save_bytes_used(out_dir: Path, value: int) -> None:
    _atomic_write_text(
        fetch_state_path(out_dir), json.dumps({"bytes_used": int(value)})
    )


def append_rows(out_dir: Path, rows: list[ManifestRow]) -> None:
    """Atomically append ``rows`` to the manifest CSV.

    Reads any existing rows, writes header+existing+new to a sibling
    tempfile, then ``os.replace``s it into place. Costs O(file) per flush;
    paired with ``ManifestWriter``'s ``flush_every=25`` that's acceptable.
    """
    if not rows:
        return
    p = manifest_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=MANIFEST_FIELDS)
            writer.writeheader()
            if p.exists():
                with open(p, newline="") as src:
                    reader = csv.DictReader(src)
                    for row in reader:
                        writer.writerow({k: row.get(k, "") for k in MANIFEST_FIELDS})
            for r in rows:
                writer.writerow(asdict(r))
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


class ManifestWriter:
    """Buffered, atomic-flushing manifest appender.

    Use as a context manager. ``add(row)`` buffers; every ``flush_every``
    rows the buffer is appended atomically. ``note_bytes(n)`` bumps the
    in-memory bytes total without persisting until exit. Exit flushes the
    remaining buffer and writes the bytes-used file once.
    """

    def __init__(self, out_dir: Path, *, flush_every: int = 25) -> None:
        self.out_dir = out_dir
        self.flush_every = flush_every
        self._buffer: list[ManifestRow] = []
        self._bytes_at_start = load_bytes_used(out_dir)
        self._bytes_added = 0
        # Prime the hash cache so adds can keep it in sync cheaply.
        self._known_hashes = load_known_hashes(out_dir)

    def __enter__(self) -> "ManifestWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.flush()
        save_bytes_used(self.out_dir, self._bytes_at_start + self._bytes_added)

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
        return self._bytes_added
