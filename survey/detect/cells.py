"""Cell-level detectors: multiline cells, locale numbers, units, missing-value qualifiers."""

from __future__ import annotations

import re
from collections import Counter

from .parser import ParsedSample, SAMPLE_GAP_TOKEN


_EUROPEAN_NUM_RE = re.compile(r"^\d{1,3}(\.\d{3})+,\d+$")
_UNIT_SUFFIX_RE = re.compile(
    r"^-?\d+(?:[.,]\d+)?\s?(kg|g|mg|cm|mm|m|km|%|°[CF]?|ms|s|hr|min|MB|GB|KB|TB|°)$",
    re.IGNORECASE,
)
_KNOWN_NULL_TOKENS = {
    "",
    "na",
    "n/a",
    "null",
    "nil",
    "nan",
    "none",
    "-",
    "--",
    "?",
    "missing",
    "n.a.",
    "sans objet",
    "no data",
}


def multiline_cell_present(sample: ParsedSample) -> bool:
    """Any cell containing the file's record delimiter (i.e. an embedded newline)."""
    if not sample.rows:
        return False
    for row in sample.rows:
        for cell, is_quoted in row:
            if "\n" in cell or "\r" in cell:
                return True
    return False


def locale_european_numbers(sample: ParsedSample) -> bool:
    """Any column whose majority of non-empty cells match the EU number pattern."""
    if not sample.rows:
        return False
    n_cols = max(len(r) for r in sample.rows)
    for col_idx in range(n_cols):
        cells = []
        for row in sample.rows:
            if col_idx < len(row):
                v = row[col_idx][0]
                if v and v.strip():
                    cells.append(v.strip())
        if not cells:
            continue
        matches = sum(1 for c in cells if _EUROPEAN_NUM_RE.match(c))
        if matches >= 3 and matches / len(cells) >= 0.6:
            return True
    return False


def units_in_values(sample: ParsedSample) -> bool:
    """Any column where >=20% of cells end in a unit suffix."""
    if not sample.rows:
        return False
    n_cols = max(len(r) for r in sample.rows)
    for col_idx in range(n_cols):
        cells = []
        for row in sample.rows:
            if col_idx < len(row):
                v = row[col_idx][0]
                if v and v.strip():
                    cells.append(v.strip())
        if len(cells) < 3:
            continue
        matches = sum(1 for c in cells if _UNIT_SUFFIX_RE.match(c))
        if matches / len(cells) >= 0.2 and matches >= 3:
            return True
    return False


def missing_value_qualifier_diverse(sample: ParsedSample) -> bool:
    """Two-or-more distinct null tokens in the file.

    The original Pollock convention treats only the empty string as null;
    Hypoparsr / Pytheas show real-world files mix multiple ("NA", "-",
    "N/A", custom locale terms). We flag when ≥ 2 distinct tokens appear.
    """
    if not sample.rows:
        return False
    seen: Counter = Counter()
    for row in sample.rows:
        for cell, _ in row:
            v = (cell or "").strip().lower()
            if v in _KNOWN_NULL_TOKENS:
                seen[v] += 1
    return len(seen) >= 2
