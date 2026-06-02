"""Structural detectors: header/preamble/footnote, multi-table, jagged rows.

Header / preamble / footnote heuristics roughly follow what
``pollock/CSVFile.py:write_parameters`` would compute on its XML tree, but
operate directly on the parsed row list (no XML, so big files don't OOM).
"""

from __future__ import annotations

import re
from collections import Counter

from .parser import ParsedSample, SAMPLE_GAP_TOKEN

# Heuristics
_HEADER_LIKE_TYPE = "TYPE_STRING"
# Cell types that unambiguously mark a row as data (not header). If any cell
# in a candidate header row parses as one of these, the row can't be header.
# This was the missing constraint that caused 99% false-positive rate of
# table_multirow_header on Eurostat SDMX-CSV: data rows there have
# string-typed dimension codes in early columns (DATAFLOW, freq, geo)
# *plus* a numeric OBS_VALUE — the old heuristic only counted the strings
# and ignored the numeric.
_DATA_TYPES = frozenset({"TYPE_INT", "TYPE_FLOAT", "TYPE_DATE", "TYPE_TIME", "TYPE_BOOLEAN", "TYPE_PRICE"})
_LINE_ART_RE = re.compile(r"^\s*[-=*_~]{5,}\s*$")
_COMMENT_PREFIXES = ("#", "//", ";")
_AGGREGATE_KEYWORDS = (
    "total",
    "subtotal",
    "sum",
    "grand total",
    "average",
    "mean",
    "count",
)


def _row_text(row: list[tuple[str, bool]]) -> str:
    return "".join(cell for cell, _ in row)


def _row_is_empty(row: list[tuple[str, bool]]) -> bool:
    return all(not cell.strip() for cell, _ in row)


def n_rows_cols(sample: ParsedSample) -> tuple[int, int]:
    if not sample.rows:
        return 0, 0
    n_rows = len(sample.rows)
    n_cols = max(len(r) for r in sample.rows) if sample.rows else 0
    return n_rows, n_cols


def header_lines(sample: ParsedSample) -> tuple[int, float]:
    """Best-effort header-row count.

    Heuristic: a "header" run is a contiguous block of leading rows whose
    cells are predominantly strings (``parse_cell`` returns
    ``TYPE_STRING``) AND the block is followed by a row whose dominant
    type differs. Maxes out at 3 leading rows (matches the original
    Pollock file_header_multirow_2/3 cap).
    """
    from pollock.data_types import parse_cell  # imported lazily for cost

    if not sample.rows:
        return 0, 0.0

    # Skip preamble rows (≤ 1-cell rows or fully-empty rows) when scanning.
    non_preamble_idx = 0
    for idx, row in enumerate(sample.rows):
        # Heuristic: a "preamble" row has a single non-empty cell or is empty.
        if _row_is_empty(row):
            continue
        non_empty_cells = [c for c, _ in row if c.strip()]
        if len(non_empty_cells) <= 1 and len(row) > 1:
            continue
        non_preamble_idx = idx
        break

    candidate_block_size = 0
    for idx in range(non_preamble_idx, min(non_preamble_idx + 3, len(sample.rows))):
        row = sample.rows[idx]
        if _row_is_empty(row):
            break
        types = [parse_cell(c) for c, _ in row if c.strip()]
        if not types:
            break
        # Hard rule: a header row must contain NO cells that parse as ints,
        # floats, dates, times, booleans, or currency. Even one numeric/date
        # cell makes this a data row. The old "≥60% strings" rule fired on
        # SDMX-CSV data rows that have string-typed dimension codes plus a
        # numeric OBS_VALUE — exactly the pattern that produced ~99% false
        # positives for table_multirow_header on Eurostat (493/493 files).
        n_data_typed = sum(1 for t in types if t in _DATA_TYPES)
        if n_data_typed > 0:
            break
        string_share = sum(1 for t in types if t == _HEADER_LIKE_TYPE) / len(types)
        if string_share >= 0.6:
            candidate_block_size += 1
        else:
            break

    # Need at least one downstream row whose dominant type isn't string,
    # otherwise we'd flag pure-text files as "all header".
    if candidate_block_size > 0:
        for idx in range(non_preamble_idx + candidate_block_size, len(sample.rows)):
            row = sample.rows[idx]
            if _row_is_empty(row):
                continue
            types = [parse_cell(c) for c, _ in row if c.strip()]
            if not types:
                continue
            string_share = sum(1 for t in types if t == _HEADER_LIKE_TYPE) / len(types)
            if string_share < 0.6:
                return candidate_block_size, 0.85
            return candidate_block_size, 0.6
        # No downstream type-change found.
        return candidate_block_size, 0.4

    return 0, 0.7


