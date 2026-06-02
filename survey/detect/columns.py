"""Column-level detectors: header anomalies, type heterogeneity, boundaries."""

from __future__ import annotations

import re
from collections import Counter

from .parser import ParsedSample


_NONALNUM_RE = re.compile(r"[^a-zA-Z0-9_]")
_LONG_HEADER = 64  # Pollock convention: column_header_long when len > 64


def column_names(sample: ParsedSample, header_count: int) -> list[str]:
    """Build a column-names list from the first ``header_count`` rows.

    Mirrors ``CSVFile.write_clean_csv`` lines 207-217: when there are
    multiple header rows the names are space-joined per column.
    """
    if header_count <= 0 or not sample.rows:
        n_cols = max((len(r) for r in sample.rows), default=0)
        return [f"col_{i}" for i in range(n_cols)]

    header_rows = sample.rows[:header_count]
    n_cols = max(len(r) for r in header_rows)
    columns: list[str] = []
    for col_idx in range(n_cols):
        parts = []
        for row in header_rows:
            if col_idx < len(row):
                parts.append((row[col_idx][0] or "").strip())
        columns.append(" ".join(p for p in parts if p))
    return columns


def column_header_unique(names: list[str]) -> bool:
    non_empty = [n for n in names if n]
    return len(non_empty) == len(set(non_empty)) if non_empty else True


def column_header_non_alnum(names: list[str]) -> bool:
    return any(_NONALNUM_RE.search(n) for n in names if n)


def column_header_empty(names: list[str]) -> bool:
    return any(not n for n in names)


def column_header_long(names: list[str]) -> bool:
    return any(len(n) > _LONG_HEADER for n in names)


def leading_trailing_whitespace_in_header(sample: ParsedSample, header_count: int) -> bool:
    """Header cells with leading/trailing whitespace before they were stripped."""
    if header_count <= 0 or not sample.rows:
        return False
    for row in sample.rows[:header_count]:
        for cell, _ in row:
            if cell != cell.strip():
                return True
    return False


def _column_type_histograms(sample: ParsedSample, header_count: int) -> list[Counter]:
    """Per-column ``Counter`` over ``parse_cell`` types (data rows only)."""
    from pollock.data_types import parse_cell

    if not sample.rows:
        return []
    n_cols = max(len(r) for r in sample.rows)
    histograms = [Counter() for _ in range(n_cols)]
    for row in sample.rows[header_count:]:
        for col_idx, (cell, _) in enumerate(row):
            if col_idx >= n_cols:
                break
            t = parse_cell(cell or "")
            if t == "TYPE_EMPTY":
                continue
            histograms[col_idx][t] += 1
    return histograms


def column_formats_heterogeneous(sample: ParsedSample, header_count: int) -> tuple[bool, float]:
    """Any column with > 1 non-empty type."""
    histograms = _column_type_histograms(sample, header_count)
    if not histograms:
        return False, 0.0
    heterogeneous = any(len(h) > 1 for h in histograms)
    return heterogeneous, 0.7 if sample.sampled else 0.9


def _dominant_type_changes(sample: ParsedSample, header_count: int) -> set[str]:
    """Return the set of types whose dominant column changes mid-file.

    Implementation: for each column, split data rows into two halves and
    compute the mode in each half. Any type that is the mode in one half
    but not the other counts as a "boundary".
    """
    from pollock.data_types import parse_cell

    if not sample.rows:
        return set()
    data_rows = sample.rows[header_count:]
    if len(data_rows) < 4:
        return set()
    mid = len(data_rows) // 2
    types_changed: set[str] = set()
    n_cols = max(len(r) for r in sample.rows)
    for col_idx in range(n_cols):
        first_half = []
        second_half = []
        for r_idx, row in enumerate(data_rows):
            if col_idx >= len(row):
                continue
            cell = row[col_idx][0] or ""
            t = parse_cell(cell)
            if t == "TYPE_EMPTY":
                continue
            (first_half if r_idx < mid else second_half).append(t)
        if not first_half or not second_half:
            continue
        mode_a = Counter(first_half).most_common(1)[0][0]
        mode_b = Counter(second_half).most_common(1)[0][0]
        if mode_a != mode_b:
            types_changed.add(mode_a)
            types_changed.add(mode_b)
    return types_changed


def column_string_boundary(sample: ParsedSample, header_count: int) -> bool:
    return "TYPE_STRING" in _dominant_type_changes(sample, header_count)


def column_int_boundary(sample: ParsedSample, header_count: int) -> bool:
    return "TYPE_INT" in _dominant_type_changes(sample, header_count)


def column_date_boundary(sample: ParsedSample, header_count: int) -> bool:
    return "TYPE_DATE" in _dominant_type_changes(sample, header_count)
