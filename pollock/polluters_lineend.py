"""
Engine D: Line-ending and record-delimiter chaos.

Pollutions that exploit parser disagreement on what constitutes a record
boundary: mixed line endings within one file, embedded delimiters in quoted
fields, NUL bytes, form feeds, trailing whitespace, missing/extra terminators,
unicode line separators.

Most attacks are byte-level (RawBytePolluter). The clean+parameters output is
written via the standard XML pipeline, so the parser sees the polluted bytes
but the evaluator scores against the honest reference. Parameters declare the
honest record_delimiter (\\r\\n) — the attacks land hardest when the parser is
not warned about the inconsistency.
"""
from __future__ import annotations

import random

from .polluters_extended import RawBytePolluter


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _split_records(b: bytes) -> list[bytes]:
    """Split on \\r\\n and return list of record bodies (no trailing empty)."""
    parts = b.split(b"\r\n")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    return parts


# ---------------------------------------------------------------------------
# 1. Mixed CRLF / LF / CR cycling
# ---------------------------------------------------------------------------

def _mixed_crlf_lf_cr_cycling(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    endings = [b"\r\n", b"\n", b"\r"]
    out = []
    for i, row in enumerate(rows):
        out.append(row)
        out.append(endings[i % 3])
    return b"".join(out)


# ---------------------------------------------------------------------------
# 2. Random per-line endings (deterministic seed)
# ---------------------------------------------------------------------------

def _random_endings(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    rng = random.Random(0xD)
    endings = [b"\r\n", b"\n", b"\r"]
    out = []
    for row in rows:
        out.append(row)
        out.append(rng.choice(endings))
    return b"".join(out)


# ---------------------------------------------------------------------------
# 3. Last 5 rows use different ending (LF) than the first 80 (CRLF)
# ---------------------------------------------------------------------------

def _tail_changes_ending(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    out = []
    n = len(rows)
    for i, row in enumerate(rows):
        out.append(row)
        out.append(b"\n" if i >= n - 5 else b"\r\n")
    return b"".join(out)


# ---------------------------------------------------------------------------
# 4. CR-only line endings throughout (Mac classic) — params still say CRLF
# ---------------------------------------------------------------------------

def _all_cr_only(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\r")


# ---------------------------------------------------------------------------
# 5. LF-only throughout — params still declare CRLF
# ---------------------------------------------------------------------------

def _all_lf_only(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\n")


# ---------------------------------------------------------------------------
# 6. CRLF declared but stray CR in middle of a long cell
# ---------------------------------------------------------------------------

def _stray_cr_in_cell(b: bytes, _file) -> bytes:
    rows = b.split(b"\r\n")
    # row 3 (index 3 incl. header) tends to have a long ProductDescription cell.
    # Insert a CR in the middle of it.
    if len(rows) > 4:
        target = rows[3]
        mid = len(target) // 2
        rows[3] = target[:mid] + b"\r" + target[mid:]
    return b"\r\n".join(rows)


# ---------------------------------------------------------------------------
# 7. Embedded NUL bytes at random positions
# ---------------------------------------------------------------------------

def _scattered_nuls(b: bytes, _file) -> bytes:
    rng = random.Random(0xD7)
    arr = bytearray(b)
    # 20 NULs in the middle of the file
    safe_zone = (len(arr) // 10, len(arr) - 100)
    for _ in range(20):
        pos = rng.randint(*safe_zone)
        arr.insert(pos, 0x00)
    return bytes(arr)


# ---------------------------------------------------------------------------
# 8. NUL inside a quoted cell
# ---------------------------------------------------------------------------

def _nul_in_quoted_cell(b: bytes, _file) -> bytes:
    # Find first quoted cell (between two ") and inject NUL in the middle.
    first = b.find(b'"')
    if first < 0:
        return b
    second = b.find(b'"', first + 1)
    if second < 0:
        return b
    mid = (first + second) // 2
    return b[:mid] + b"\x00\x00\x00" + b[mid:]


# ---------------------------------------------------------------------------
# 9. Form feed (\x0c) declared as record delimiter
# ---------------------------------------------------------------------------

def _ff_record_delim(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\x0c")


# ---------------------------------------------------------------------------
# 10. Vertical tab (\x0b) as record delimiter
# ---------------------------------------------------------------------------

def _vt_record_delim(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\x0b")


# ---------------------------------------------------------------------------
# 11. Form feed mid-record (not on row boundary)
# ---------------------------------------------------------------------------

def _ff_mid_record(b: bytes, _file) -> bytes:
    rows = b.split(b"\r\n")
    # Inject FF mid-cell on row 3
    if len(rows) > 4:
        target = rows[3]
        mid = len(target) // 2
        rows[3] = target[:mid] + b"\x0c" + target[mid:]
    return b"\r\n".join(rows)


# ---------------------------------------------------------------------------
# 12. Trailing whitespace before \r\n on every line
# ---------------------------------------------------------------------------

def _trailing_spaces(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"   \r\n")


# ---------------------------------------------------------------------------
# 13. Trailing tab before \r\n
# ---------------------------------------------------------------------------

def _trailing_tabs(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\t\r\n")


# ---------------------------------------------------------------------------
# 14. Final newline missing (no trailing terminator at EOF)
# ---------------------------------------------------------------------------

def _no_trailing_newline(b: bytes, _file) -> bytes:
    if b.endswith(b"\r\n"):
        return b[:-2]
    return b


# ---------------------------------------------------------------------------
# 15. Doubled trailing newline (\r\n\r\n)
# ---------------------------------------------------------------------------

def _doubled_trailing_newline(b: bytes, _file) -> bytes:
    if b.endswith(b"\r\n"):
        return b + b"\r\n"
    return b + b"\r\n\r\n"


# ---------------------------------------------------------------------------
# 16. Triple trailing newline (\r\n\r\n\r\n)
# ---------------------------------------------------------------------------

def _triple_trailing_newline(b: bytes, _file) -> bytes:
    if b.endswith(b"\r\n"):
        return b + b"\r\n\r\n"
    return b + b"\r\n\r\n\r\n"


# ---------------------------------------------------------------------------
# 17. Single-quote quotechar but a cell contains a literal " followed by \n
#    The clean output uses a single-quote quote (changeQuotationChar).
#    But we go byte-level: rewrite all " to ' AND inject a stray " inside
#    a long cell, followed by a newline. RFC violation: parser should
#    interpret " literally, but many parsers will treat it as a quote
#    starting context and consume the newline.
# ---------------------------------------------------------------------------

def _stray_quote_then_newline(b: bytes, _file) -> bytes:
    out = b.replace(b'"', b"'")
    # Now inject `"foo\nbar"` in a row body
    rows = out.split(b"\r\n")
    if len(rows) > 5:
        target = rows[4]
        mid = len(target) // 2
        rows[4] = target[:mid] + b'"foo\nbar"' + target[mid:]
    return b"\r\n".join(rows)


# ---------------------------------------------------------------------------
# 18. Quoted-field newlines spanning many lines (RFC-legal)
#    Replace one cell's value with a multi-line quoted block.
# ---------------------------------------------------------------------------

def _multiline_quoted_field(b: bytes, _file) -> bytes:
    # Inject a block in row 3 (after header) — replace a known cell value.
    block = b'"line1\r\nline2\r\nline3\r\nline4\r\nline5"'
    rows = b.split(b"\r\n")
    if len(rows) > 4:
        # row 3 (index 3): replace the URL cell's value (between the last two ")
        # Simpler: append a new column-like field by replacing the empty trailing
        # cell. For robustness, just substitute first occurrence of the URL
        # cell pattern.
        target = rows[3]
        # find the second-to-last comma
        commas = [i for i, c in enumerate(target) if c == ord(',')]
        if len(commas) >= 2:
            cut = commas[-1]
            rows[3] = target[:cut + 1] + block + target[cut + 1:]
    return b"\r\n".join(rows)


# ---------------------------------------------------------------------------
# 19. Quoted-field with mixed \r\n vs \n inside two adjacent quoted blocks
# ---------------------------------------------------------------------------

def _mixed_inner_eol_quoted(b: bytes, _file) -> bytes:
    block_a = b'"alpha\r\nbeta"'
    block_b = b'"gamma\ndelta"'
    rows = b.split(b"\r\n")
    if len(rows) > 6:
        for ridx, blk in [(3, block_a), (4, block_b)]:
            target = rows[ridx]
            commas = [i for i, c in enumerate(target) if c == ord(',')]
            if len(commas) >= 2:
                cut = commas[-1]
                rows[ridx] = target[:cut + 1] + blk + target[cut + 1:]
    return b"\r\n".join(rows)


# ---------------------------------------------------------------------------
# 20. Multi-character record delimiter \r\n\r\n (blank-line separator)
# ---------------------------------------------------------------------------

def _blank_line_separator(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\r\n\r\n")


# ---------------------------------------------------------------------------
# 21. CRLF mostly, one row ends only \n
# ---------------------------------------------------------------------------

def _one_lf_in_crlf(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    out = []
    for i, row in enumerate(rows):
        out.append(row)
        out.append(b"\n" if i == 5 else b"\r\n")
    return b"".join(out)


# ---------------------------------------------------------------------------
# 22. CRLF mostly, one row ends only \r
# ---------------------------------------------------------------------------

def _one_cr_in_crlf(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    out = []
    for i, row in enumerate(rows):
        out.append(row)
        out.append(b"\r" if i == 5 else b"\r\n")
    return b"".join(out)


# ---------------------------------------------------------------------------
# 23. EOF mid-cell (last row truncated)
# ---------------------------------------------------------------------------

def _eof_mid_cell(b: bytes, _file) -> bytes:
    rows = b.split(b"\r\n")
    if rows and not rows[-1]:
        rows = rows[:-1]
    if len(rows) > 1:
        last = rows[-1]
        # truncate to half — unclosed quote possible.
        rows[-1] = last[: len(last) // 2]
    return b"\r\n".join(rows)


# ---------------------------------------------------------------------------
# 24. Bytes 0x80-0x9F (C1 control codes) sprinkled near line endings
# ---------------------------------------------------------------------------

def _c1_controls_at_eol(b: bytes, _file) -> bytes:
    rng = random.Random(0xC1)
    rows = _split_records(b)
    out = []
    c1 = list(range(0x80, 0xA0))
    for row in rows:
        out.append(row)
        out.append(bytes([rng.choice(c1)]))
        out.append(b"\r\n")
    return b"".join(out)


# ---------------------------------------------------------------------------
# 25. Half the file uses CRLF, the other half uses Unicode LS (U+2028)
# ---------------------------------------------------------------------------

def _half_ls_separator(b: bytes, _file) -> bytes:
    # Note: file is expected to be UTF-8. U+2028 is 0xE2 0x80 0xA8.
    rows = _split_records(b)
    out = []
    half = len(rows) // 2
    for i, row in enumerate(rows):
        out.append(row)
        if i < half:
            out.append(b"\r\n")
        else:
            out.append(b"\xe2\x80\xa8")
    return b"".join(out)


# ---------------------------------------------------------------------------
# Round 2 — sharpened variants chosen after seeing round 1 results.
# These are filled in after running.
# ---------------------------------------------------------------------------

# Sharpened: every other line gets two trailing spaces
def _alternating_trailing_spaces(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    out = []
    for i, row in enumerate(rows):
        if i % 2:
            out.append(row + b"  ")
        else:
            out.append(row)
        out.append(b"\r\n")
    return b"".join(out)


# Sharpened: NUL right after every CRLF (start-of-line NUL)
def _nul_at_line_start(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\r\n\x00")


# Sharpened: bare CR at start of every line (CRLF -> CRCRLF)
def _double_cr_lineend(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\r\r\n")


# Sharpened: LF-LF blank lines mixed in (every 3rd row a blank)
def _blank_every_third(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    out = []
    for i, row in enumerate(rows):
        out.append(row)
        out.append(b"\r\n")
        if i % 3 == 2:
            out.append(b"\r\n")
    return b"".join(out)


# Sharpened: 0x85 (NEL — Unicode Next Line) as record delimiter
def _nel_record_delim(b: bytes, _file) -> bytes:
    # NEL in UTF-8 is 0xC2 0x85
    return b.replace(b"\r\n", b"\xc2\x85")


# Sharpened: PS (U+2029, Paragraph Separator, 0xE2 0x80 0xA9) as delimiter
def _ps_record_delim(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\xe2\x80\xa9")


# Sharpened: sprinkle backspace (\x08) before line endings
def _backspace_before_eol(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\x08\r\n")


# Sharpened: stray quote at the very start of a line (mid-file)
def _stray_quote_line_start(b: bytes, _file) -> bytes:
    rows = b.split(b"\r\n")
    if len(rows) > 10:
        rows[8] = b'"' + rows[8]
    return b"\r\n".join(rows)


# Sharpened: NUL replacing one CRLF in the middle of the file
def _nul_replaces_one_crlf(b: bytes, _file) -> bytes:
    # Replace only the 5th CRLF with a NUL byte.
    # Find positions of CRLF.
    out = bytearray()
    count = 0
    i = 0
    while i < len(b):
        if i + 1 < len(b) and b[i] == 0x0D and b[i + 1] == 0x0A:
            count += 1
            if count == 5:
                out.append(0x00)
            else:
                out.extend(b"\r\n")
            i += 2
        else:
            out.append(b[i])
            i += 1
    return bytes(out)


# Sharpened: mid-cell embedded \r\n inside an unquoted field
def _crlf_in_unquoted_cell(b: bytes, _file) -> bytes:
    rows = b.split(b"\r\n")
    if len(rows) > 4:
        target = rows[3]
        # Find first comma not inside quotes — naive but ok here
        idx = target.find(b',')
        if idx > 0:
            # Inject \r\n right after the first comma — splits the row
            rows[3] = target[: idx + 1] + b"\r\nFAKEHALF" + target[idx + 1:]
    return b"\r\n".join(rows)


# Sharpened: CRLF replaced by \r\n + 0xFE (a single byte that's not CR/LF)
def _byte_after_each_crlf(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\r\n\xfe")


# ---------------------------------------------------------------------------
# Round 2 — additional sharpened variants from round 1 wins.
# ---------------------------------------------------------------------------

# Compound: 0xFE bytes after every CRLF + scattered NULs in cells
def _fe_plus_nuls(b: bytes, _file) -> bytes:
    out = b.replace(b"\r\n", b"\r\n\xfe")
    rng = random.Random(0xFE)
    arr = bytearray(out)
    for _ in range(15):
        pos = rng.randint(len(arr) // 10, len(arr) - 100)
        arr.insert(pos, 0x00)
    return bytes(arr)


# C1 control bytes scattered mid-cell (not at EOL) — many parsers may treat
# 0x85 as line terminator even inside content.
def _c1_mid_cell(b: bytes, _file) -> bytes:
    rng = random.Random(0x85)
    rows = b.split(b"\r\n")
    c1 = list(range(0x80, 0xA0))
    for ridx in range(2, min(len(rows) - 1, 20)):
        target = bytearray(rows[ridx])
        for _ in range(2):
            pos = rng.randint(20, max(20, len(target) - 20))
            target.insert(pos, rng.choice(c1))
        rows[ridx] = bytes(target)
    return b"\r\n".join(rows)


# UTF-8 NEL (0xC2 0x85) inside cells, NOT replacing CRLF — inline only
def _nel_inside_cells(b: bytes, _file) -> bytes:
    rows = b.split(b"\r\n")
    for ridx in range(2, min(len(rows) - 1, 20)):
        target = rows[ridx]
        mid = len(target) // 2
        rows[ridx] = target[:mid] + b"\xc2\x85" + target[mid:]
    return b"\r\n".join(rows)


# Interleave LS / PS / CRLF as record terminators
def _interleave_ls_ps_crlf(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    endings = [b"\r\n", b"\xe2\x80\xa8", b"\xe2\x80\xa9"]
    out = []
    for i, row in enumerate(rows):
        out.append(row)
        out.append(endings[i % 3])
    return b"".join(out)


# Three-byte sequence (0xFE 0xFF 0x00) after each CRLF — looks like a BOM
# fragment plus NUL: parsers that tolerate the FE/FF prefix still get a NUL
def _three_byte_after_crlf(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\r\n\xfe\xff\x00")


# Random C1 controls scattered throughout the body
def _random_c1_throughout(b: bytes, _file) -> bytes:
    rng = random.Random(0xC0)
    arr = bytearray(b)
    for _ in range(40):
        pos = rng.randint(len(arr) // 20, len(arr) - 50)
        arr.insert(pos, rng.randint(0x80, 0x9F))
    return bytes(arr)


# UTF-8 BOM (EF BB BF) injected after each CRLF — many tools strip BOM only
# at file start; mid-stream BOMs leak as garbage characters.
def _bom_after_each_crlf(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\r\n\xef\xbb\xbf")


# Doubled form-feed delimiter (each record terminator is 0x0c 0x0c)
def _double_ff_delim(b: bytes, _file) -> bytes:
    return b.replace(b"\r\n", b"\x0c\x0c")


# CR-only file with one stray LF every 5 rows — compound: parser detects
# CR as terminator, then a lone LF appears in what it thinks is the next row.
def _cr_only_with_stray_lf(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    out = []
    for i, row in enumerate(rows):
        out.append(row)
        if i and i % 5 == 0:
            out.append(b"\r\n")
        else:
            out.append(b"\r")
    return b"".join(out)


# Stray quote before every CRLF in the second half of the file —
# RFC-violating but pushes parser into quote-tracking mode mid-record
def _quote_before_crlf_back_half(b: bytes, _file) -> bytes:
    rows = _split_records(b)
    n = len(rows)
    out = []
    for i, row in enumerate(rows):
        if i >= n // 2:
            out.append(row + b'"')
        else:
            out.append(row)
        out.append(b"\r\n")
    return b"".join(out)


# ---------------------------------------------------------------------------
# POLLUTIONS list
# ---------------------------------------------------------------------------

POLLUTIONS = [
    ("lineend_mixed_crlf_lf_cr_cycle.csv",
     RawBytePolluter("mixed_cycle", _mixed_crlf_lf_cr_cycling,
                     "Cycle CRLF/LF/CR per row"), {}),

    ("lineend_random_per_line.csv",
     RawBytePolluter("random_endings", _random_endings,
                     "Randomly choose CRLF/LF/CR per row"), {}),

    ("lineend_tail5_lf_rest_crlf.csv",
     RawBytePolluter("tail5_lf", _tail_changes_ending,
                     "Last 5 rows use LF, rest CRLF"), {}),

    ("lineend_all_cr_only.csv",
     RawBytePolluter("all_cr", _all_cr_only,
                     "CR-only line endings, params declare CRLF"), {}),

    ("lineend_all_lf_only.csv",
     RawBytePolluter("all_lf", _all_lf_only,
                     "LF-only line endings, params declare CRLF"), {}),

    ("lineend_stray_cr_in_cell.csv",
     RawBytePolluter("stray_cr", _stray_cr_in_cell,
                     "Stray CR mid-record in long cell"), {}),

    ("lineend_scattered_nuls.csv",
     RawBytePolluter("scattered_nuls", _scattered_nuls,
                     "20 NUL bytes randomly throughout file"), {}),

    ("lineend_nul_in_quoted_cell.csv",
     RawBytePolluter("nul_in_quote", _nul_in_quoted_cell,
                     "NUL bytes inside a quoted cell"), {}),

    ("lineend_ff_as_record_delim.csv",
     RawBytePolluter("ff_delim", _ff_record_delim,
                     "Form feed (0x0c) as record delimiter"), {}),

    ("lineend_vt_as_record_delim.csv",
     RawBytePolluter("vt_delim", _vt_record_delim,
                     "Vertical tab (0x0b) as record delimiter"), {}),

    ("lineend_ff_mid_record.csv",
     RawBytePolluter("ff_mid", _ff_mid_record,
                     "Form feed mid-record, not at boundary"), {}),

    ("lineend_trailing_spaces.csv",
     RawBytePolluter("trailing_spaces", _trailing_spaces,
                     "Three trailing spaces before every \\r\\n"), {}),

    ("lineend_trailing_tab.csv",
     RawBytePolluter("trailing_tab", _trailing_tabs,
                     "Trailing tab before every \\r\\n"), {}),

    ("lineend_no_final_newline.csv",
     RawBytePolluter("no_final_nl", _no_trailing_newline,
                     "Final \\r\\n stripped"), {}),

    ("lineend_double_trailing_newline.csv",
     RawBytePolluter("double_eof", _doubled_trailing_newline,
                     "Doubled \\r\\n at EOF"), {}),

    ("lineend_triple_trailing_newline.csv",
     RawBytePolluter("triple_eof", _triple_trailing_newline,
                     "Triple \\r\\n at EOF"), {}),

    ("lineend_stray_quote_with_lf.csv",
     RawBytePolluter("stray_quote_nl", _stray_quote_then_newline,
                     "All quotes single-quoted but stray \" + LF inside cell"), {}),

    ("lineend_multiline_quoted_field.csv",
     RawBytePolluter("multiline_quoted", _multiline_quoted_field,
                     "RFC-legal multiline quoted field"), {}),

    ("lineend_mixed_inner_eol_quoted.csv",
     RawBytePolluter("mixed_inner_eol", _mixed_inner_eol_quoted,
                     "Two quoted blocks: one with CRLF inside, one with LF only"), {}),

    ("lineend_blank_line_separator.csv",
     RawBytePolluter("blank_separator", _blank_line_separator,
                     "Records separated by blank line (\\r\\n\\r\\n)"), {}),

    ("lineend_one_row_lf_in_crlf.csv",
     RawBytePolluter("one_lf", _one_lf_in_crlf,
                     "Most rows CRLF, row 6 ends only \\n"), {}),

    ("lineend_one_row_cr_in_crlf.csv",
     RawBytePolluter("one_cr", _one_cr_in_crlf,
                     "Most rows CRLF, row 6 ends only \\r"), {}),

    ("lineend_eof_mid_cell.csv",
     RawBytePolluter("eof_mid_cell", _eof_mid_cell,
                     "Last row truncated mid-cell"), {}),

    ("lineend_c1_controls_at_eol.csv",
     RawBytePolluter("c1_at_eol", _c1_controls_at_eol,
                     "C1 control byte (0x80-0x9F) before each \\r\\n"), {}),

    ("lineend_half_ls_separator.csv",
     RawBytePolluter("half_ls", _half_ls_separator,
                     "Half CRLF, half U+2028 (Unicode line separator)"), {}),

    # Round 2 sharpened variants.
    ("lineend_alternating_trailing_spaces.csv",
     RawBytePolluter("alt_trail_sp", _alternating_trailing_spaces,
                     "Every 2nd line has 2 trailing spaces"), {}),

    ("lineend_nul_at_line_start.csv",
     RawBytePolluter("nul_at_start", _nul_at_line_start,
                     "NUL byte after every \\r\\n"), {}),

    ("lineend_double_cr_lineend.csv",
     RawBytePolluter("double_cr", _double_cr_lineend,
                     "CRLF -> CRCRLF (extra CR before each LF)"), {}),

    ("lineend_blank_every_third.csv",
     RawBytePolluter("blank_3rd", _blank_every_third,
                     "Blank line after every 3rd record"), {}),

    ("lineend_nel_record_delim.csv",
     RawBytePolluter("nel_delim", _nel_record_delim,
                     "Unicode NEL (U+0085) as record delimiter"), {}),

    ("lineend_ps_record_delim.csv",
     RawBytePolluter("ps_delim", _ps_record_delim,
                     "Unicode PS (U+2029) as record delimiter"), {}),

    ("lineend_backspace_before_eol.csv",
     RawBytePolluter("bs_before_eol", _backspace_before_eol,
                     "Backspace (0x08) before each \\r\\n"), {}),

    ("lineend_stray_quote_line_start.csv",
     RawBytePolluter("stray_q_start", _stray_quote_line_start,
                     "Bare quote at the start of one mid-file row"), {}),

    ("lineend_nul_replaces_crlf.csv",
     RawBytePolluter("nul_replaces_crlf", _nul_replaces_one_crlf,
                     "One CRLF replaced by a NUL byte"), {}),

    ("lineend_crlf_in_unquoted_cell.csv",
     RawBytePolluter("crlf_unquoted_cell", _crlf_in_unquoted_cell,
                     "Stray CRLF inside an unquoted cell"), {}),

    ("lineend_byte_after_each_crlf.csv",
     RawBytePolluter("byte_after_eol", _byte_after_each_crlf,
                     "0xFE byte right after each \\r\\n"), {}),

    # Round 2 — additional sharpened variants from round-1 wins.
    ("lineend_fe_plus_nuls.csv",
     RawBytePolluter("fe_plus_nuls", _fe_plus_nuls,
                     "Compound: 0xFE after each CRLF + scattered NULs"), {}),

    ("lineend_c1_mid_cell.csv",
     RawBytePolluter("c1_mid_cell", _c1_mid_cell,
                     "C1 control bytes injected mid-cell (not at EOL)"), {}),

    ("lineend_nel_inside_cells.csv",
     RawBytePolluter("nel_in_cells", _nel_inside_cells,
                     "UTF-8 NEL bytes embedded inside cell content"), {}),

    ("lineend_interleave_ls_ps_crlf.csv",
     RawBytePolluter("interleave_eol", _interleave_ls_ps_crlf,
                     "Cycle CRLF / U+2028 / U+2029 as record terminators"), {}),

    ("lineend_three_byte_after_crlf.csv",
     RawBytePolluter("three_byte_eol", _three_byte_after_crlf,
                     "0xFE 0xFF 0x00 sequence after each CRLF"), {}),

    ("lineend_random_c1_throughout.csv",
     RawBytePolluter("rand_c1", _random_c1_throughout,
                     "40 random C1 bytes scattered through file"), {}),

    ("lineend_bom_after_each_crlf.csv",
     RawBytePolluter("bom_after_eol", _bom_after_each_crlf,
                     "UTF-8 BOM (EF BB BF) injected after each CRLF"), {}),

    ("lineend_double_ff_delim.csv",
     RawBytePolluter("double_ff", _double_ff_delim,
                     "Doubled form-feed as record terminator"), {}),

    ("lineend_cr_only_with_stray_lf.csv",
     RawBytePolluter("cr_lf_compound", _cr_only_with_stray_lf,
                     "CR-only with one CRLF every 5th row"), {}),

    ("lineend_quote_before_crlf_back_half.csv",
     RawBytePolluter("quote_before_eol", _quote_before_crlf_back_half,
                     "Stray quote before CRLF in second half of file"), {}),
]
