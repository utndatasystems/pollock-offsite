"""Dialect-level detectors.

Includes the four ``table_not_*`` flags (delimiter / quote / escape /
record-delim is not the standard one) and the new ``ambiguous_delimiter``,
``mixed_quote_styles``, ``sniffer_low_confidence`` candidates.
"""

from __future__ import annotations

import re
from collections import Counter

from clevercsv.cparser_util import parse_string
from clevercsv.dialect import SimpleDialect

from .parser import ParsedSample


_CANDIDATE_DELIMS = (",", ";", "\t", "|")
_AMBIGUITY_TOLERANCE = 1  # column-count variance treated as "same"
_DELIM_AMBIGUITY_MIN_ROWS = 5


def table_not_comma_delimiter(sample: ParsedSample) -> bool:
    return sample.field_delimiter != ","


def table_not_double_quote(sample: ParsedSample) -> bool:
    # Empty quotechar = no quoting at all → also "not double quote".
    return sample.quote_char != '"'


def table_not_escape_quote(sample: ParsedSample) -> bool:
    """Pollock convention: 'escape via doubled quote' is the norm.

    SimpleDialect represents this with ``escapechar == ''``.
    """
    return sample.escape_char not in ("", '"')


def table_not_crlf_delimiter(sample: ParsedSample, record_delimiter: str) -> bool:
    return record_delimiter != "\r\n"


def sniffer_low_confidence(sample: ParsedSample, threshold: float = 0.7) -> tuple[bool, float]:
    """Composite confidence beyond the binary clevercsv signal.

    We can't read clevercsv's internal score, so we approximate: a sniffed
    dialect that produces wildly variable row lengths or yields only one
    column on a multi-line file is treated as low-confidence.
    """
    if sample.sniffer_dialect is None:
        return True, 0.0

    if not sample.rows:
        return True, 0.0

    col_counts = [len(r) for r in sample.rows]
    if max(col_counts) <= 1 and len(col_counts) > 3:
        return True, 0.2

    mode = Counter(col_counts).most_common(1)[0][0]
    matching = sum(1 for c in col_counts if c == mode)
    ratio = matching / len(col_counts) if col_counts else 0.0
    return ratio < threshold, ratio


def ambiguous_delimiter(sample: ParsedSample) -> bool:
    """≥2 candidate delimiters yield approximately the same column count."""
    text = sample.raw_text
    lines = [ln for ln in text.splitlines() if ln.strip()][:50]
    if len(lines) < _DELIM_AMBIGUITY_MIN_ROWS:
        return False

    # Two-part plausibility (kept in lockstep with
    # ``survey.scan.detectors.detect_mixed_delimiter``):
    #   (a) absolute: modal frequency ≥ 0.9 — a real delimiter is
    #       consistent on essentially every data row.
    #   (b) relative: candidates whose modal frequency is more than 0.1
    #       below the best candidate's are dropped — a clear winner
    #       means the file is not actually ambiguous.
    candidate_stats: list[tuple[str, float, int]] = []
    for d in _CANDIDATE_DELIMS:
        try:
            counts = [len(line.split(d)) for line in lines]
        except Exception:
            continue
        if not counts:
            continue
        most_common_count, freq = Counter(counts).most_common(1)[0]
        modal_freq = freq / len(counts)
        if most_common_count >= 2 and modal_freq >= 0.9:
            candidate_stats.append((d, modal_freq, most_common_count))

    if len(candidate_stats) < 2:
        return False

    best_freq = max(f for _, f, _ in candidate_stats)
    plausible_stats = [(d, mc) for d, f, mc in candidate_stats if best_freq - f <= 0.1]

    if len(plausible_stats) < 2:
        return False

    max_cols = max(mc for _, mc in plausible_stats)
    plausible = [d for d, mc in plausible_stats if mc >= max_cols / 2]
    return len(plausible) >= 2


def mixed_quote_styles(sample: ParsedSample) -> bool:
    """Flag when both ``"`` and ``'`` appear as wrapping characters in cells.

    Scans ``sample.raw_text`` directly: ``parse_string`` strips the chosen
    quote char from each cell, so a post-parse view can never show double
    quotes when ``quote_char == '"'``. We look for fields whose boundaries
    are followed/preceded by the field delimiter (or line/text edge) and
    whose first/last char is ``"`` or ``'``.
    """
    text = sample.raw_text
    if not text:
        return False
    delim = sample.field_delimiter or ","
    if delim in ('"', "'"):
        return False

    delim_re = re.escape(delim)
    field_re = re.compile(
        rf'(?:^|(?<={delim_re})|(?<=\n))'
        rf'(?:(?P<dq>"[^"\n]*")|(?P<sq>\'[^\'\n]*\'))'
        rf'(?={delim_re}|\n|$)',
        re.MULTILINE,
    )

    total_fields = 0
    for line in text.splitlines():
        if line.strip():
            total_fields += line.count(delim) + 1
    if total_fields == 0:
        return False

    double = single = 0
    for m in field_re.finditer(text):
        if m.group("dq"):
            double += 1
        else:
            single += 1
    return (double / total_fields) > 0.05 and (single / total_fields) > 0.05


def dialect_unparseable(sample: ParsedSample) -> bool:
    """clevercsv returns delimiter ``" "`` for many fixed-width files.

    We treat that case (plus missing dialect) as ``dialect_unparseable``
    so downstream consumers don't act on garbage values.
    """
    if sample.sniffer_dialect is None:
        return True
    return sample.field_delimiter == " "
