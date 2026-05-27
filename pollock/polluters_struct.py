"""
Engine E — Structural ambiguity polluters.

Each pollution produces a CSV that is syntactically well-formed under more
than one plausible dialect interpretation. The benchmark grades against the
clean output we render through the standard XML pipeline; if a sniffer-
driven parser settles on a *different* valid interpretation it scores 0
even though it produced a sensible answer.

Style follows the standard polluters in `polluters_stdlib.py`. Every
filename starts with `struct_`. POLLUTIONS is a list of
    (filename, callable, kwargs)
that the orchestrator (`pollute_main_extended.py`) consumes.
"""
from __future__ import annotations

import random
from copy import deepcopy

from lxml import etree
from lxml.builder import E

from . import polluters_base as pb
from . import polluters_stdlib as pl
from .CSVFile import CSVFile, create_cell
from .polluters_extended import RawBytePolluter


# ---------------------------------------------------------------------------
# Helpers
#
# `polluters_base.changeCell` and `addCells` in the stdlib module are buggy
# (they reference an `insert_value_cell` symbol that doesn't exist and pass
# wrong args to `create_cell`). Our engine doesn't ship fixes for that —
# we just provide drop-in equivalents here that build cells correctly via
# the documented `create_cell` signature.
# ---------------------------------------------------------------------------

def _row_count(file: CSVFile, table: int = 0) -> int:
    return len(file.xml.getroot().xpath(f"//table[{table + 1}]/row"))


def _set_row_field_delim(file: CSVFile, row_idx_one_based: int, new_delim: str,
                         table: int = 0) -> None:
    """Change every field_delimiter of a single row (1-based)."""
    root = file.xml.getroot()
    for fd in root.xpath(f"//table[{table + 1}]/row[{row_idx_one_based}]/field_delimiter"):
        fd.text = new_delim


def my_changeCell(file: CSVFile, row, col, new_content: str, table: int = 0):
    """Working drop-in for polluters_base.changeCell.

    Selects the cell at (row, col) (both 1-based), removes its existing
    children, and rebuilds the cell with `new_content` using the file's
    quoting/escape settings.
    """
    root = file.xml.getroot()
    if isinstance(row, int) and row < 0:
        row = "last()-" + str(row + 1)
    if isinstance(col, int) and col < 0:
        col = "last()-" + str(col + 1)

    query = root.xpath(f"//table[{table + 1}]/row[{row}]/cell[{col}]")
    for old_cell in query:
        existing_role = old_cell.attrib.get("role", "")
        # Build a fresh cell with the new content.
        new_cell = create_cell(field_delimiter=file.field_delimiter,
                               quotation_char=file.quotation_char,
                               escape_char=file.escape_char,
                               text=new_content or "",
                               role=existing_role)
        parent = old_cell.getparent()
        idx = parent.index(old_cell)
        parent.remove(old_cell)
        parent.insert(idx, new_cell)


def my_addCells(file: CSVFile, row, position: int, content: str = "",
                n_cells: int = 1, role: str = "", table: int = 0):
    """Working drop-in for polluters_base.addCells.

    Inserts `n_cells` cells at `position` (0-based) in row `row` (1-based),
    each carrying `content` and `role`, with the matching field delimiter.
    """
    assert position >= 0
    root = file.xml.getroot()
    if isinstance(row, int) and row < 0:
        row = "last()-" + str(row + 1)
    rows = root.xpath(f"//table[{table + 1}]/row[{row}]")
    for r in rows:
        cell_list = [x for x in r if x.tag == "cell"]
        pos = position
        if pos >= len(cell_list):
            row_pos = len(r) - 1  # before record_delimiter
        elif pos > 0:
            tmp = cell_list[pos]
            row_pos = r.index(tmp) - 1
        else:
            row_pos = 0
        for _ in range(n_cells):
            cell = create_cell(field_delimiter=file.field_delimiter,
                               quotation_char=file.quotation_char,
                               escape_char=file.escape_char,
                               text=content or "", role=role)
            delim = E.field_delimiter(file.field_delimiter)
            r.insert(row_pos, cell)
            if row_pos > 0:
                r.insert(row_pos, delim)
            else:
                r.insert(row_pos + 1, delim)


# ---------------------------------------------------------------------------
# 1. Two viable delimiters in one file (alternating , and ;)
# ---------------------------------------------------------------------------

def two_delimiters_alternating(file: CSVFile):
    """Half the rows use `,` and half use `;`. The clean output remains the
    canonical comma-separated rendering — a sniffer that picks `;` will see
    every `,` row as a single column and score 0 on cells.
    """
    n = _row_count(file)
    for i in range(1, n + 1):
        if i % 2 == 0:  # even-numbered rows (1-based) -> ;
            _set_row_field_delim(file, i, ";")


# ---------------------------------------------------------------------------
# 2. Comma-or-pipe ambiguity
# ---------------------------------------------------------------------------

