"""Aggregate report generation.

Reads ``<out-dir>/parameters/*_parameters.json`` plus, when present, the
manifest and triage outputs, and produces:

- ``reports/survey_summary.csv``      — per-flag count / pct_files / mean_confidence
- ``reports/dialect_distribution.csv``— delim × encoding × quotechar co-occurrence
- ``reports/big_file_breakdown.csv``  — flag rates restricted to >10 MB files
- ``reports/summary.md``              — human-readable digest of the above
                                        plus tier1-vs-gold P/R/F1 (when ``score``
                                        was run first).
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from sut.utils import print as ts_print

from ..config import (
    BIG_FILE_THRESHOLD_BYTES,
    NEW_CANDIDATE_FLAGS,
    POLLOCK_ORIGINAL_FLAGS,
)


_BOOLEAN_FLAGS = POLLOCK_ORIGINAL_FLAGS + NEW_CANDIDATE_FLAGS
_TOP_N = 10


def _load_records(params_dir: Path) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    # rglob: tier1 outputs may be nested when input data is itself nested
    # (e.g. inside_airbnb mirrors country/region/city/date).
    for path in sorted(params_dir.rglob("*_parameters.json")):
        try:
            with open(path) as f:
                out.append((str(path.relative_to(params_dir)), json.load(f)))
        except Exception:
            continue
    return out


def _origin_of(record: dict) -> str:
    return (record.get("source_meta") or {}).get("origin") or "unknown"


def _bytes_of(record: dict) -> int:
    return int((record.get("source_meta") or {}).get("bytes") or 0)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _summary_rows(records: list[tuple[str, dict]]) -> list[dict]:
    n_files = len(records)
    rows: list[dict] = []
    for flag in _BOOLEAN_FLAGS:
        count = 0
        confs: list[float] = []
        for _, rec in records:
            ann = rec.get("annotations") or {}
            if bool(ann.get(flag)):
                count += 1
            conf = (rec.get("confidences") or {}).get(flag)
            if isinstance(conf, (int, float)):
                confs.append(float(conf))
        rows.append(
            {
                "flag": flag,
                "count": count,
                "pct_files": round(100 * count / n_files, 2) if n_files else 0.0,
                "mean_confidence": round(sum(confs) / len(confs), 3) if confs else None,
            }
        )
    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows


def _by_source_counts(records: list[tuple[str, dict]]) -> dict[str, dict[str, int]]:
    """Counter per origin (rows) × flag (cols) — used by summary.md."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, rec in records:
        origin = _origin_of(rec)
        out[origin]["__total__"] += 1
        ann = rec.get("annotations") or {}
        for flag in _BOOLEAN_FLAGS:
            if bool(ann.get(flag)):
                out[origin][flag] += 1
    return out


def _dialect_distribution(records: list[tuple[str, dict]]) -> list[dict]:
    """Co-occurrence: (delimiter, encoding, quotechar) tuples + counts."""
    counter: Counter = Counter()
    for _, rec in records:
        key = (
            rec.get("delimiter") or "",
            rec.get("encoding") or "",
            rec.get("quotechar") or "",
        )
        counter[key] += 1
    rows: list[dict] = []
    for (delim, enc, quote), count in counter.most_common():
        rows.append(
            {
                "delimiter": repr(delim),
                "encoding": enc,
                "quotechar": repr(quote),
                "count": count,
            }
        )
    return rows


def _big_file_breakdown(records: list[tuple[str, dict]]) -> list[dict]:
    big = [r for r in records if _bytes_of(r[1]) > BIG_FILE_THRESHOLD_BYTES]
    n_big = len(big)
    if not n_big:
        return []
    rows: list[dict] = []
    for flag in _BOOLEAN_FLAGS:
        count = sum(1 for _, rec in big if bool((rec.get("annotations") or {}).get(flag)))
        rows.append(
            {
                "flag": flag,
                "count": count,
                "pct_big_files": round(100 * count / n_big, 2),
                "n_big_files": n_big,
            }
        )
    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows


