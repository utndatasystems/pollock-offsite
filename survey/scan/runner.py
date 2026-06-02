"""Scan runner — walks an input directory, runs detectors in parallel,
writes one JSON per pollution.

Modeled on ``survey.detect.runner.run_annotate``: same joblib + tqdm
parallelism pattern, same compression-aware file walker.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from joblib import Parallel, delayed

from sut.utils import print as ts_print

from ..detect import format_check
from ..detect.runner import CSV_GLOBS, _list_csv_files
from .detectors import (
    DEFAULT_LONG_FIELD_CHARS,
    DEFAULT_MAX_BYTES,
    POLLUTION_NAMES,
    scan_file,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scan_one(
    path: Path,
    in_dir: Path,
    dataset_prefix: str,
    long_field_chars: int,
    max_bytes: int,
    no_sampling: bool,
) -> tuple[str, dict[str, list[int]] | None, bool, str | None]:
    """Worker: scan one file. Returns (rel_path, results, sampled, err)."""
    try:
        rel = str(path.relative_to(in_dir))
    except ValueError:
        rel = str(path)
    if dataset_prefix:
        rel = f"{dataset_prefix}/{rel}"
    non_csv = format_check.detect_non_csv_format(path)
    if non_csv is not None:
        return rel, None, False, f"non-csv format detected: {non_csv}"
    try:
        results, sampled = scan_file(
            path,
            long_field_chars=long_field_chars,
            max_bytes=max_bytes,
            no_sampling=no_sampling,
        )
        return rel, results, sampled, None
    except Exception as exc:  # noqa: BLE001
        return rel, None, False, repr(exc)


def run_scan(args) -> int:
    in_dir: Path = Path(args.in_dir).resolve()
    dataset_prefix: str | None = getattr(args, "dataset_prefix", None)
    if dataset_prefix is None:
        dataset_prefix = in_dir.name
    out_dir: Path = (Path(args.out_dir) / "scan" / dataset_prefix).resolve()
    long_field_chars: int = int(getattr(args, "long_field_chars", DEFAULT_LONG_FIELD_CHARS))
    max_bytes: int = int(getattr(args, "max_bytes", DEFAULT_MAX_BYTES))
    jobs: int = int(getattr(args, "jobs", 1))
    force: bool = bool(getattr(args, "force", False))
    no_sampling: bool = bool(getattr(args, "no_sampling", False))

    if not in_dir.is_dir():
        ts_print(f"[scan] no input directory: {in_dir}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    pollution_paths = [out_dir / f"{n}.json" for n in POLLUTION_NAMES]

    # Treat ANY existing output (summary or per-defect) as "already populated"
    # so we never half-overwrite a previous run when summary.json was missing.
    existing = [p for p in [summary_path, *pollution_paths] if p.exists()]
    if existing and not force:
        ts_print(
            f"[scan] output already populated under {out_dir} "
            f"({len(existing)} file(s)); pass --force to overwrite."
        )
        return 0

    files = _list_csv_files(in_dir)
    if not files:
        ts_print(f"[scan] no CSV files under {in_dir}")
        return 0

    ts_print(f"[scan] {len(files)} files -> {out_dir} (jobs={jobs})")
    t0 = time.time()

    # Aggregator: pollution -> {rel_path -> [line_numbers]}.
    aggregate: dict[str, dict[str, list[int]]] = {n: {} for n in POLLUTION_NAMES}
    errors: dict[str, str] = {}
    sampled_files: list[str] = []
    n_ok = 0

    from tqdm.auto import tqdm

    def _ingest(
        rel: str,
        results: dict[str, list[int]] | None,
        sampled: bool,
        err: str | None,
    ) -> None:
        nonlocal n_ok
        if err is not None or results is None:
            errors[rel] = err or "unknown"
            return
        n_ok += 1
        if sampled:
            sampled_files.append(rel)
        for name, lines in results.items():
            if lines:
                aggregate[name][rel] = lines

    if jobs <= 1:
        for p in tqdm(files, desc="scan", unit="file", dynamic_ncols=True, leave=False):
            rel, res, sampled, err = _scan_one(
                p, in_dir, dataset_prefix, long_field_chars, max_bytes, no_sampling
            )
            _ingest(rel, res, sampled, err)
    else:
        bar = tqdm(
            total=len(files),
            desc="scan",
            unit="file",
            dynamic_ncols=True,
            leave=False,
        )
        try:
            for rel, res, sampled, err in Parallel(
                n_jobs=jobs,
                prefer="processes",
                return_as="generator_unordered",
            )(
                delayed(_scan_one)(p, in_dir, dataset_prefix, long_field_chars, max_bytes, no_sampling)
                for p in files
            ):
                _ingest(rel, res, sampled, err)
                bar.update(1)
        finally:
            bar.close()

    # Write per-pollution JSONs (sorted by key for stable diffs).
    for name, mapping in aggregate.items():
        path = out_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {k: mapping[k] for k in sorted(mapping)},
                f,
                indent=2,
                ensure_ascii=False,
            )

    sampled_files.sort()
    summary = {
        "scanned_at": _now_iso(),
        "input_dir": str(in_dir),
        "dataset_prefix": dataset_prefix,
        "n_files_total": len(files),
        "n_files_ok": n_ok,
        "n_files_error": len(errors),
        "long_field_chars": long_field_chars,
        "max_bytes": max_bytes,
        "no_sampling": no_sampling,
        "counts": {name: len(aggregate[name]) for name in POLLUTION_NAMES},
        "sampled_files": sampled_files,
        "errors": errors,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - t0
    ts_print(
        f"[scan] done: {n_ok}/{len(files)} ok, {len(errors)} errors in {elapsed:.1f}s"
    )
    for name in POLLUTION_NAMES:
        ts_print(f"  {name}: {len(aggregate[name])} files")
    if sampled_files:
        ts_print(
            f"[scan] {len(sampled_files)} file(s) used head/tail sampling "
            f"(line numbers in the tail half are unreliable):"
        )
        # Cap the inline list — full list is in summary.json.
        for rel in sampled_files[:20]:
            ts_print(f"  sampled: {rel}")
        if len(sampled_files) > 20:
            ts_print(
                f"  ... and {len(sampled_files) - 20} more "
                f"(see summary.json::sampled_files)"
            )
    return 0