def two_delimiters_comma_pipe(file: CSVFile):
    """Half the rows use `,`, half use `|`.  Both look like a 9-column grid."""
    n = _row_count(file)
    for i in range(1, n + 1):
        if i % 2 == 0:
            _set_row_field_delim(file, i, "|")


# ---------------------------------------------------------------------------
# 3. Variable column count (5 / 7 / 5 / 7) masked by null_padding
# ---------------------------------------------------------------------------

def variable_column_count(file: CSVFile):
    """First half of each data row is dropped on alternating rows so column
    counts oscillate between 5 and 7. The clean output keeps all 9 columns
    (we use deleteCells to drop *cells* in the xml).
    """
    # Only mutate the polluted CSV view — use a fresh copy of source bytes
    # via raw byte mutator path. But we can't do that cleanly here because
    # changeCell-based dropping affects clean output too. Use a byte
    # mutator.
    raise NotImplementedError  # routed through RawBytePolluter below


# ---------------------------------------------------------------------------
# 4. Multi-table with no separator (source.csv twice in a row)
# ---------------------------------------------------------------------------

def two_tables_no_sep_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Append the *clean* source CSV to itself with no blank-line separator.
    The honest clean output (from un-mutated XML) still describes one table.
    """
    text = raw.decode(file.encoding, errors="replace")
    # Strip header from the appended copy so it looks like a continuation.
    # That makes it MORE likely a parser will treat the file as one big 166-row
    # table (and our clean has only 84 rows) → cell_f1 craters.
    # We'll keep header so the table-detection problem is even harder for
    # parsers that look for header-like rows.
    if not text.endswith("\n"):
        text += "\n"
    return (text + text).encode(file.encoding, errors="replace")


# ---------------------------------------------------------------------------
# 5. Multi-table with one blank row separator + different col count
# ---------------------------------------------------------------------------

def two_tables_blank_sep_diff_cols_bytes(raw: bytes, file: CSVFile) -> bytes:
    text = raw.decode(file.encoding, errors="replace")
    if not text.endswith("\n"):
        text += "\n"
    # Build a 5-column second table by truncating each line.
    second = []
    for line in text.splitlines():
        # naive split, doesn't respect quotes — but second table is *spurious*,
        # we want it to look ambiguous, not perfectly parsable
        parts = line.split(",")
        second.append(",".join(parts[:5]))
    return (text + "\n" + "\n".join(second) + "\n").encode(file.encoding,
                                                            errors="replace")


# ---------------------------------------------------------------------------
# 6. Multi-table with overlapping columns (table 2 starts 2 cols in)
# ---------------------------------------------------------------------------

def two_tables_overlapping_bytes(raw: bytes, file: CSVFile) -> bytes:
    text = raw.decode(file.encoding, errors="replace")
    if not text.endswith("\n"):
        text += "\n"
    second = []
    for line in text.splitlines():
        parts = line.split(",")
        second.append(",".join(parts[2:]))  # drop first 2 cols
    return (text + "\n" + "\n".join(second) + "\n").encode(file.encoding,
                                                            errors="replace")


# ---------------------------------------------------------------------------
# 7. Header looks like data (1,2,3,...,9)
# ---------------------------------------------------------------------------

def header_numeric(file: CSVFile):
    """Replace header cells with `1..9` — sniffers like clevercsv use heuristics
    that look at type homogeneity per column to decide if there's a header.
    Numeric header on a numeric-mixed table tends to flip the sniffer's
    decision.
    """
    for c in range(1, 10):
        my_changeCell(file, row=1, col=c, new_content=str(c))


# ---------------------------------------------------------------------------
# 8. Data looks like header (insert plausible header-like row in the middle)
# ---------------------------------------------------------------------------

def midfile_header_lookalike(file: CSVFile):
    """Replace data row 5 with strings that look like column names. The clean
    rendering still treats it as a data row (role='data'), but a parser that
    detects multi-table or skips bad rows may treat it as a new header.
    """
    fake_header = ["DATE", "TIME", "Quantity", "ProductID", "Price",
                   "ProductType", "ProductDescription", "URL", "Comments"]
    for c, val in enumerate(fake_header, start=1):
        my_changeCell(file, row=10, col=c, new_content=val)


# ---------------------------------------------------------------------------
# 9. Reordered columns within rows (swap cols 3 and 4 in 10 random rows)
# ---------------------------------------------------------------------------

def reorder_cols_3_4_some_rows(file: CSVFile):
    """Swap columns 3 (Qty) and 4 (PRODUCTID) in 10 evenly-spaced data rows.
    Sniffer can't catch — both fields look like short tokens. The clean
    output keeps the original column order, so cell-level grading fails for
    affected cells.
    """
    n = _row_count(file)
    rows_to_swap = list(range(5, n, 8))[:10]
    raise NotImplementedError  # see _reorder_cols_3_4_some_rows_bytes below


def _reorder_cols_3_4_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Byte-level swap of cols 3 and 4 in selected rows. (clean stays honest.)"""
    text = raw.decode(file.encoding, errors="replace")
    lines = text.splitlines(keepends=True)
    swap_idx = list(range(5, len(lines), 8))[:10]
    out = []
    for i, line in enumerate(lines):
        if i in swap_idx:
            # naive split — these rows don't quote cols 3 or 4, so it's safe
            parts = line.rstrip("\r\n").split(",")
            tail = line[len(line.rstrip("\r\n")):]
            if len(parts) >= 4:
                parts[2], parts[3] = parts[3], parts[2]
                out.append(",".join(parts) + tail)
                continue
        out.append(line)
    return "".join(out).encode(file.encoding, errors="replace")


