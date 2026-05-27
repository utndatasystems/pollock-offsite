#!/usr/bin/env python3
"""Summarize SUT benchmark errors into a repo-level CSV file."""

from __future__ import annotations

import argparse
import csv
import os
import re
from collections import defaultdict
from pathlib import Path


POLLUTION_PATTERNS = [
    (r"file_no_payload", "Empty file (0 bytes)"),
    (r"file_no_trailing_newline", "Missing trailing newline"),
    (r"file_double_trailing_newline", "Double trailing newline"),
    (r"file_no_header", "No header row"),
    (r"file_header_multirow_(\d+)", "Multi-row header ({0} rows)"),
    (r"file_header_only", "Header row only, no data"),
    (r"file_one_data_row", "Single data row"),
    (r"file_preamble", "Preamble rows before header"),
    (r"file_multitable_less", "Two tables, first has fewer columns"),
    (r"file_multitable_more", "Two tables, first has more columns"),
    (r"file_multitable_same", "Two tables with the same number of columns"),
    (r"file_field_delimiter_(0x\w+(?:_0x\w+)*)", "Non-standard field delimiter ({0})"),
    (r"file_quotation_char_(0x\w+)", "Non-standard quotation character ({0})"),
    (r"file_escape_char_(0x\w+)", "Non-standard escape character ({0})"),
    (r"file_record_delimiter_(0x\w+)", "Non-standard record delimiter ({0})"),
    (r"row_extra_quote(\d+)_col(\d+)", "Extra unescaped quote in row {0}, column {1}"),
    (
        r"row_field_delimiter_(\d+)_",
        "Row {0} uses space as field delimiter (opposed to the correct delimiter defined by the grammar)",
    ),
    (r"row_less_sep_row(\d+)_col(\d+)", "Missing delimiter in row {0} at column {1}"),
    (r"row_more_sep_row(\d+)_col(\d+)", "Extra delimiter in row {0} at column {1}"),
]


GROUP_PATTERNS = [
    (r"row_field_delimiter_\d+_", "One single row uses space as field delimiter"),
    (r"row_extra_quote\d+_col\d+", "Extra unescaped quote in one single row"),
    (r"row_less_sep_row\d+_col\d+", "Missing delimiter in one single row"),
    (r"row_more_sep_row\d+_col\d+", "Extra delimiter in one single row"),
]


SUMMARY_FIELDS = [
    "dataset",
    "sut",
    "pollution_group",
    "total_files",
    "failed_files",
    "poor_files",
    "error_files",
    "failure_rate",
    "poor_rate",
    "error_rate",
    "avg_header_f1",
    "avg_record_f1",
    "avg_cell_f1",
    "min_cell_f1",
    "worst_file",
]


def pollution_group(filename: str) -> str:
    """Collapse row-specific variants but keep detailed file-level pollution labels."""
    stem = filename.removesuffix(".csv")
    for pattern, description in GROUP_PATTERNS:
        if re.match(pattern, stem):
            return description
    for pattern, description in POLLUTION_PATTERNS:
        match = re.match(pattern, stem)
        if match:
            return description.format(*match.groups())
    return "Unknown"


def float_value(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def discover_suts(results_dir: Path, dataset: str) -> list[str]:
    suts = []
    if not results_dir.exists():
        return suts
    for child in sorted(results_dir.iterdir()):
        if not child.is_dir():
            continue
        result_file = child / dataset / f"{child.name}_results.csv"
        if result_file.exists():
            suts.append(child.name)
    return suts


def empty_stats() -> dict:
    return {
        "total_files": 0,
        "failed_files": 0,
        "poor_files": 0,
        "header_f1_sum": 0.0,
        "record_f1_sum": 0.0,
        "cell_f1_sum": 0.0,
        "min_cell_f1": None,
        "worst_file": "",
    }


def update_stats(stats: dict, row: dict[str, str], sut: str, threshold: float) -> None:
    success = int(float_value(row, f"{sut}_success"))
    header_f1 = float_value(row, f"{sut}_header_f1")
    record_f1 = float_value(row, f"{sut}_record_f1")
    cell_f1 = float_value(row, f"{sut}_cell_f1")

    stats["total_files"] += 1
    stats["header_f1_sum"] += header_f1
    stats["record_f1_sum"] += record_f1
    stats["cell_f1_sum"] += cell_f1

    if success == 0:
        stats["failed_files"] += 1
    elif cell_f1 < threshold:
        stats["poor_files"] += 1

    if stats["min_cell_f1"] is None or cell_f1 < stats["min_cell_f1"]:
        stats["min_cell_f1"] = cell_f1
        stats["worst_file"] = row.get("file", "")


def finalize(dataset: str, sut: str, group: str, stats: dict) -> dict[str, str]:
    total = stats["total_files"]
    failed = stats["failed_files"]
    poor = stats["poor_files"]
    errors = failed + poor

    def rate(value: int) -> str:
        return f"{value / total:.6f}" if total else "0.000000"

    def avg(value: float) -> str:
        return f"{value / total:.6f}" if total else "0.000000"

    min_cell = stats["min_cell_f1"]
    return {
        "dataset": dataset,
        "sut": sut,
        "pollution_group": group,
        "total_files": str(total),
        "failed_files": str(failed),
        "poor_files": str(poor),
        "error_files": str(errors),
        "failure_rate": rate(failed),
        "poor_rate": rate(poor),
        "error_rate": rate(errors),
        "avg_header_f1": avg(stats["header_f1_sum"]),
        "avg_record_f1": avg(stats["record_f1_sum"]),
        "avg_cell_f1": avg(stats["cell_f1_sum"]),
        "min_cell_f1": f"{min_cell:.6f}" if min_cell is not None else "",
        "worst_file": stats["worst_file"],
    }


def summarize_sut(results_file: Path, dataset: str, sut: str, threshold: float) -> list[dict[str, str]]:
    by_group = defaultdict(empty_stats)
    overall = empty_stats()

    with results_file.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"file", f"{sut}_success", f"{sut}_cell_f1"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{results_file} is missing columns: {sorted(missing)}")

        for row in reader:
            group = pollution_group(row["file"])
            update_stats(by_group[group], row, sut, threshold)
            update_stats(overall, row, sut, threshold)

    rows = [finalize(dataset, sut, "ALL", overall)]
    rows.extend(
        finalize(dataset, sut, group, stats)
        for group, stats in sorted(by_group.items(), key=lambda item: item[0])
    )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="polluted_files", help="Dataset name under results/<sut>/")
    parser.add_argument("--threshold", type=float, default=0.99, help="Cell F1 below this is counted as poor.")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Root results directory.")
    parser.add_argument("--output", type=Path, default=Path("sut_error_summary.csv"), help="Repo-level output CSV.")
    parser.add_argument("--sut", action="append", dest="suts", help="SUT to include. Repeatable. Defaults to all found.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suts = args.suts or discover_suts(args.results_dir, args.dataset)
    if not suts:
        raise SystemExit(f"No SUT result files found for dataset '{args.dataset}' in {args.results_dir}")

    rows: list[dict[str, str]] = []
    for sut in sorted(suts):
        results_file = args.results_dir / sut / args.dataset / f"{sut}_results.csv"
        if not results_file.exists():
            print(f"skip missing results file: {results_file}")
            continue
        rows.extend(summarize_sut(results_file, args.dataset, sut, args.threshold))

    if not rows:
        raise SystemExit("No summary rows were generated.")

    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