def preamble_lines(sample: ParsedSample) -> tuple[int, float]:
    """Count leading rows that are empty or have a single non-empty cell."""
    if not sample.rows:
        return 0, 0.0
    count = 0
    for row in sample.rows:
        if _row_is_empty(row):
            count += 1
            continue
        non_empty_cells = [c for c, _ in row if c.strip()]
        if len(non_empty_cells) <= 1 and len(row) > 1:
            count += 1
            continue
        break
    return count, 0.9


def footnote_lines(sample: ParsedSample) -> tuple[int, float]:
    """Count trailing rows that are empty or have a single non-empty cell."""
    if not sample.rows:
        return 0, 0.0
    count = 0
    for row in reversed(sample.rows):
        if _row_is_empty(row):
            count += 1
            continue
        non_empty_cells = [c for c, _ in row if c.strip()]
        if len(non_empty_cells) <= 1 and len(row) > 1:
            count += 1
            continue
        break
    return count, 0.9


def table_no_header(header_count: int) -> bool:
    return header_count == 0


def table_multirow_header(header_count: int) -> bool:
    return header_count > 1


def table_preamble_rows(preamble_count: int) -> bool:
    return preamble_count > 0


def table_footnote_rows(footnote_count: int) -> bool:
    return footnote_count > 0


def table_columns_less_than_2(n_cols: int) -> bool:
    return n_cols < 2


def table_columns_more_256(n_cols: int) -> bool:
    return n_cols > 256


def table_lines_less_2(n_rows: int) -> bool:
    return n_rows < 2


def table_lines_more_65k(n_rows: int) -> bool:
    return n_rows > 65000


def table_multiple_tables(sample: ParsedSample) -> tuple[bool, float]:
    """Detect ≥ 1 fully-empty row inside the data span.

    The "data span" is everything after the first non-empty / non-preamble
    row and before any trailing empty/single-cell rows. An empty row inside
    that span suggests a second table follows (Pollock's
    ``file_multitable_*``). Big files only see the head/tail sample so we
    return ``False`` when the gap sentinel is the only candidate.
    """
    if not sample.rows or len(sample.rows) < 4:
        return False, 0.7

    rows = sample.rows
    n = len(rows)

    # Find boundaries.
    start = 0
    while start < n and (
        _row_is_empty(rows[start])
        or len([c for c, _ in rows[start] if c.strip()]) <= 1
    ):
        start += 1
    end = n - 1
    while end > start and (
        _row_is_empty(rows[end])
        or len([c for c, _ in rows[end] if c.strip()]) <= 1
    ):
        end -= 1

    # Helper: is this row immediately adjacent to the head/tail sample-gap
    # marker? clevercsv produces a stray empty row right before/after the
    # sentinel due to newline interaction with the glue, so we ignore those.
    def _is_near_gap(i: int) -> bool:
        for j in (i - 1, i + 1):
            if 0 <= j < n and SAMPLE_GAP_TOKEN in _row_text(rows[j]):
                return True
        return False

    saw_empty = False
    for idx in range(start, end):
        if _row_is_empty(rows[idx]):
            text = _row_text(rows[idx])
            if SAMPLE_GAP_TOKEN in text:
                continue
            if _is_near_gap(idx):
                continue
            saw_empty = True
            break

    # On sampled (head/tail) reads we can't see the middle of the file, so
    # any "blank in data span" is more likely a sampling artefact than a
    # real second-table boundary. Demote confidence accordingly.
    return saw_empty, 0.5 if sample.sampled else 0.85