# ---------------------------------------------------------------------------
# 10. Header has one extra trailing column
# ---------------------------------------------------------------------------

def header_extra_trailing_comma(file: CSVFile):
    """Add an empty 10th cell to the header. Some parsers (pandas) will
    interpret this as a name-less index column."""
    my_addCells(file, row=1, position=9, content="", n_cells=1, role="header")


# ---------------------------------------------------------------------------
# 11. Empty leading column on every row (`,DATE,TIME,...`)
# ---------------------------------------------------------------------------

def empty_leading_col_all_rows(file: CSVFile):
    n = _row_count(file)
    for i in range(1, n + 1):
        my_addCells(file, row=i, position=0, content="", n_cells=1,
                    role="header" if i == 1 else "data")


# ---------------------------------------------------------------------------
# 12. Empty trailing column on every row (`...,Comments,`)
# ---------------------------------------------------------------------------

def empty_trailing_col_all_rows(file: CSVFile):
    n = _row_count(file)
    for i in range(1, n + 1):
        my_addCells(file, row=i, position=9, content="", n_cells=1,
                    role="header" if i == 1 else "data")


# ---------------------------------------------------------------------------
# 13. All rows have 9 cols, except one with 10
# ---------------------------------------------------------------------------

def one_row_extra_col(file: CSVFile):
    my_addCells(file, row=15, position=9, content="EXTRA", n_cells=1,
                role="data")


# ---------------------------------------------------------------------------
# 14. Header cell that's an empty string in position 0
# ---------------------------------------------------------------------------

def header_empty_first_cell(file: CSVFile):
    my_changeCell(file, row=1, col=1, new_content="")


# ---------------------------------------------------------------------------
# 15. Header with duplicate column names
# ---------------------------------------------------------------------------

def header_all_duplicate_names(file: CSVFile):
    for c in range(1, 10):
        my_changeCell(file, row=1, col=c, new_content="DATE")


# ---------------------------------------------------------------------------
# 16. Single-column file with delimiter-shaped data
# ---------------------------------------------------------------------------

