"""
Engine B - Quote & escape pathologies.

Round 2: kept the high-impact attacks (rare quote chars, EOF unclosed,
header/data ambiguity, long-span unterminated, quote-storm), trimmed
single-cell duds (cell_f1 > 0.99 across all 4 SuTs), and added sharpened
variants that scale damage by acting on many rows at once.
"""
from __future__ import annotations

from . import polluters_stdlib as pl
from .CSVFile import CSVFile
from .polluters_extended import RawBytePolluter


# ---------------------------------------------------------------------------
# Byte-level helpers
# ---------------------------------------------------------------------------

def _split_lines(b: bytes) -> list[bytes]:
    return b.split(b"\r\n")


def _join_lines(lines: list[bytes]) -> bytes:
    return b"\r\n".join(lines)


# ---------------------------------------------------------------------------
# Long-span unterminated-quote attacks (proven winners)
# ---------------------------------------------------------------------------

def _unterminated_row5(b: bytes, file: CSVFile) -> bytes:
    lines = _split_lines(b)
    if len(lines) > 5:
        idx = lines[5].find(b",")
        if idx >= 0:
            lines[5] = lines[5][: idx + 1] + b'"' + lines[5][idx + 1 :]
    return _join_lines(lines)


def _open5_close50(b: bytes, file: CSVFile) -> bytes:
    lines = _split_lines(b)
    if len(lines) > 50:
        idx_open = lines[5].find(b",")
        if idx_open >= 0:
            lines[5] = lines[5][: idx_open + 1] + b'"' + lines[5][idx_open + 1 :]
        idx_close = lines[50].rfind(b",")
        if idx_close >= 0:
            lines[50] = lines[50][:idx_close] + b'"' + lines[50][idx_close:]
    return _join_lines(lines)


def _open5_close80(b: bytes, file: CSVFile) -> bytes:
    lines = _split_lines(b)
    if len(lines) > 80:
        idx_open = lines[5].find(b",")
        if idx_open >= 0:
            lines[5] = lines[5][: idx_open + 1] + b'"' + lines[5][idx_open + 1 :]
        idx_close = lines[80].rfind(b",")
        if idx_close >= 0:
            lines[80] = lines[80][:idx_close] + b'"' + lines[80][idx_close:]
    return _join_lines(lines)


def _cascading_unclosed(b: bytes, file: CSVFile) -> bytes:
    lines = _split_lines(b)
    for r in (5, 10, 15):
        if len(lines) > r:
            idx = lines[r].find(b",")
            if idx >= 0:
                lines[r] = lines[r][: idx + 1] + b'"' + lines[r][idx + 1 :]
    return _join_lines(lines)


def _quote_storm(b: bytes, file: CSVFile) -> bytes:
    """Many stray opening quotes scattered. ROUND 2: tighten to every-other-row."""
    lines = _split_lines(b)
    # Hit rows 3,5,7,9,...,49 (a quote on every other data row in first half).
    for r in range(3, 50, 2):
        if len(lines) > r:
            idx = lines[r].find(b",")
            if idx >= 0:
                lines[r] = lines[r][: idx + 1] + b'"' + lines[r][idx + 1 :]
    return _join_lines(lines)