def jagged_rows_count(sample: ParsedSample) -> tuple[int, float]:
    if not sample.rows:
        return 0, 0.0
    counts = [len(r) for r in sample.rows]
    mode = Counter(counts).most_common(1)[0][0]
    return sum(1 for c in counts if c != mode), 0.9 if not sample.sampled else 0.6


def _delim_lists(sample: ParsedSample) -> dict[str, list[str]]:
    """Re-derive the per-row delimiter / quote / record-delimiter values.

    ``clevercsv`` doesn't expose the per-row values directly; we infer
    them from the raw text by splitting on the dominant record delimiter.
    """
    text = sample.raw_text
    rec_delim = _record_delim_dominant(text)
    raw_lines = text.split(rec_delim) if rec_delim else [text]
    field_delim = sample.field_delimiter or ","
    quote = sample.quote_char or '"'

    per_row_n_fields: list[int] = []
    per_row_record_delim: list[str] = []
    per_row_field_delim: list[str] = []
    per_row_quotation: list[str] = []
    per_row_escape: list[str] = []

    for line in raw_lines:
        if not line:
            continue
        if SAMPLE_GAP_TOKEN in line:
            continue
        per_row_n_fields.append(line.count(field_delim) + 1)
        per_row_record_delim.append(rec_delim)
        per_row_field_delim.append(field_delim)
        per_row_quotation.append(quote if quote and quote in line else "")
        # No reliable per-row escape detection — best-effort: mark presence.
        per_row_escape.append(sample.escape_char or "")

    return {
        "n_fields": per_row_n_fields,
        "record_delimiter": per_row_record_delim,
        "field_delimiter": per_row_field_delim,
        "quotation": per_row_quotation,
        "escape": per_row_escape,
    }


def _record_delim_dominant(text: str) -> str:
    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    cr_only = text.count("\r") - crlf
    if crlf >= lf_only and crlf >= cr_only:
        return "\r\n"
    if lf_only >= cr_only:
        return "\n"
    return "\r"


def _row_inconsistent(values: list[str]) -> bool:
    distinct = {v for v in values if v != ""}
    return len(distinct) > 1


def row_inconsistencies(sample: ParsedSample) -> dict[str, bool]:
    """Return all five ``row_inconsistent_*`` flags in one pass."""
    lists = _delim_lists(sample)
    return {
        "row_inconsistent_n_delimiter": len(set(lists["n_fields"])) > 1
            if lists["n_fields"] else False,
        "row_inconsistent_record_delimiter": _row_inconsistent(lists["record_delimiter"]),
        "row_inconsistent_field_delimiter": _row_inconsistent(lists["field_delimiter"]),
        "row_inconsistent_quotation": False,  # see below
        "row_inconsistent_escape": _row_inconsistent(lists["escape"]),
    }


def has_comment_lines(sample: ParsedSample) -> bool:
    """Lines starting with ``#``, ``//``, or ``;`` (excluding the gap sentinel)."""
    for line in sample.raw_text.splitlines():
        stripped = line.lstrip()
        if not stripped:
            continue
        if SAMPLE_GAP_TOKEN in line:
            continue
        if stripped.startswith(_COMMENT_PREFIXES):
            return True
    return False


def line_art_row_present(sample: ParsedSample) -> bool:
    for line in sample.raw_text.splitlines():
        if _LINE_ART_RE.match(line):
            return True
    return False


def aggregated_row_present(sample: ParsedSample) -> bool:
    """First non-empty cell matches an aggregate keyword, others numeric."""
    if not sample.rows:
        return False
    for row in sample.rows:
        cells = [c for c, _ in row]
        if not cells:
            continue
        first = cells[0].strip().lower()
        if not first:
            continue
        if any(kw == first or first.startswith(kw + " ") for kw in _AGGREGATE_KEYWORDS):
            # require at least one numeric-looking remainder
            remainder = cells[1:]
            num_count = 0
            for c in remainder:
                cs = c.strip().replace(",", "").replace("$", "").replace("€", "").replace("%", "")
                if not cs:
                    continue
                try:
                    float(cs)
                    num_count += 1
                except ValueError:
                    pass
            if num_count >= 1:
                return True
    return False
