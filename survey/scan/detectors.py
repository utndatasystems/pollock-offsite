"""Line-level pollution detectors for ``python -m survey scan``.

Each detector returns ``list[int]`` of 1-based line numbers (referring to
positions in the file's raw text) where the pollution was observed. An
empty list means "not flagged".

Design notes:
- We bias for **precision** (low false positives). When in doubt, do not
  flag.
- We re-use ``survey.detect.parser.parse_csv_sample`` for encoding/dialect
  detection and row tokenization (clevercsv with ``return_quoted=True``).
- Line numbers refer to the **raw text after sample-gap glue is stripped**;
  that is, line N in the output corresponds to N counting from 1 over the
  decoded text. For sampled big files this still maps cleanly to the head;
  the tail is offset by the gap and we deliberately do not try to reverse
  the offset (caller is informed via the ``sampled`` flag).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from survey.detect import io_utils
from survey.detect.parser import SAMPLE_GAP_TOKEN, ParsedSample, parse_csv_sample


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_LONG_FIELD_CHARS = 2048
DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB

# Comment markers detected at the very start of a (lstripped) line.
_LINE_COMMENT_PREFIXES_STRICT = ("#", "//", "/*")
# A leading "--" is special-cased because it is also a common null token
# when used standalone; see ``detect_comments``.
_LINE_COMMENT_PREFIX_DASHDASH = "--"


def _is_comment_line(line: str) -> bool:
    """True iff the lstripped line starts with a whole-line comment marker.

    Matches ``#``, ``//``, ``/*``, or ``--`` followed by a space or tab.
    The space/tab requirement on ``--`` keeps the standalone ``--`` null
    token from being misclassified as a comment.

    Used by the 4 detectors that need to *skip* commented rows. The
    comment detector itself reuses this and then applies an extra
    "non-whitespace content after the marker" check before flagging,
    so blank-ish ``--<space>`` lines aren't reported as real comments.
    """
    s = line.lstrip()
    if not s:
        return False
    if s.startswith(_LINE_COMMENT_PREFIXES_STRICT):
        return True
    if (
        s.startswith(_LINE_COMMENT_PREFIX_DASHDASH)
        and len(s) > 2
        and s[2] in " \t"
    ):
        return True
    return False

# Tokens treated as null-value markers. Lower-cased for comparison.
#
# Deliberately diverges from ``survey.detect.cells._KNOWN_NULL_TOKENS``:
#   - Drops "na"  — collides with country code ISO-2 "NA" (Namibia).
#   - Drops "-"   — collides with category labels and numeric ranges.
#   - Adds "unknown", "nul" — common in real-world cleaning scripts.
# Both detectors flag the same broad pollution but with different
# precision/recall trade-offs; this list is tuned for line-level scan
# precision.
NULL_TOKENS = (
    "n/a",
    "null",
    "nil",
    "nan",
    "none",
    "missing",
    "n.a.",
    "no data",
    "sans objet",
    "unknown",
    "nul",
    "?",
    "--",
)
EMPTY_NULL_TOKEN = ""

# Mojibake regex: characters that almost always indicate cp1252 bytes
# decoded as UTF-8 (e.g., "Ã©" for "é", "â€™" for "'", etc.). Curated to
# avoid flagging legitimate text in languages that use these patterns.
_MOJIBAKE_PATTERNS = re.compile(
    r"(Ã[©¨¤¶¼\u0081-\u009F]|â€[™œ\"\u009d˜]|Â[°§©®¶·¢£¥¦\u00a0])"
)

# Candidates for the mixed-delimiter detector.
_DELIM_CANDIDATES = (",", ";", "\t", "|")
# European-decimal-comma pattern: a comma sandwiched between digits is a
# decimal separator, NOT a field delimiter. Used by detect_mixed_delimiter
# to avoid false positives on locale-formatted numeric files.
_EU_DECIMAL_COMMA_RE = re.compile(r"\d,\d")

# At least this many data rows before computing modal column count.
_MIN_DATA_ROWS_FOR_MODE = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class ScanContext:
    """Bundle of per-file state shared by detectors.

    The ``_row_starts`` and ``_header_indices`` slots are populated lazily
    via ``row_starts(ctx)`` / ``header_indices(ctx)`` so multiple detectors
    can share the result without recomputing it.
    """

    sample: ParsedSample
    raw_lines: list[str]            # text split on universal newlines, 1-based via [i-1]
    raw_text: str                   # full sample text (BOM-stripped)
    raw_bytes: bytes                # original bytes (for encoding diagnostics)
    long_field_chars: int
    _row_starts: list[int] | None = field(default=None, repr=False)
    _header_indices: list[int] | None = field(default=None, repr=False)


def row_starts(ctx: ScanContext) -> list[int]:
    """Memoized accessor for the per-row line-number mapping."""
    if ctx._row_starts is None:
        ctx._row_starts = _row_starts_at_line(ctx.sample, ctx.raw_text, ctx.raw_lines)
    return ctx._row_starts


def header_indices(ctx: ScanContext) -> list[int]:
    """Memoized accessor for the detected header-row indices."""
    if ctx._header_indices is None:
        ctx._header_indices = _detect_header_indices(ctx, row_starts(ctx))
    return ctx._header_indices


def _build_raw_lines(text: str) -> list[str]:
    """Split text into lines preserving 1-based line indexing.

    Universal newline split: handles \\n, \\r\\n, \\r equally so that
    line numbers match what a user would see in an editor.
    """
    return text.splitlines()


def _is_gap_line(line: str) -> bool:
    return SAMPLE_GAP_TOKEN in line


def _normalize_null(cell: str) -> str | None:
    """Return a normalized null-token form, or None if not a null token."""
    s = (cell or "").strip()
    if s == "":
        return EMPTY_NULL_TOKEN
    low = s.lower()
    if low in NULL_TOKENS:
        return low
    return None


def _mask_quoted(line: str, quote: str) -> str:
    """Replace characters inside quoted regions with spaces.

    Preserves line length; characters inside quoted regions, including
    escaped doubled-quotes, are blanked. The opening/closing quote
    characters themselves stay in place. The result is safe to use with
    ``str.split(delim)`` / ``str.count(delim)`` to count delimiters that
    are NOT inside cells.

    This is a *per-line* approximation: a quoted field that spans multiple
    raw lines won't be tracked across the line boundary. That's
    acceptable for ``detect_mixed_delimiter``, which already operates
    line-by-line and is gated by file-level plausibility checks.
    """
    if not quote or quote not in line:
        return line
    out: list[str] = []
    in_q = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == quote:
            if in_q and i + 1 < n and line[i + 1] == quote:
                # Doubled-quote escape: stay inside quoted region.
                out.append("  ")
                i += 2
                continue
            in_q = not in_q
            out.append(ch)  # keep quote char itself
            i += 1
            continue
        if in_q:
            out.append(" ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _row_starts_at_line(
    sample: ParsedSample, raw_text: str, raw_lines: list[str]
) -> list[int]:
    """Map each parsed-row index to the 1-based starting line in the raw text.

    Walks ``raw_text`` character-by-character with a small CSV state
    machine that mirrors clevercsv's parsing rules:

    - Inside a quoted field, a doubled quote (``""``) is an escaped quote
      and does NOT toggle quote state.
    - Inside a quoted field, embedded newlines extend the row.
    - Outside a quoted field, ``\\n`` / ``\\r\\n`` / ``\\r`` ends the row.

    The previous implementation just counted quote chars per line and
    flipped state on odd parity — that's wrong whenever a single line
    contains an even number of unescaped quotes plus an odd number of
    doubled-quote escapes, and it also gets confused by quote chars
    appearing in unquoted cells (which clevercsv treats as literals).

    Returns a list aligned with ``sample.rows``; entries that can't be
    mapped (e.g., we ran past the end) are marked with ``-1``.
    """
    starts: list[int] = []
    n_rows = len(sample.rows)
    if n_rows == 0:
        return starts

    quote = sample.quote_char or '"'
    delim = sample.field_delimiter or ","

    in_quotes = False
    at_field_start = True   # next char begins a fresh cell
    line_no = 1
    pending_row_start = 1
    rows_seen = 0
    n = len(raw_text)
    i = 0

    while i < n and rows_seen < n_rows:
        ch = raw_text[i]

        if not in_quotes:
            # Are we at the very first character of a row? Record its line.
            if at_field_start and i == 0:
                starts.append(line_no)
                rows_seen += 1
                pending_row_start = -1  # already recorded
                at_field_start = False
            elif pending_row_start > 0:
                # We crossed a real row boundary; record the line where the
                # next non-empty position begins. Empty lines between rows
                # produce empty rows in the parser too, so we record this
                # line regardless of content.
                starts.append(line_no)
                rows_seen += 1
                pending_row_start = -1
                at_field_start = False
                if rows_seen >= n_rows:
                    break

            if quote and ch == quote and at_field_start:
                # Quote at the start of a cell opens a quoted field.
                in_quotes = True
                at_field_start = False
                i += 1
                continue

            if ch == delim:
                at_field_start = True
                i += 1
                continue

            if ch == "\r":
                # Handle CRLF as one record terminator; bare \r as Mac classic.
                if i + 1 < n and raw_text[i + 1] == "\n":
                    i += 2
                else:
                    i += 1
                line_no += 1
                at_field_start = True
                pending_row_start = line_no
                continue
            if ch == "\n":
                line_no += 1
                at_field_start = True
                pending_row_start = line_no
                i += 1
                continue

            at_field_start = False
            i += 1
            continue

        # Inside a quoted field.
        if quote and ch == quote:
            if i + 1 < n and raw_text[i + 1] == quote:
                # Doubled quote = escaped literal; stay in quotes.
                i += 2
                continue
            in_quotes = False
            i += 1
            continue

        # Track newlines inside quoted fields so line_no stays accurate.
        if ch == "\r":
            if i + 1 < n and raw_text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            line_no += 1
            continue
        if ch == "\n":
            line_no += 1
            i += 1
            continue

        i += 1

    # If we never recorded the very first row (input started in quotes,
    # parser produced 0 rows, etc.), fall back gracefully.
    while len(starts) < n_rows:
        starts.append(-1)

    # Validation: any start beyond raw_lines is invalid.
    max_line = len(raw_lines)
    for idx in range(len(starts)):
        if starts[idx] > max_line:
            starts[idx] = -1

    return starts


# ---------------------------------------------------------------------------
# Detector 1: comments
# ---------------------------------------------------------------------------


def detect_comments(ctx: ScanContext) -> list[int]:
    """Detect commented lines and intra-row / end-of-line comments.

    Strategy:
    - **Whole-line comments**: a row is flagged when (a) its raw line —
      after lstrip — starts with ``#``, ``//``, ``/*``, or ``-- ``, AND
      either (b1) the line precedes the detected header (a preamble
      comment with prose-style commas should still flag), OR (b2) the
      parsed row is **sparse** — ≤2 non-empty cells. The sparseness
      guard prevents flagging dense data rows like
      ``/* in C,used by gcc,common`` whose first cell coincidentally
      starts with a comment marker but the row is structured data.
    - **Inline / intra-row comments**: a parsed cell whose stripped value
      starts with ``# ``, ``// ``, ``/*``, or ``-- `` and the row is
      sparse *relative to the file's modal column count*. We require
      ``modal_cols > 2`` before treating any 2-cell row as sparse — a
      file whose data shape is truly 2 columns has no "sparse" rows.

    Skip:
    - Sample-gap sentinel lines.
    - Lines that fall inside a quoted multiline value (approximated by
      "this raw line isn't a row-start").
    """
    hits: set[int] = set()
    starts = row_starts(ctx)
    row_starts_set = {s for s in starts if s > 0}

    # Build a line_no -> row_idx map so the whole-line scan can consult
    # the parsed row's sparseness without re-scanning.
    line_to_row: dict[int, int] = {}
    for row_idx, line_no in enumerate(starts):
        if line_no > 0 and line_no not in line_to_row:
            line_to_row[line_no] = row_idx

    # Modal column count over data-shaped rows. A file with modal_cols ==
    # 2 is *not* a candidate for inline comment detection (any row in
    # such a file is "sparse" by construction).
    col_counts = [
        len(ctx.sample.rows[i])
        for i in range(len(ctx.sample.rows))
        if i < len(starts) and starts[i] > 0
    ]
    modal_cols = Counter(col_counts).most_common(1)[0][0] if col_counts else 0

    # The line number where the detected header starts. Lines before this
    # are preamble; we relax the sparseness gate there because real
    # preamble comments (``# Source: Smith et al. 2004, Cambridge MA``)
    # contain prose with commas and parse as dense rows.
    hdr_idx = header_indices(ctx)
    header_first_line = (
        starts[hdr_idx[0]]
        if hdr_idx and hdr_idx[0] < len(starts) and starts[hdr_idx[0]] > 0
        else None
    )

    def _row_is_sparse(row_idx: int) -> bool:
        """Sparse = <=2 non-empty cells. Used to guard whole-line and
        inline comment classification against dense data rows."""
        if row_idx >= len(ctx.sample.rows):
            return True
        row = ctx.sample.rows[row_idx]
        return sum(1 for c, _ in row if c.strip()) <= 2

    # ---- whole-line comments --------------------------------------------
    for line_no, line in enumerate(ctx.raw_lines, start=1):
        if _is_gap_line(line):
            continue
        stripped = line.lstrip()
        if not stripped:
            continue
        # Skip lines that aren't row-starts (mid-quote multiline content).
        # If parser produced no row mapping we fall back to scanning all
        # lines — the parser failure itself signals other pollutions.
        if row_starts_set and line_no not in row_starts_set:
            continue

        is_strict_marker = stripped.startswith(_LINE_COMMENT_PREFIXES_STRICT)
        is_dashdash_comment = (
            stripped.startswith(_LINE_COMMENT_PREFIX_DASHDASH)
            and len(stripped) > 2
            and stripped[2] in " \t"
            and stripped[2:].strip()
        )
        if not (is_strict_marker or is_dashdash_comment):
            continue

        # Sparseness guard with pre-header leniency: dense rows in the
        # data span are likely structured data with a comment-marker
        # leading char, but the same shape *before* the header is a real
        # preamble comment whose prose contains commas.
        is_preamble = header_first_line is not None and line_no < header_first_line
        row_idx = line_to_row.get(line_no)
        if (
            not is_preamble
            and row_idx is not None
            and not _row_is_sparse(row_idx)
        ):
            continue
        hits.add(line_no)

    # ---- inline / intra-row comments -----------------------------------
    # Only fire when the file's modal shape has >2 columns — a true 2-col
    # file (e.g., "name,note") has no rows that are "sparse" relative to
    # its data shape.
    if modal_cols > 2:
        for row_idx, row in enumerate(ctx.sample.rows):
            if row_idx >= len(starts):
                break
            line_no = starts[row_idx]
            if line_no <= 0:
                continue
            if line_no in hits:
                continue  # already flagged as whole-line comment
            line_text = ctx.raw_lines[line_no - 1] if line_no - 1 < len(ctx.raw_lines) else ""
            if _is_gap_line(line_text):
                continue
            if not _row_is_sparse(row_idx):
                continue
            for cell, _is_quoted in row:
                s = (cell or "").lstrip()
                if not s:
                    continue
                if SAMPLE_GAP_TOKEN in s:
                    continue
                if (
                    s.startswith("# ")
                    or s.startswith("// ")
                    or s.startswith("/*")
                    or (s.startswith("-- ") and len(s) > 3)
                ):
                    hits.add(line_no)
                    break

    return sorted(hits)


# ---------------------------------------------------------------------------
# Detector 2: extremely long fields
# ---------------------------------------------------------------------------


def detect_long_fields(ctx: ScanContext) -> list[int]:
    """Cells whose character length exceeds ``ctx.long_field_chars``."""
    threshold = ctx.long_field_chars
    starts = row_starts(ctx)
    hits: set[int] = set()
    for row_idx, row in enumerate(ctx.sample.rows):
        if row_idx >= len(starts):
            break
        line_no = starts[row_idx]
        if line_no <= 0:
            continue
        for cell, _is_quoted in row:
            if len(cell) > threshold:
                hits.add(line_no)
                break
    return sorted(hits)


# ---------------------------------------------------------------------------
# Detector 3: variable column count
# ---------------------------------------------------------------------------


def _is_preamble_or_footnote_row(row) -> bool:
    """A row that's empty or has ≤1 non-empty cell."""
    non_empty = [c for c, _ in row if c.strip()]
    return len(non_empty) <= 1


_HEADER_DATA_TYPES = frozenset(
    {"TYPE_INT", "TYPE_FLOAT", "TYPE_DATE", "TYPE_TIME", "TYPE_BOOLEAN", "TYPE_PRICE"}
)


def _detect_header_indices(ctx: ScanContext, starts: list[int]) -> list[int]:
    """Return the list of row indices the header heuristic considers headers.

    Mirrors the gate used by ``detect_header_mismatch``: skip preamble,
    take up to 3 leading rows where every cell is a string type (no
    int/float/date/etc.) and ≥60% are TYPE_STRING. Returns ``[]`` when no
    header is detectable.

    Shared so that ``detect_variable_columns`` can avoid double-flagging
    header rows that ``detect_header_mismatch`` already reports.
    """
    from pollock.data_types import parse_cell  # lazy import

    rows = ctx.sample.rows
    if not rows:
        return []

    # Skip leading preamble: empty rows, single-cell rows, comment lines.
    non_preamble = 0
    for idx, row in enumerate(rows):
        if not row:
            continue
        non_empty = [c for c, _ in row if c.strip()]
        if len(non_empty) == 0:
            continue
        if len(non_empty) <= 1 and len(row) > 1:
            continue
        if idx < len(starts):
            line_no = starts[idx]
            if (
                line_no > 0
                and line_no - 1 < len(ctx.raw_lines)
                and _is_comment_line(ctx.raw_lines[line_no - 1])
            ):
                continue
        non_preamble = idx
        break

    found: list[int] = []
    for idx in range(non_preamble, min(non_preamble + 3, len(rows))):
        row = rows[idx]
        non_empty_types = [parse_cell(c) for c, _ in row if c.strip()]
        if not non_empty_types:
            break
        if any(t in _HEADER_DATA_TYPES for t in non_empty_types):
            break
        string_share = sum(1 for t in non_empty_types if t == "TYPE_STRING") / len(non_empty_types)
        if string_share < 0.6:
            break
        found.append(idx)
    return found


def detect_variable_columns(ctx: ScanContext) -> list[int]:
    """Rows whose column count differs from the modal data-row count.

    Skip:
    - Empty / single-cell rows (treated as preamble or footnote).
    - Rows starting with a comment marker.
    - Rows containing the gap sentinel.
    - **Detected header rows** — these are reported by
      ``detect_header_mismatch`` instead, so we don't double-flag.
    - Files with fewer than ``_MIN_DATA_ROWS_FOR_MODE`` qualifying rows.
    """
    rows = ctx.sample.rows
    starts = row_starts(ctx)
    if not rows:
        return []

    header_idx_set = set(header_indices(ctx))

    # Build qualifying row indices and their column counts.
    quals: list[tuple[int, int]] = []  # (row_idx, n_cols)
    for row_idx, row in enumerate(rows):
        if row_idx >= len(starts):
            break
        if row_idx in header_idx_set:
            continue
        line_no = starts[row_idx]
        if line_no <= 0:
            continue
        line_text = ctx.raw_lines[line_no - 1] if line_no - 1 < len(ctx.raw_lines) else ""
        if _is_gap_line(line_text):
            continue
        if _is_comment_line(line_text):
            continue
        if _is_preamble_or_footnote_row(row):
            continue
        quals.append((row_idx, len(row)))

    if len(quals) < _MIN_DATA_ROWS_FOR_MODE:
        return []

    counts = [c for _, c in quals]
    mode = Counter(counts).most_common(1)[0][0]

    hits: set[int] = set()
    for row_idx, n_cols in quals:
        if n_cols == mode:
            continue
        line_no = starts[row_idx]
        if line_no > 0:
            hits.add(line_no)
    return sorted(hits)


# ---------------------------------------------------------------------------
# Detector 4: mixed delimiter
# ---------------------------------------------------------------------------


def detect_mixed_delimiter(ctx: ScanContext) -> list[int]:
    """Rows where two candidate delimiters both appear at suspicious rates.

    Two-stage:
    1. **File-level gate**: at least 2 of {``,`` ``;`` ``\\t`` ``|``} must
       each split ≥70% of non-empty lines into ≥2 columns with a dominant
       column count. (Mirrors ``dialect.ambiguous_delimiter``.)
    2. **Per-row check**: among the plausible delimiters, flag rows where
       the secondary delimiter appears at ≥40% the count of the primary
       (and at least 1 occurrence).
    """
    quote = ctx.sample.quote_char or '"'
    # Filter out gap and comment lines for plausibility scoring. Mask
    # quoted regions so delimiter-like characters inside cells (e.g., a
    # comma inside `"smith, jr."`) don't poison the count.
    clean_lines: list[tuple[int, str]] = []  # (line_no, masked_line)
    for line_no, line in enumerate(ctx.raw_lines, start=1):
        if _is_gap_line(line):
            continue
        if not line.strip():
            continue
        if _is_comment_line(line):
            continue
        clean_lines.append((line_no, _mask_quoted(line, quote)))

    if len(clean_lines) < 5:
        return []

    # Two-pass scoring:
    #
    # Pass 1 (`_count_raw`): score each candidate delimiter using its
    # raw count (no EU-decimal mask). The mask was originally added to
    # suppress FPs on `;`-delimited European-locale files where commas
    # are decimal separators inside cells — but it's only safe to apply
    # *after* we've decided which delimiter is primary. Applied
    # unconditionally, it neutralizes commas in genuine comma-delimited
    # numeric files (e.g. ``1,2,3,4``) and blinds the per-row check.
    #
    # Pass 2 (`_count_with_eu_mask`): once we know the primary, count
    # secondary occurrences with the EU-decimal mask applied to comma
    # *only* when comma is NOT primary. That way ``1,5;2,5`` (semicolon
    # primary) treats `1,5` as one cell (no comma noise) but ``1,5,3``
    # (comma primary) still sees three commas.
    def _count_raw(line: str, d: str) -> int:
        return line.count(d)

    def _count_with_eu_mask(line: str, d: str, primary: str) -> int:
        c = line.count(d)
        if d == "," and primary != ",":
            c -= len(_EU_DECIMAL_COMMA_RE.findall(line))
        return max(c, 0)

    # Two-part plausibility:
    #   (a) absolute: modal frequency must be ≥ 0.9. A real delimiter is
    #       consistent on essentially every data row; prose-with-commas
    #       under a different primary delimiter typically scores 0.5–0.8
    #       and would otherwise sneak in as a false runner-up.
    #   (b) relative: candidates whose modal frequency is meaningfully
    #       below the best candidate's are dropped. A clear winner means
    #       there is no real ambiguity.
    candidate_stats: list[tuple[str, float, int]] = []
    for d in _DELIM_CANDIDATES:
        counts = [_count_raw(line, d) + 1 for _, line in clean_lines]
        mc, freq = Counter(counts).most_common(1)[0]
        modal_freq = freq / len(counts)
        if mc >= 2 and modal_freq >= 0.9:
            candidate_stats.append((d, modal_freq, mc))

    if len(candidate_stats) < 2:
        return []

    best_freq = max(f for _, f, _ in candidate_stats)
    plausible_stats = [(d, mc) for d, f, mc in candidate_stats if best_freq - f <= 0.1]

    if len(plausible_stats) < 2:
        return []

    # Column-count dominance: a candidate producing far fewer columns than
    # the leader is likely a character appearing inside cell values, not a
    # real delimiter (e.g., one comma in a "lat, lon" coordinate field).
    max_cols = max(mc for _, mc in plausible_stats)
    plausible = [d for d, mc in plausible_stats if mc >= max_cols / 2]

    if len(plausible) < 2:
        return []

    # Primary = sniffer's pick if it's in the plausible set, else the
    # highest-coverage candidate by raw count.
    primary = ctx.sample.field_delimiter if ctx.sample.field_delimiter in plausible else plausible[0]
    secondaries = [d for d in plausible if d != primary]

    hits: set[int] = set()
    for line_no, line in clean_lines:
        p_count = _count_with_eu_mask(line, primary, primary)
        if p_count == 0:
            for s in secondaries:
                if _count_with_eu_mask(line, s, primary) > 0:
                    hits.add(line_no)
                    break
            continue
        for s in secondaries:
            s_count = _count_with_eu_mask(line, s, primary)
            if s_count >= 1 and s_count >= p_count * 0.4:
                hits.add(line_no)
                break
    return sorted(hits)


# ---------------------------------------------------------------------------
# Detector 5: header mismatch
# ---------------------------------------------------------------------------


def detect_header_mismatch(ctx: ScanContext) -> list[int]:
    """Header line(s) whose column count differs from modal data-row count.

    Only fires when:
    - A header is detectable (≥60% string cells, no numeric/date cells in
      the header row).
    - There are ≥``_MIN_DATA_ROWS_FOR_MODE`` qualifying data rows.

    Reports the line number(s) of the header row(s).
    """
    rows = ctx.sample.rows
    starts = row_starts(ctx)
    if not rows or len(rows) < _MIN_DATA_ROWS_FOR_MODE + 1:
        return []

    hdr_idx = header_indices(ctx)
    if not hdr_idx:
        return []

    # Modal data-row column count (excluding header rows + preamble + footnote).
    data_counts: list[int] = []
    for idx in range(hdr_idx[-1] + 1, len(rows)):
        row = rows[idx]
        if _is_preamble_or_footnote_row(row):
            continue
        if idx >= len(starts):
            break
        line_no = starts[idx]
        if line_no <= 0:
            continue
        line_text = ctx.raw_lines[line_no - 1] if line_no - 1 < len(ctx.raw_lines) else ""
        if _is_gap_line(line_text):
            continue
        if _is_comment_line(line_text):
            continue
        data_counts.append(len(row))

    if len(data_counts) < _MIN_DATA_ROWS_FOR_MODE:
        return []

    mode = Counter(data_counts).most_common(1)[0][0]

    hits: list[int] = []
    for idx in hdr_idx:
        if idx < len(starts):
            line_no = starts[idx]
            if line_no <= 0:
                continue
            header_cols = len(rows[idx])
            if header_cols != mode:
                hits.append(line_no)
    return sorted(set(hits))


# ---------------------------------------------------------------------------
# Detector 6: unquoted multiline values
# ---------------------------------------------------------------------------


def detect_unquoted_multiline(ctx: ScanContext) -> list[int]:
    """Detect unquoted newlines inside CSV cells.

    Two signals:

    1. **Direct (rarely fires)**: a parsed cell containing ``\\n`` /
       ``\\r`` whose ``is_quoted=False``. clevercsv almost never
       produces this — it uses doubled-quote escapes and newline-in-cell
       only when the field is quoted.

    2. **Orphan-fragment pattern**: clevercsv splits an unquoted bare
       newline into two adjacent rows: a normal-width prefix row plus a
       *single-cell suffix* (the orphan). We flag a row that:

       - has exactly **1 cell** — a true split-by-newline suffix has no
         delimiters in it; jagged data rows that are merely missing a
         trailing column parse as ≥2 cells, so we don't catch them.
       - is sandwiched between two modal-width rows.
       - is not preamble / footnote / comment / detected header.

       Stricter than "≤ modal//2+1" — the looser version flagged real
       jagged-data rows. The 1-cell rule keeps recall on the canonical
       split case while avoiding the FP.

    Reports the line number of the row at which the split begins.
    """
    rows = ctx.sample.rows
    starts = row_starts(ctx)
    hits: set[int] = set()

    # Signal 1: parsed cell with embedded newline + is_quoted=False.
    for row_idx, row in enumerate(rows):
        if row_idx >= len(starts):
            break
        line_no = starts[row_idx]
        if line_no <= 0:
            continue
        for cell, is_quoted in row:
            if is_quoted:
                continue
            if "\n" in cell or "\r" in cell:
                hits.add(line_no)
                break

    # Signal 2: orphan-fragment pattern.
    # NOTE: the file may also contain legitimate quoted multiline cells —
    # those are independent of an unquoted-newline split, so we do NOT
    # gate on their presence.
    if rows and starts and len(rows) >= _MIN_DATA_ROWS_FOR_MODE + 1:
        # Modal column count over data-shaped rows.
        col_counts: list[int] = []
        for row_idx, row in enumerate(rows):
            if row_idx >= len(starts):
                break
            line_no = starts[row_idx]
            if line_no <= 0:
                continue
            line_text = ctx.raw_lines[line_no - 1] if line_no - 1 < len(ctx.raw_lines) else ""
            if _is_gap_line(line_text) or _is_comment_line(line_text):
                continue
            if _is_preamble_or_footnote_row(row):
                continue
            col_counts.append(len(row))

        if col_counts:
            modal = Counter(col_counts).most_common(1)[0][0]
            header_idx_set = set(header_indices(ctx))
            if modal >= 3:  # detector needs a meaningful structure
                # An orphan suffix is exactly 1 cell wide and sandwiched
                # between two modal-width rows. This precise shape
                # distinguishes a true split-by-unquoted-newline from a
                # merely jagged row missing a trailing column.
                for row_idx in range(1, len(rows) - 1):
                    if row_idx >= len(starts):
                        break
                    if row_idx in header_idx_set:
                        continue
                    line_no = starts[row_idx]
                    if line_no <= 0:
                        continue
                    line_text = ctx.raw_lines[line_no - 1] if line_no - 1 < len(ctx.raw_lines) else ""
                    if _is_gap_line(line_text) or _is_comment_line(line_text):
                        continue
                    row = rows[row_idx]
                    if len(row) != 1:
                        continue
                    # Both neighbors must be at modal width.
                    prev_row = rows[row_idx - 1]
                    next_row = rows[row_idx + 1]
                    if len(prev_row) == modal and len(next_row) == modal:
                        hits.add(line_no)

    return sorted(hits)


# ---------------------------------------------------------------------------
# Detector 7: encoding issues
# ---------------------------------------------------------------------------


def detect_encoding_issues(ctx: ScanContext) -> list[int]:
    """Lines with invalid UTF-8, UTF-16 content, or mojibake patterns.

    Strategy:
    - **UTF-16 detection** (path 0): if the raw bytes start with a UTF-16
      or UTF-32 BOM, OR contain a high ratio of NUL bytes
      (``>= ~25%``, the signature of UTF-16 LE/BE 7-bit-ASCII content
      where every other byte is 0x00), flag line 1. UTF-16 LE bodies
      coincidentally pass strict UTF-8 decode (NUL is a valid UTF-8
      codepoint), so without an explicit check the issue is invisible.
    - **Invalid UTF-8** (path 1): if strict UTF-8 fails, walk the bytes
      and translate decode errors to line numbers.
    - **Mojibake** (path 2): if UTF-8 succeeds, scan decoded text for
      curated cp1252-as-UTF-8 patterns.
    """
    raw = ctx.raw_bytes
    if not raw:
        return []

    hits: set[int] = set()

    # Path 0: explicit UTF-16/UTF-32 detection.
    UTF16_BOMS = (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff", b"\xff\xfe", b"\xfe\xff")
    is_utf16_bom = raw.startswith(UTF16_BOMS) and not raw.startswith(b"\xef\xbb\xbf")
    # Heuristic for UTF-16 without BOM: ASCII content in UTF-16 LE/BE has
    # ~50% NUL bytes. We use a conservative >=25% threshold over the
    # first 4 KB to avoid flagging plain binary files (which usually have
    # mixed bytes, not the alternating-NUL pattern).
    head = raw[:4096]
    nul_ratio = head.count(b"\x00") / len(head) if head else 0.0
    looks_utf16_no_bom = nul_ratio >= 0.25

    if is_utf16_bom or looks_utf16_no_bom:
        # Whole-file flag at line 1; we can't reliably line-map UTF-16
        # against the parser's UTF-8 view of raw_text.
        return [1]

    # Path 1: strip UTF-8 BOM if any, then try strict UTF-8.
    bom_len = 3 if raw.startswith(b"\xef\xbb\xbf") else 0
    body = raw[bom_len:]

    try:
        body.decode("utf-8", errors="strict")
        utf8_clean = True
    except UnicodeDecodeError:
        utf8_clean = False

    if not utf8_clean:
        # Walk bytes; map each error offset to a line number using \n counts.
        # We use ``errors="replace"`` then find replacement chars to locate
        # the bad spots. Safer: use ``codecs.iterdecode``-style scan via
        # incremental decoder.
        import codecs

        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        line_no = 1
        i = 0
        n = len(body)
        # Track the byte → line mapping by counting newlines as we advance.
        while i < n:
            byte = body[i:i + 1]
            try:
                decoded = decoder.decode(byte, final=(i == n - 1))
                # Count newlines we just consumed.
                line_no += decoded.count("\n")
                i += 1
            except UnicodeDecodeError:
                hits.add(line_no)
                # Skip past the bad byte and keep going, resetting decoder.
                decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
                # Find next newline byte to advance past current bad spot
                # without spamming dozens of errors per line.
                next_nl = body.find(b"\n", i)
                if next_nl < 0:
                    break
                i = next_nl + 1
                line_no += 1
        return sorted(hits)

    # Path 2: UTF-8 was clean — scan decoded text for mojibake patterns.
    text = ctx.raw_text  # already BOM-stripped, gap-glued for big files
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _is_gap_line(line):
            continue
        if _MOJIBAKE_PATTERNS.search(line):
            hits.add(line_no)
    return sorted(hits)


# ---------------------------------------------------------------------------
# Detector 8: null representation mismatch
# ---------------------------------------------------------------------------


def detect_null_mismatch(ctx: ScanContext) -> list[int]:
    """Files using ≥2 distinct null tokens.

    Reports the **first occurrence** of each distinct token (so we can
    localize the pollution without flooding output).

    Two distinct non-empty tokens, OR one non-empty token + presence of
    truly empty cells, both qualify. (Pure all-empty files are not
    flagged.)
    """
    starts = row_starts(ctx)
    first_seen: dict[str, int] = {}

    for row_idx, row in enumerate(ctx.sample.rows):
        if row_idx >= len(starts):
            break
        line_no = starts[row_idx]
        if line_no <= 0:
            continue
        for cell, _is_quoted in row:
            tok = _normalize_null(cell)
            if tok is None:
                continue
            if tok not in first_seen:
                first_seen[tok] = line_no

    non_empty_tokens = [t for t in first_seen if t != EMPTY_NULL_TOKEN]
    has_empty = EMPTY_NULL_TOKEN in first_seen

    if len(non_empty_tokens) >= 2 or (len(non_empty_tokens) >= 1 and has_empty):
        # Return the first-occurrence line number per distinct token,
        # sorted and deduplicated.
        return sorted(set(first_seen.values()))
    return []


# ---------------------------------------------------------------------------
# Top-level dispatch
# ---------------------------------------------------------------------------


POLLUTION_NAMES = (
    "comments",
    "long_fields",
    "variable_columns",
    "mixed_delimiter",
    "header_mismatch",
    "unquoted_multiline",
    "encoding_issues",
    "null_mismatch",
)


def _read_raw_bytes(path: Path, max_bytes: int) -> bytes:
    """Read up to ``max_bytes`` of uncompressed bytes for encoding scan."""
    return io_utils.read_all_bytes(path, cap=max_bytes)


def scan_file(
    path: Path,
    *,
    long_field_chars: int = DEFAULT_LONG_FIELD_CHARS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    no_sampling: bool = False,
) -> tuple[dict[str, list[int]], bool]:
    """Run all detectors on a single file.

    Returns ``(results, sampled)`` where ``results`` is a dict
    ``{pollution_name: [line_numbers]}`` (empty lists kept; the runner
    filters them) and ``sampled`` is True when the parser used head/tail
    sampling. When ``no_sampling=True``, the big-file sampler is forced
    off so the whole file is scanned.

    Exceptions raised by ``parse_csv_sample`` (or by individual
    detectors) propagate to the caller; ``run_scan`` catches them per
    file so a single bad file never aborts the whole run.
    """
    sample = parse_csv_sample(path, force_no_sampling=no_sampling)
    raw_text = sample.raw_text or ""
    raw_lines = _build_raw_lines(raw_text)
    raw_bytes = _read_raw_bytes(path, max_bytes)

    ctx = ScanContext(
        sample=sample,
        raw_lines=raw_lines,
        raw_text=raw_text,
        raw_bytes=raw_bytes,
        long_field_chars=long_field_chars,
    )

    results = {
        "comments": detect_comments(ctx),
        "long_fields": detect_long_fields(ctx),
        "variable_columns": detect_variable_columns(ctx),
        "mixed_delimiter": detect_mixed_delimiter(ctx),
        "header_mismatch": detect_header_mismatch(ctx),
        "unquoted_multiline": detect_unquoted_multiline(ctx),
        "encoding_issues": detect_encoding_issues(ctx),
        "null_mismatch": detect_null_mismatch(ctx),
    }
    return results, sample.sampled