def single_column_with_commas_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Pretend the file is a 1-column file. Replace the delimiter on the wire
    with `|` and quote each row's whole content in one cell. The cell
    contents still contain commas. The clean rendering (from the un-mutated
    XML) is the canonical 9-column file — a parser that detects `,` will
    parse 9 columns; one that detects `|` will parse 1 column with
    comma-laced content. Both are 'right'; only one matches the clean output.
    """
    text = raw.decode(file.encoding, errors="replace")
    out_lines = []
    for line in text.splitlines():
        # Wrap whole line in quotes and prefix with a `|` separator-friendly
        # header row at index 0.
        # Escape any existing quotes by doubling them.
        line_escaped = line.replace('"', '""')
        out_lines.append(f'"{line_escaped}"')
    return ("|\n" + "\n".join(out_lines) + "\n").encode(file.encoding,
                                                        errors="replace")


# ---------------------------------------------------------------------------
# 17. First row empty, header on row 2
# ---------------------------------------------------------------------------

def empty_line_then_header_bytes(raw: bytes, file: CSVFile) -> bytes:
    return b"\r\n" + raw


# ---------------------------------------------------------------------------
# 18. Empty line in middle of data
# ---------------------------------------------------------------------------

def empty_line_middle_bytes(raw: bytes, file: CSVFile) -> bytes:
    text = raw.decode(file.encoding, errors="replace")
    lines = text.splitlines(keepends=True)
    if len(lines) >= 50:
        lines.insert(40, "\r\n")
    return "".join(lines).encode(file.encoding, errors="replace")


# ---------------------------------------------------------------------------
# 19. Three consecutive empty lines in middle
# ---------------------------------------------------------------------------

def three_empty_lines_middle_bytes(raw: bytes, file: CSVFile) -> bytes:
    text = raw.decode(file.encoding, errors="replace")
    lines = text.splitlines(keepends=True)
    if len(lines) >= 50:
        lines[40:40] = ["\r\n", "\r\n", "\r\n"]
    return "".join(lines).encode(file.encoding, errors="replace")


# ---------------------------------------------------------------------------
# 20. Multi-line header with mismatched column counts
# ---------------------------------------------------------------------------

def multiline_header_mismatch(file: CSVFile):
    """Insert a second header row with only 7 cells. Both rows are role
    'header'; the rendering layer concatenates with " ".
    """
    # second header row with 7 cells (9 - 2 less)
    short_header = ["UNIT", "TS", "QUANTITY", "ID", "USD", "TYPE", "DESC"]
    pb.addRows(file, cell_content=short_header, n_rows=1, position=1,
               col_count=7, role="header")


# ---------------------------------------------------------------------------
# 21. Data row that's a single long string (no delimiters)
# ---------------------------------------------------------------------------

def single_string_data_row(file: CSVFile):
    """Replace data row 20 with one cell that is one long string, no delimiters
    in it. We use the row-level deleteRowFieldDelimiter trick.
    """
    # Just blank out cells 2..9 to nothing, and put the whole content in cell 1.
    long = ("28/01/2018 00:00 2 MG-8769 $74.69 Mens Waterproof Hiking Boots "
            "Waterproof boots https://example.com/MG_8769.html")
    my_changeCell(file, row=20, col=1, new_content=long)
    for c in range(2, 10):
        my_changeCell(file, row=20, col=c, new_content="")


# ---------------------------------------------------------------------------
# 22. Trailing-comma rows mixed with non-trailing-comma rows
# ---------------------------------------------------------------------------

def trailing_comma_mixed_bytes(raw: bytes, file: CSVFile) -> bytes:
    text = raw.decode(file.encoding, errors="replace")
    lines = text.splitlines(keepends=True)
    out = []
    for i, line in enumerate(lines):
        if i % 2 == 1 and line.rstrip("\r\n").endswith(","):
            stripped = line.rstrip("\r\n")
            tail = line[len(stripped):]
            out.append(stripped.rstrip(",") + tail)
        else:
            out.append(line)
    return "".join(out).encode(file.encoding, errors="replace")


# ---------------------------------------------------------------------------
# 23. Column 1 contains values with embedded commas, unquoted
# ---------------------------------------------------------------------------

def col1_unquoted_commas(file: CSVFile):
    """Inject extra commas into the DATE column, unquoted. clean still has the
    original DATE value; the parser will split a single cell into 2.
    """
    # Pick 8 data rows; replace col 1 with a value containing a comma.
    targets = [3, 7, 11, 15, 19, 23, 27, 31]
    for r in targets:
        my_changeCell(file, row=r, col=1,
                      new_content=f"2018, January, {r}")


# ---------------------------------------------------------------------------
# 24. Column-merge ambiguity: `John, Smith` unquoted — should be 1 cell
# ---------------------------------------------------------------------------

def col_merge_ambiguity_bytes(raw: bytes, file: CSVFile) -> bytes:
    """The clean version keeps `"Throw Pillow, Wooden Paddles"` as one cell.
    On the wire, drop the surrounding quotes — parser sees 2 cells; clean has
    1. Causes a column-count drift on every affected row.
    """
    text = raw.decode(file.encoding, errors="replace")
    return text.replace('"Throw Pillow, Wooden Paddles"',
                        'Throw Pillow, Wooden Paddles').replace(
        '"Cycling Jersey, Short-Sleeve"',
        'Cycling Jersey, Short-Sleeve').replace(
        '"Mens Silk Underwear, Crewneck"',
        'Mens Silk Underwear, Crewneck').replace(
        "\"Men's Silk Underwear, Crewneck\"",
        "Men's Silk Underwear, Crewneck").encode(file.encoding,
                                                 errors="replace")


# ---------------------------------------------------------------------------
# 25. Header on line 5 with 4 lines of un-declared preamble
# ---------------------------------------------------------------------------

def undeclared_preamble_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Prepend 4 lines of preamble. The XML doesn't know about it, so the
    clean output starts with the real header. The parser sees the preamble
    as data and gets confused.
    """
    preamble = ("# data export, generated 2018\r\n"
                "# v1.0, internal use only\r\n"
                "Source,Output,Period,Data,Notes,Format,Spec,Vendor,Region\r\n"
                "table,csv,2018,sales,confidential,utf8,v1,acme,us\r\n").encode(
        file.encoding, errors="replace")
    return preamble + raw


# ---------------------------------------------------------------------------
# Round-2 sharpened variants
# ---------------------------------------------------------------------------

def two_delimiters_block_split(file: CSVFile):
    """First 30 rows use `,`, last rows use `;`. A sniffer that scans the
    head of the file picks `,` (correct), then chokes on the tail. Or vice
    versa.
    """
    n = _row_count(file)
    for i in range(31, n + 1):
        _set_row_field_delim(file, i, ";")