def _summary_md(
    records: list[tuple[str, dict]],
    summary_rows: list[dict],
    by_source: dict[str, dict[str, int]],
    dialect_rows: list[dict],
    big_file_rows: list[dict],
    tier1_score_rows: list[dict] | None,
) -> str:
    n_files = len(records)
    lines: list[str] = []
    lines.append("# CSV Pollution Survey — Summary\n")
    lines.append(f"**Files surveyed:** {n_files}\n")

    origins = {_origin_of(rec) for _, rec in records}
    lines.append(f"**Origins:** {', '.join(sorted(origins))}\n")

    lines.append("\n## Top pollutions\n")
    lines.append("| Flag | Count | % files | Mean confidence |\n")
    lines.append("|---|---:|---:|---:|\n")
    for row in summary_rows[:_TOP_N]:
        conf = row["mean_confidence"]
        conf_s = f"{conf:.2f}" if conf is not None else "–"
        lines.append(
            f"| `{row['flag']}` | {row['count']} | {row['pct_files']:.1f}% | {conf_s} |\n"
        )

    lines.append("\n## By source\n")
    lines.append("| Origin | Files | "
                 + " | ".join(f"`{f}`" for f in [r["flag"] for r in summary_rows[:5]])
                 + " |\n")
    lines.append("|---|---:|" + "|".join([":---:"] * 5) + "|\n")
    top5 = [r["flag"] for r in summary_rows[:5]]
    for origin, counts in sorted(by_source.items()):
        total = counts.get("__total__", 0)
        cells = " | ".join(
            f"{counts.get(flag, 0)} ({100*counts.get(flag,0)/total:.0f}%)" if total else "0"
            for flag in top5
        )
        lines.append(f"| {origin} | {total} | {cells} |\n")

    lines.append("\n## Top dialect combinations\n")
    lines.append("| Delimiter | Encoding | Quote char | Count |\n")
    lines.append("|---|---|---|---:|\n")
    for row in dialect_rows[:_TOP_N]:
        lines.append(
            f"| {row['delimiter']} | {row['encoding']} | {row['quotechar']} | {row['count']} |\n"
        )

    if big_file_rows:
        lines.append("\n## Pollutions in big files (>10 MB)\n")
        lines.append(f"_Big files in corpus: {big_file_rows[0]['n_big_files']}_\n\n")
        lines.append("| Flag | Count | % big files |\n")
        lines.append("|---|---:|---:|\n")
        for row in big_file_rows[:_TOP_N]:
            lines.append(
                f"| `{row['flag']}` | {row['count']} | {row['pct_big_files']:.1f}% |\n"
            )

    if tier1_score_rows:
        lines.append("\n## Tier 1 vs Gold (P/R/F1)\n")
        lines.append("| Flag | Support | P | R | F1 |\n")
        lines.append("|---|---:|---:|---:|---:|\n")
        for row in tier1_score_rows:
            if int(row.get("support", 0)) == 0:
                continue
            lines.append(
                f"| `{row['flag']}` | {row['support']} | "
                f"{row['precision']} | {row['recall']} | {row['f1']} |\n"
            )

    return "".join(lines)


def _load_score_csv(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    with open(path) as f:
        return list(csv.DictReader(f))


def run_report(args) -> int:
    out_dir: Path = Path(args.out_dir).resolve() if hasattr(args, "out_dir") else Path(args.out).parent
    reports_dir = (Path(args.out) if hasattr(args, "out") else out_dir / "reports").resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Tolerate either --out-dir or --out being passed.
    params_dir = (
        Path(args.out_dir).resolve() / "parameters"
        if hasattr(args, "out_dir")
        else reports_dir.parent / "parameters"
    )
    if not params_dir.is_dir():
        ts_print(f"[report] no parameters directory at {params_dir}")
        return 1

    records = _load_records(params_dir)
    if not records:
        ts_print(f"[report] no Tier 1 outputs to summarise under {params_dir}")
        return 0

    summary_rows = _summary_rows(records)
    by_source = _by_source_counts(records)
    dialect_rows = _dialect_distribution(records)
    big_file_rows = _big_file_breakdown(records)

    _write_csv(
        reports_dir / "survey_summary.csv",
        summary_rows,
        ["flag", "count", "pct_files", "mean_confidence"],
    )
    _write_csv(
        reports_dir / "dialect_distribution.csv",
        dialect_rows,
        ["delimiter", "encoding", "quotechar", "count"],
    )
    if big_file_rows:
        _write_csv(
            reports_dir / "big_file_breakdown.csv",
            big_file_rows,
            ["flag", "count", "pct_big_files", "n_big_files"],
        )

    # Pull in Tier 1 vs Gold table if `score` was run.
    tier1_score = _load_score_csv(reports_dir / "tier1_vs_gold.csv")

    md = _summary_md(records, summary_rows, by_source, dialect_rows, big_file_rows, tier1_score)
    (reports_dir / "summary.md").write_text(md)

    ts_print(
        f"[report] wrote {len(records)} files of summary to {reports_dir}/"
        f" (survey_summary.csv, dialect_distribution.csv, "
        f"{'big_file_breakdown.csv, ' if big_file_rows else ''}summary.md)"
    )
    return 0
