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


def load_known_hashes(out_dir: Path) -> set[str]:
    p = manifest_path(out_dir)
    if not p.exists():
        return set()
    seen: set[str] = set()
    with open(p, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = (row.get("sha256") or "").strip()
            if s:
                seen.add(s)
    return seen


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
    p = fetch_state_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump({"bytes_used": int(value)}, f)


def append_rows(out_dir: Path, rows: list[ManifestRow]) -> None:
    if not rows:
        return
    p = manifest_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    is_new = not p.exists()
    with open(p, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if is_new:
            writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))