def two_delimiters_tab_block(file: CSVFile):
    """Same idea, but ; -> tab. Tabs and commas are both common defaults."""
    n = _row_count(file)
    for i in range(40, n + 1):
        _set_row_field_delim(file, i, "\t")


def header_only_tabs(file: CSVFile):
    """Header uses tabs, data rows use commas. Some sniffers read the first
    line to pick a delimiter."""
    _set_row_field_delim(file, 1, "\t")


def empty_first_two_cols_all(file: CSVFile):
    n = _row_count(file)
    for i in range(1, n + 1):
        for _ in range(2):
            my_addCells(file, row=i, position=0, content="", n_cells=1,
                        role="header" if i == 1 else "data")


def header_numeric_then_data_swap(file: CSVFile):
    """Combine 7+8: numeric header, AND replace row 6 with header-like text."""
    for c in range(1, 10):
        my_changeCell(file, row=1, col=c, new_content=str(c))
    fake_header = ["DATE", "TIME", "Quantity", "ProductID", "Price",
                   "ProductType", "ProductDescription", "URL", "Comments"]
    for c, val in enumerate(fake_header, start=1):
        my_changeCell(file, row=6, col=c, new_content=val)


def midfile_repeated_header(file: CSVFile):
    """Insert exact copies of the header at rows 25 and 50. Parser may treat
    each occurrence as a new table boundary.
    """
    header_vals = ["DATE", "TIME", "Qty", "PRODUCTID", "Price", "ProductType",
                   "ProductDescription", "URL", "Comments"]
    pb.addRows(file, cell_content=header_vals, n_rows=1, position=25,
               role="data")
    pb.addRows(file, cell_content=header_vals, n_rows=1, position=50,
               role="data")


def short_rows_5_cols_first_30(file: CSVFile):
    """First 30 data rows have only 5 cells; rest have 9. duckdbauto's
    null_padding fills with NULLs but column count detection lands on either
    5 (sample size 30) or 9 (full sample).
    """
    for r in range(2, 32):
        # delete cells 6..9 (cols 6,7,8,9 = indices 6..9 in 1-based)
        pb.deleteCells(file, row=r, col=[5, 6, 7, 8])


def two_tables_no_sep_strict_xml(file: CSVFile):
    """Pure-XML doubled file (two `<table>` blocks, no empty boundary).
    """
    pl.addTable(file, n_rows=_row_count(file), n_cols=9, empty_boundary=False)


def reorder_many_rows_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Swap cols 3 and 4 in every other data row."""
    text = raw.decode(file.encoding, errors="replace")
    lines = text.splitlines(keepends=True)
    out = []
    for i, line in enumerate(lines):
        if i >= 1 and i % 2 == 0:
            parts = line.rstrip("\r\n").split(",")
            tail = line[len(line.rstrip("\r\n")):]
            if len(parts) >= 4:
                parts[2], parts[3] = parts[3], parts[2]
                out.append(",".join(parts) + tail)
                continue
        out.append(line)
    return "".join(out).encode(file.encoding, errors="replace")


def col_split_more_pairs_bytes(raw: bytes, file: CSVFile) -> bytes:
    """More aggressive variant of #24 — strip quotes around every quoted
    cell that has a comma in it.
    """
    import re as _re
    text = raw.decode(file.encoding, errors="replace")
    # Match short quoted strings (no embedded quotes) that contain a comma
    # and aren't sentences (skip strings >40 chars to avoid mangling reviews).
    def _replace(m):
        inner = m.group(1)
        if "," in inner and len(inner) < 40:
            return inner
        return m.group(0)
    text2 = _re.sub(r'"([^"]+)"', _replace, text)
    return text2.encode(file.encoding, errors="replace")


def undeclared_preamble_short_bytes(raw: bytes, file: CSVFile) -> bytes:
    """1-line undeclared preamble. Parser typically treats line 0 as header,
    pushes everything down."""
    pre = b"# generated 2018-01-01, source=internal\r\n"
    return pre + raw


# ---------------------------------------------------------------------------
# Round-3 sharpened variants
# ---------------------------------------------------------------------------

def single_col_with_tab_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Variant of #16 — declared "delimiter" at top of file is a tab. Sniffer
    that looks for whitespace delimiter on row 1 picks tab → 1 column.
    """
    text = raw.decode(file.encoding, errors="replace")
    out_lines = []
    for line in text.splitlines():
        line_escaped = line.replace('"', '""')
        out_lines.append(f'"{line_escaped}"')
    return ("\t\n" + "\n".join(out_lines) + "\n").encode(file.encoding,
                                                          errors="replace")