def _ragged_open_quotes(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2: extend pattern to whole file."""
    lines = _split_lines(b)
    for r in (5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70):
        if len(lines) > r:
            idx = lines[r].find(b",")
            if idx >= 0:
                lines[r] = lines[r][: idx + 1] + b'"' + lines[r][idx + 1 :]
    return _join_lines(lines)


def _interlocked_pairs(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 NEW: every 5 rows, open at row N close at row N+3.
    Creates interlocked partial spans."""
    lines = _split_lines(b)
    for start in (5, 12, 19, 26, 33, 40, 47, 54, 61, 68):
        if len(lines) > start + 3:
            idx_o = lines[start].find(b",")
            if idx_o >= 0:
                lines[start] = lines[start][: idx_o + 1] + b'"' + lines[start][idx_o + 1 :]
            idx_c = lines[start + 3].rfind(b",")
            if idx_c >= 0:
                lines[start + 3] = lines[start + 3][:idx_c] + b'"' + lines[start + 3][idx_c:]
    return _join_lines(lines)


# ---------------------------------------------------------------------------
# Header/data quote ambiguity (proven winners — pandas scored 0.56)
# ---------------------------------------------------------------------------

def _open_header_close_data(b: bytes, file: CSVFile) -> bytes:
    lines = _split_lines(b)
    if len(lines) > 1:
        lines[0] = lines[0] + b'"'
        lines[1] = lines[1] + b'"'
    return _join_lines(lines)


def _open_header_close_row5(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 NEW: open quote on header, close on row 5 — eats first 5 records."""
    lines = _split_lines(b)
    if len(lines) > 5:
        lines[0] = lines[0] + b'"'
        idx_close = lines[5].rfind(b",")
        if idx_close >= 0:
            lines[5] = lines[5][:idx_close] + b'"' + lines[5][idx_close:]
    return _join_lines(lines)


def _quote_in_header_only(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 NEW: stray opening quote inside header cell, no close."""
    lines = _split_lines(b)
    if len(lines):
        idx = lines[0].find(b",")
        if idx >= 0:
            lines[0] = lines[0][: idx + 1] + b'"' + lines[0][idx + 1 :]
    return _join_lines(lines)


# ---------------------------------------------------------------------------
# Rare quote characters (proven winners — multiple SuTs to 0.0)
# ---------------------------------------------------------------------------

def quote_backtick(file: CSVFile) -> None:
    pl.changeQuotationChar(file, target_char="`")
    file.filename = "quote_char_backtick.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def quote_pipe(file: CSVFile) -> None:
    pl.changeQuotationChar(file, target_char="|")
    file.filename = "quote_char_pipe.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def quote_tilde(file: CSVFile) -> None:
    pl.changeQuotationChar(file, target_char="~")
    file.filename = "quote_char_tilde.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def quote_section_sign(file: CSVFile) -> None:
    file.encoding = "utf-8"
    file.xml.getroot().attrib["encoding"] = "utf-8"
    pl.changeQuotationChar(file, target_char="\u00a7")
    file.filename = "quote_char_section.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def quote_caret(file: CSVFile) -> None:
    """ROUND 2 NEW: caret as quote char."""
    pl.changeQuotationChar(file, target_char="^")
    file.filename = "quote_char_caret.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def quote_dollar(file: CSVFile) -> None:
    """ROUND 2 NEW: dollar sign as quote char (collides with $-prices in source)."""
    pl.changeQuotationChar(file, target_char="$")
    file.filename = "quote_char_dollar.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def quote_hash(file: CSVFile) -> None:
    """ROUND 2 NEW: # as quote char (collides with comment conventions)."""
    pl.changeQuotationChar(file, target_char="#")
    file.filename = "quote_char_hash.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def quote_apostrophe(file: CSVFile) -> None:
    """ROUND 2 NEW: ' as quote char — collides with embedded apostrophes in source."""
    pl.changeQuotationChar(file, target_char="'")
    file.filename = "quote_char_apostrophe.csv"
    file.xml.getroot().attrib["filename"] = file.filename


# ---------------------------------------------------------------------------
# EOF / trailing-quote attacks (proven winner — pandas to 0.0)
# ---------------------------------------------------------------------------

def _eof_unclosed_quote_ws(b: bytes, file: CSVFile) -> bytes:
    return b + b'"   '


def _eof_open_long(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 NEW: open quote at row 70's start, then several CRLF/junk before EOF."""
    lines = _split_lines(b)
    if len(lines) > 70:
        idx = lines[70].find(b",")
        if idx >= 0:
            lines[70] = lines[70][: idx + 1] + b'"' + lines[70][idx + 1 :]
    # No close anywhere through to EOF.
    return _join_lines(lines)


def _eof_quote_then_data(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 NEW: append `,"` plus more content, no terminator."""
    return b + b'"unfinished cell with content but no close'


# ---------------------------------------------------------------------------
# Multi-row mass attacks (round 2 sharpening)
# ---------------------------------------------------------------------------

def _every_field_triple_quoted_many_rows(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 SHARPENED: triple-quote-wrap fields on many rows."""
    lines = _split_lines(b)
    for r in (10, 15, 20, 25, 30, 35, 40, 45, 50, 55):
        if len(lines) > r:
            parts = lines[r].split(b",")
            wrapped = [b'"""' + p.strip(b'"') + b'"""' for p in parts]
            lines[r] = b",".join(wrapped)
    return _join_lines(lines)


def _close_then_garbage_many_rows(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 SHARPENED: 'foo'GARBAGE in many rows."""
    lines = _split_lines(b)
    for r in (10, 12, 14, 16, 18, 20, 22, 24, 26, 28):
        if len(lines) > r:
            parts = lines[r].split(b",")
            new_parts = []
            for p in parts:
                stripped = p.strip(b'"')[:6]
                new_parts.append(b'"' + stripped + b'"X')
            lines[r] = b",".join(new_parts)
    return _join_lines(lines)


def _empty_quoted_vs_empty_many_rows(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 SHARPENED: ,"",, on many rows."""
    lines = _split_lines(b)
    for r in (10, 12, 14, 16, 18, 20, 22, 24):
        if len(lines) > r:
            parts = lines[r].split(b",")
            if len(parts) >= 8:
                parts[3] = b'""'
                parts[4] = b''
                parts[5] = b'""'
                parts[6] = b''
                lines[r] = b",".join(parts)
    return _join_lines(lines)


def _quote_inside_unquoted_many_rows(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 SHARPENED: foo"bar in field 5 across many rows."""
    lines = _split_lines(b)
    for r in (8, 11, 14, 17, 20, 23, 26, 29):
        if len(lines) > r:
            parts = lines[r].split(b",", 6)
            if len(parts) >= 7:
                parts[5] = b'foo"bar'
                lines[r] = b",".join(parts)
    return _join_lines(lines)


def _doubled_quote_chain_many_rows(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2 SHARPENED: 'a""b""c""d""e""f""g' in many rows."""
    lines = _split_lines(b)
    for r in (10, 14, 18, 22, 26, 30, 34, 38):
        if len(lines) > r:
            parts = lines[r].split(b",", 6)
            if len(parts) >= 7:
                parts[6] = b'"a""b""c""d""e""f""g""h"'
                lines[r] = b",".join(parts)
    return _join_lines(lines)


# ---------------------------------------------------------------------------
# Mixed escape / declared-mismatch (modest winners, kept)
# ---------------------------------------------------------------------------

def _mixed_escapes_doubled_and_backslash(b: bytes, file: CSVFile) -> bytes:
    lines = _split_lines(b)
    if len(lines) > 12:
        parts11 = lines[11].split(b",", 6)
        if len(parts11) >= 7:
            parts11[6] = b'"she said ""hi"" today."'
            lines[11] = b",".join(parts11)
        parts12 = lines[12].split(b",", 6)
        if len(parts12) >= 7:
            parts12[6] = b'"she said \\"bye\\" today."'
            lines[12] = b",".join(parts12)
    return _join_lines(lines)


def _declare_backslash_use_doubled(file: CSVFile) -> None:
    pl.changeEscapeCharacter(file, target_escape="\\")
    file.filename = "quote_decl_backslash_use_doubled.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def _esc_before_delim_combined(b: bytes, file: CSVFile) -> bytes:
    """Declare escape=\\ AND inject \\, in body across many rows.
    ROUND 2: sharpen by hitting many rows."""
    pl.changeEscapeCharacter(file, target_escape="\\")
    file.filename = "quote_esc_before_delim.csv"
    file.xml.getroot().attrib["filename"] = file.filename
    # NB: this is a RawBytePolluter mutator, so we already operate on bytes;
    # the file param is just for context (we cannot write XML changes here
    # because parameters/clean were already rendered before this is called).
    # The trick: we can't change the JSON now — but the params were generated
    # from the XML state at apply() time. So we declared escape=\\ in the
    # function above (via pl.changeEscapeCharacter) BEFORE the byte rendering.
    # We do the byte injection here.
    lines = _split_lines(b)
    for r in (8, 12, 16, 20, 24):
        if len(lines) > r:
            parts = lines[r].split(b",", 6)
            if len(parts) >= 7:
                parts[5] = b'foo\\,extra'
                lines[r] = b",".join(parts)
    return _join_lines(lines)


def _unquoted_with_quoted_comma(b: bytes, file: CSVFile) -> bytes:
    """ROUND 2: hit many rows."""
    lines = _split_lines(b)
    for r in (10, 15, 20, 25, 30, 35, 40):
        if len(lines) > r:
            parts = lines[r].split(b",", 6)
            if len(parts) >= 7:
                parts[5] = b'foo","bar'
                lines[r] = b",".join(parts)
    return _join_lines(lines)


# ---------------------------------------------------------------------------
# POLLUTIONS registry — round 2
# ---------------------------------------------------------------------------

POLLUTIONS = [
    # ---- Long-span unterminated (winners) ----
    ("quote_unterminated_row5.csv",
     RawBytePolluter("unterm5", _unterminated_row5,
                     "Stray opening quote on data row 5, never closed."), {}),

    ("quote_unterminated_open5_close50.csv",
     RawBytePolluter("open5_close50", _open5_close50,
                     "Open row 5, close row 50 - 45 records eaten."), {}),

    ("quote_open5_close80.csv",
     RawBytePolluter("open5_close80", _open5_close80,
                     "Open row 5, close row 80 - eats nearly the whole file."), {}),

    ("quote_cascading_unclosed.csv",
     RawBytePolluter("cascading", _cascading_unclosed,
                     "Stray opens at rows 5, 10, 15."), {}),

    ("quote_storm.csv",
     RawBytePolluter("storm", _quote_storm,
                     "Stray quote on every other data row, rows 3..49."), {}),

    ("quote_ragged_opens.csv",
     RawBytePolluter("ragged", _ragged_open_quotes,
                     "Stray opens at irregular intervals across whole file."), {}),

    ("quote_interlocked_pairs.csv",
     RawBytePolluter("interlocked", _interlocked_pairs,
                     "Open/close pairs every 7 rows - interlocked partial spans."), {}),

    # ---- Header/data ambiguity ----
    ("quote_open_header_close_data.csv",
     RawBytePolluter("hdr_data", _open_header_close_data,
                     "Quote opened on header line, closed on data row 1."), {}),

    ("quote_open_header_close_row5.csv",
     RawBytePolluter("hdr_row5", _open_header_close_row5,
                     "Open on header, close on row 5 - eats 5 records."), {}),

    ("quote_in_header_only.csv",
     RawBytePolluter("hdr_only", _quote_in_header_only,
                     "Stray opening quote inside header cell, no close."), {}),

    # ---- Rare quote characters ----
    ("quote_char_backtick.csv", quote_backtick, {}),
    ("quote_char_pipe.csv", quote_pipe, {}),
    ("quote_char_tilde.csv", quote_tilde, {}),
    ("quote_char_section.csv", quote_section_sign, {}),
    ("quote_char_caret.csv", quote_caret, {}),
    ("quote_char_dollar.csv", quote_dollar, {}),
    ("quote_char_hash.csv", quote_hash, {}),
    ("quote_char_apostrophe.csv", quote_apostrophe, {}),

    # ---- EOF/trailing ----
    ("quote_eof_unclosed_ws.csv",
     RawBytePolluter("eof_ws", _eof_unclosed_quote_ws,
                     'Trailing " plus whitespace at EOF, no close.'), {}),

    ("quote_eof_open_long.csv",
     RawBytePolluter("eof_open_long", _eof_open_long,
                     "Open quote in row 70, no close before EOF."), {}),

    ("quote_eof_quote_then_data.csv",
     RawBytePolluter("eof_qd", _eof_quote_then_data,
                     "Append unfinished quoted cell with content at EOF."), {}),

    # ---- Multi-row mass attacks (sharpened from round 1) ----
    ("quote_every_field_triple_many.csv",
     RawBytePolluter("triple_many", _every_field_triple_quoted_many_rows,
                     "Triple-quote-wrap fields on 10 rows."), {}),

    ("quote_close_then_garbage_many.csv",
     RawBytePolluter("garbage_many", _close_then_garbage_many_rows,
                     "'foo'X close-then-garbage in 10 rows."), {}),

    ("quote_empty_quoted_many.csv",
     RawBytePolluter("empty_many", _empty_quoted_vs_empty_many_rows,
                     'Mix of "" and bare empty across 8 rows.'), {}),

    ("quote_inside_unquoted_many.csv",
     RawBytePolluter("inq_many", _quote_inside_unquoted_many_rows,
                     'foo"bar in field 5 across 8 rows.'), {}),

    ("quote_doubled_chain_many.csv",
     RawBytePolluter("dchain_many", _doubled_quote_chain_many_rows,
                     'Chain of "" pairs across 8 rows.'), {}),

    # ---- Modest winners kept ----
    ("quote_mixed_escapes_doubled_and_backslash.csv",
     RawBytePolluter("mixed_escapes", _mixed_escapes_doubled_and_backslash,
                     'Row 11 uses "", row 12 uses \\" for embedded quotes.'), {}),

    ("quote_decl_backslash_use_doubled.csv", _declare_backslash_use_doubled, {}),

    ("quote_esc_before_delim.csv",
     RawBytePolluter("esc_bd", _esc_before_delim_combined,
                     "escape=\\ declared, body uses foo\\,extra in 5 rows."), {}),

    ("quote_unquoted_with_quoted_comma.csv",
     RawBytePolluter("unq_qc", _unquoted_with_quoted_comma,
                     'foo","bar (looks like adjacent close quotes) in 7 rows.'), {}),
]
