"""Local-directory fetch backend.

Walks ``--source-dir`` for CSV / TSV files (plain or zstd-compressed) and
appends one manifest row per file. Idempotent on sha256 — re-running over
the same directory only adds new files.

Recognised extensions:
- ``.csv`` / ``.CSV``  — plain CSV
- ``.tsv`` / ``.TSV``  — plain TSV
- ``.csv.zstd`` / ``.csv.zst`` / ``.CSV.zstd`` / ... — zstd-compressed CSV
- ``.tsv.zstd`` / ``.tsv.zst`` / ... — zstd-compressed TSV
- ``.csv.gz`` / ``.csv.gzip`` / ``.tsv.gz`` / ... — gzip-compressed CSV/TSV

The downstream annotator (``survey/detect/parser.py``) decompresses
``.zstd`` / ``.zst`` / ``.gz`` / ``.gzip`` files transparently, so this
fetcher does NOT decompress to disk.
"""

from __future__ import annotations

from pathlib import Path

from tqdm.auto import tqdm

from . import manifest
from ._log import get_logger

logger = get_logger("local")


# Recognised suffix patterns (lowercased comparison).
_PLAIN_SUFFIXES = (".csv", ".tsv")
_COMPRESSED_DOUBLE_SUFFIXES = (
    ".csv.zstd", ".csv.zst", ".tsv.zstd", ".tsv.zst",
    ".csv.gz", ".csv.gzip", ".tsv.gz", ".tsv.gzip",
)


def _is_csv_like(path: Path) -> bool:
    name = path.name.lower()
    if any(name.endswith(suf) for suf in _COMPRESSED_DOUBLE_SUFFIXES):
        return True
    if any(name.endswith(suf) for suf in _PLAIN_SUFFIXES):
        return True
    return False


def _walk(source_dir: Path) -> list[Path]:
    files = [p for p in source_dir.rglob("*") if p.is_file() and _is_csv_like(p)]
    files.sort()
    return files


def run_local(args) -> int:
    source_dir: Path = args.source_dir.resolve()
    out_dir: Path = Path(args.out_dir).resolve()

    if not source_dir.is_dir():
        logger.info(f"[fetch/local] not a directory: {source_dir}")
        return 1

    files = _walk(source_dir)
    if args.max_files is not None:
        files = files[: args.max_files]

    if not files:
        logger.info(f"[fetch/local] no CSV files under {source_dir}")
        return 0

    logger.info(
        f"[fetch/local] found {len(files)} candidate files "
        f"(scanning under {source_dir})"
    )

    if args.dry_run:
        for p in files[:50]:
            logger.info(f"[dry-run] {p}")
        if len(files) > 50:
            logger.info(f"[dry-run] ... and {len(files) - 50} more")
        return 0

    known = manifest.load_known_hashes(out_dir)
    # Per-run byte ledger: --max-bytes caps just this invocation's adds.
    bytes_at_start = manifest.load_bytes_used(out_dir)
    bytes_this_run = 0
    rows: list[manifest.ManifestRow] = []
    n_skipped_known = 0
    n_skipped_budget = 0

    for path in tqdm(files, desc="fetch local", unit="file", dynamic_ncols=True, leave=False):
        size = path.stat().st_size
        if bytes_this_run + size > args.max_bytes:
            n_skipped_budget += 1
            continue
        h = manifest.sha256_file(path)
        if h in known:
            n_skipped_known += 1
            continue
        known.add(h)
        rows.append(
            manifest.ManifestRow(
                origin="local",
                url=path.resolve().as_uri(),
                sha256=h,
                bytes=size,
                source=source_dir.name,
                picked_reason="local-walk",
                fetched_at=manifest.now_iso(),
                local_path=str(path.resolve()),
            )
        )
        bytes_this_run += size

    manifest.append_rows(out_dir, rows)
    manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)

    logger.info(
        f"[fetch/local] manifest written: {len(rows)} new, "
        f"{n_skipped_known} already-known, {n_skipped_budget} skipped (byte cap), "
        f"bytes_this_run={bytes_this_run:,}"
    )
    return 0