def single_col_with_caret_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Variant of #16 — sniffers like clevercsv pick the most-frequent
    consistent delim. Use a rare `^` so they back off to comma. The clean
    output is what XML rendered (canonical comma-separated) — but our wrapped
    polluted has 1 col."""
    text = raw.decode(file.encoding, errors="replace")
    out_lines = []
    for line in text.splitlines():
        line_escaped = line.replace('"', '""')
        out_lines.append(f'"{line_escaped}"')
    return ("^\n" + "\n".join(out_lines) + "\n").encode(file.encoding,
                                                        errors="replace")


def header_only_pipe(file: CSVFile):
    """Header line uses `|`, data uses `,`. Sniffer that reads the first row
    picks `|` → entire file is parsed as 1 column.
    """
    _set_row_field_delim(file, 1, "|")


def header_only_semicolon(file: CSVFile):
    """Header uses `;`, data uses `,`."""
    _set_row_field_delim(file, 1, ";")


def two_tables_no_sep_skip_header_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Append source twice but skip the second header. Now the file is one
    166-row table that obviously parses as one (header row + 165 data rows).
    But our clean expects 84 lines. Massive false-positive cells.
    """
    text = raw.decode(file.encoding, errors="replace")
    if not text.endswith("\n"):
        text += "\n"
    lines = text.splitlines(keepends=True)
    # Drop first line (header) of the appended copy
    second = "".join(lines[1:])
    return (text + second).encode(file.encoding, errors="replace")


def undeclared_preamble_2_bytes(raw: bytes, file: CSVFile) -> bytes:
    """2-line preamble — typical of CSV exports with metadata."""
    pre = ("Report: Sales Data\r\n"
           "Generated: 2018-12-31\r\n").encode(file.encoding, errors="replace")
    return pre + raw


def undeclared_preamble_metadata_bytes(raw: bytes, file: CSVFile) -> bytes:
    """3-line preamble, last line is delimited and looks like a header. Will
    confuse pandas, duckdb sniffer, and clevercsv all differently.
    """
    pre = ("Report: Quarterly Sales\r\n"
           "Generator: SAP-Export v3.2\r\n"
           "Field1,Field2,Field3,Field4,Field5\r\n").encode(file.encoding,
                                                              errors="replace")
    return pre + raw


def col_merge_ambiguity_v2_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Strip quotes around several comma-bearing 'ProductType' values.
    More cells than v1 (24).
    """
    targets = [
        '"Throw Pillow, Wooden Paddles"',
        '"Cycling Jersey, Short-Sleeve"',
        "\"Men's Silk Underwear, Crewneck\"",
        '"All-Weather Dining Table, Round 48""',
        '"Organic Cotton Oxford Shirt, Plaid"',
        '"Kids\' Sweater Fleece, Hooded"',
        "\"Women's Hikers, Low Ventilated\"",
        "\"Women's Comfort Cycling Jersey, Short-Sleeve\"",
        "\"Men's Boxer, 5\"\" Inseam\"",
        "\"Kids' Mountain Bike, 24\"\"\"",
        '"Tippet Material, Pro Freshwater"',
        '"Waterproof Boots, Tall"',
        '"Heated Insoles"',
        '"Base Layer, Pants"',
        '"Quarter-Zip Hoodie, Camo"',
        '"Tee, Traditional Fit, Short-Sleeve"',
        '"Rolling Duffle, Extra-Large"',
        '"Linen Shirt, Slightly Fitted Short-Sleeve Stripe"',
        "\"Women's Hunting Shoes, 10\"\"\"",
        "\"Men's Loafers, Leather/Nubuck\"",
        "\"Kids' Shirt, Short Sleeve, Graphic\"",
        '"Travel Lock, Combination Cable"',
        '"Beach Chair, Print"',
        '"Swimwear, Print"',
        "\"Tee, Traditional Fit, Long-Sleeve\"",
        '"Camp Light, Two-Pack"',
        '"Underwear, Print"',
        "\"Women's Waterproof Hiking Boots, Leather Mesh\"",
        "\"Men's Boots, 10\"\" Shearling-Lined\"",
        '"Flannel Tunic, Plaid"',
        '"Ceramic Lamp, Stripe"',
        '"Men\'s Socks, Two-Pack"',
    ]
    text = raw.decode(file.encoding, errors="replace")
    for q in targets:
        if q.startswith('"') and q.endswith('"'):
            text = text.replace(q, q[1:-1])
    return text.encode(file.encoding, errors="replace")


def header_numeric_floats(file: CSVFile):
    """Header uses 1.0..9.0 — looks even more like data than 1..9."""
    for c in range(1, 10):
        my_changeCell(file, row=1, col=c, new_content=f"{c}.0")


def all_uppercase_header_with_data_in_first_row_bytes(raw: bytes,
                                                      file: CSVFile) -> bytes:
    """Insert a row of data values BEFORE the header. Sniffer picks first row
    as header; but our clean keeps original header at row 0.
    """
    extra_data = (
        '01/01/2018,00:00,1,XX-0000,$0.00,Test Product,'
        '"Sample row injected before header.","https://example.com/x.html",\r\n'
    ).encode(file.encoding, errors="replace")
    return extra_data + raw


def trailing_partial_row_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Append a trailing line that isn't a full row — looks like a footer or
    a total row. Many parsers with skip_blank_lines=True still ingest it."""
    text = raw.decode(file.encoding, errors="replace")
    if not text.endswith("\n"):
        text += "\n"
    footer = "Total: 83 rows, generated by acme corp\r\n"
    return (text + footer).encode(file.encoding, errors="replace")


def preamble_then_blank_then_data_bytes(raw: bytes, file: CSVFile) -> bytes:
    """3-line preamble, then a blank line, then the real header+data.
    Pandas can't skip this without skiprows; many sniffers parse the preamble
    as the header.
    """
    pre = ("Report: Quarterly Sales\r\n"
           "Generator: SAP-Export v3.2\r\n"
           "License: internal-use only\r\n"
           "\r\n").encode(file.encoding, errors="replace")
    return pre + raw


def header_subset_with_pipe(file: CSVFile):
    """Header uses `|`, data uses `,`, but second-half of data also uses `|`.
    The sniffer sees `,` and `|` competing, decides on... whatever it decides.
    """
    n = _row_count(file)
    _set_row_field_delim(file, 1, "|")
    for i in range(40, n + 1):
        _set_row_field_delim(file, i, "|")


# ---------------------------------------------------------------------------
# POLLUTIONS
# ---------------------------------------------------------------------------

POLLUTIONS = [
    # 1. Two viable delimiters in one file
    ("struct_two_delim_alt.csv", two_delimiters_alternating, {}),
    # 2. Comma-or-pipe ambiguity
    ("struct_two_delim_pipe.csv", two_delimiters_comma_pipe, {}),
    # 3. Variable column count (5/7) — pure byte-level slice
    ("struct_var_col_count_5_7.csv",
     RawBytePolluter("var_col_count_5_7",
                     lambda raw, f: _variable_col_count_bytes(raw, f)), {}),
    # 4. Multi-table no separator
    ("struct_two_tables_no_sep.csv",
     RawBytePolluter("two_tables_no_sep", two_tables_no_sep_bytes), {}),
    # 5. Multi-table blank-sep diff cols
    ("struct_two_tables_blank_diff_cols.csv",
     RawBytePolluter("two_tables_blank_diff_cols",
                     two_tables_blank_sep_diff_cols_bytes), {}),
    # 6. Multi-table overlapping
    ("struct_two_tables_overlap.csv",
     RawBytePolluter("two_tables_overlap", two_tables_overlapping_bytes), {}),
    # 7. Header looks like data
    ("struct_header_numeric.csv", header_numeric, {}),
    # 8. Data looks like header
    ("struct_midfile_header_lookalike.csv", midfile_header_lookalike, {}),
    # 9. Reordered cols in some rows (byte-level so clean stays honest)
    ("struct_reorder_cols_3_4.csv",
     RawBytePolluter("reorder_cols_3_4", _reorder_cols_3_4_bytes), {}),
    # 10. Header has extra trailing col
    ("struct_header_extra_col.csv", header_extra_trailing_comma, {}),
    # 11. Empty leading col on every row
    ("struct_empty_leading_col.csv", empty_leading_col_all_rows, {}),
    # 12. Empty trailing col on every row
    ("struct_empty_trailing_col.csv", empty_trailing_col_all_rows, {}),
    # 13. One row with extra col
    ("struct_one_row_extra_col.csv", one_row_extra_col, {}),
    # 14. Empty first header cell
    ("struct_header_empty_first.csv", header_empty_first_cell, {}),
    # 15. Header all duplicate names
    ("struct_header_all_duplicates.csv", header_all_duplicate_names, {}),
    # 16. Single-column file with delimiter-shaped data
    ("struct_single_col_with_commas.csv",
     RawBytePolluter("single_col_with_commas",
                     single_column_with_commas_bytes), {}),
    # 17. First row empty, header on row 2
    ("struct_empty_then_header.csv",
     RawBytePolluter("empty_then_header", empty_line_then_header_bytes), {}),
    # 18. Single empty line in middle
    ("struct_empty_middle.csv",
     RawBytePolluter("empty_middle", empty_line_middle_bytes), {}),
    # 19. Three consecutive empty lines
    ("struct_three_empty_middle.csv",
     RawBytePolluter("three_empty_middle", three_empty_lines_middle_bytes),
     {}),
    # 20. Multi-line header with col-count mismatch
    ("struct_multiline_header_mismatch.csv", multiline_header_mismatch, {}),
    # 21. Single-string data row (no delimiters)
    ("struct_single_string_row.csv", single_string_data_row, {}),
    # 22. Mixed trailing-comma rows
    ("struct_mixed_trailing_comma.csv",
     RawBytePolluter("mixed_trailing_comma", trailing_comma_mixed_bytes), {}),
    # 23. Col 1 with unquoted commas
    ("struct_col1_unquoted_commas.csv", col1_unquoted_commas, {}),
    # 24. Col-merge ambiguity (drop quotes around comma-bearing values)
    ("struct_col_merge_ambiguity.csv",
     RawBytePolluter("col_merge_ambiguity", col_merge_ambiguity_bytes), {}),
    # 25. Undeclared 4-line preamble
    ("struct_undeclared_preamble_4.csv",
     RawBytePolluter("undeclared_preamble_4", undeclared_preamble_bytes), {}),

    # ----- Round 2: sharpened variants -----
    ("struct_two_delim_block_split.csv", two_delimiters_block_split, {}),
    ("struct_two_delim_tab_block.csv", two_delimiters_tab_block, {}),
    ("struct_header_only_tabs.csv", header_only_tabs, {}),
    ("struct_empty_first_two_cols.csv", empty_first_two_cols_all, {}),
    ("struct_numeric_header_data_swap.csv",
     header_numeric_then_data_swap, {}),
    ("struct_midfile_repeated_header.csv", midfile_repeated_header, {}),
    ("struct_short_rows_5_cols_first_30.csv",
     short_rows_5_cols_first_30, {}),
    ("struct_two_tables_no_sep_xml.csv", two_tables_no_sep_strict_xml, {}),
    ("struct_reorder_many_rows.csv",
     RawBytePolluter("reorder_many_rows", reorder_many_rows_bytes), {}),
    ("struct_col_split_more.csv",
     RawBytePolluter("col_split_more", col_split_more_pairs_bytes), {}),
    ("struct_undeclared_preamble_1.csv",
     RawBytePolluter("undeclared_preamble_1", undeclared_preamble_short_bytes),
     {}),

    # ----- Round 3: more sharpened variants -----
    ("struct_single_col_with_tab.csv",
     RawBytePolluter("single_col_with_tab", single_col_with_tab_bytes), {}),
    ("struct_single_col_with_caret.csv",
     RawBytePolluter("single_col_with_caret", single_col_with_caret_bytes), {}),
    ("struct_header_only_pipe.csv", header_only_pipe, {}),
    ("struct_header_only_semicolon.csv", header_only_semicolon, {}),
    ("struct_two_tables_no_sep_no_header.csv",
     RawBytePolluter("two_tables_no_sep_no_header",
                     two_tables_no_sep_skip_header_bytes), {}),
    ("struct_undeclared_preamble_2.csv",
     RawBytePolluter("undeclared_preamble_2", undeclared_preamble_2_bytes), {}),
    ("struct_undeclared_preamble_metadata.csv",
     RawBytePolluter("undeclared_preamble_metadata",
                     undeclared_preamble_metadata_bytes), {}),
    ("struct_col_merge_ambiguity_v2.csv",
     RawBytePolluter("col_merge_ambiguity_v2", col_merge_ambiguity_v2_bytes),
     {}),
    ("struct_header_numeric_floats.csv", header_numeric_floats, {}),
    ("struct_data_before_header.csv",
     RawBytePolluter("data_before_header",
                     all_uppercase_header_with_data_in_first_row_bytes), {}),
    ("struct_trailing_partial_row.csv",
     RawBytePolluter("trailing_partial_row", trailing_partial_row_bytes), {}),
    ("struct_preamble_blank_then_data.csv",
     RawBytePolluter("preamble_blank_then_data",
                     preamble_then_blank_then_data_bytes), {}),
    ("struct_header_subset_with_pipe.csv", header_subset_with_pipe, {}),
]


# ---------------------------------------------------------------------------
# Byte-level helpers used in POLLUTIONS
# ---------------------------------------------------------------------------

def _variable_col_count_bytes(raw: bytes, file: CSVFile) -> bytes:
    """Truncate every other data line to 5 cols. Header keeps all 9.
    Clean output (from XML) keeps all 9 columns + 83 data rows.
    """
    text = raw.decode(file.encoding, errors="replace")
    lines = text.splitlines(keepends=True)
    out = []
    for i, line in enumerate(lines):
        if i == 0 or i % 2 == 1:
            out.append(line)
            continue
        # naive split — these rows are mostly safe (header-row commas only)
        # but use a smarter split to handle quoted fields correctly:
        stripped = line.rstrip("\r\n")
        tail = line[len(stripped):]
        parts = _split_csv_respecting_quotes(stripped)
        if len(parts) >= 7:
            parts = parts[:5] + parts[7:]  # keep cols 1-5 and 8-9 → 7 cols
        out.append(",".join(parts) + tail)
    return "".join(out).encode(file.encoding, errors="replace")


def _split_csv_respecting_quotes(line: str) -> list:
    """Tiny CSV splitter that respects double-quoted fields."""
    out = []
    cur = []
    in_quote = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == '"':
            in_quote = not in_quote
            cur.append(c)
        elif c == "," and not in_quote:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return out
