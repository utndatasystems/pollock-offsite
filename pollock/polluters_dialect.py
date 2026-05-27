"""
Engine F — Adversarial dialect mismatch.

Each pollution writes a CSV in one dialect/encoding/structure and a
`parameters/<filename>_parameters.json` that *lies* about what is in the
file. This targets parsers that trust the parameters file blindly
(duckdbparse, pandas, mariadb, sqlite, libreoffice) and mimics a real-world
ETL failure: a misconfigured COPY command or wrong dialect declaration in
a config file.

Two attack patterns are wired here:

  * Pattern A (delimiter/quote/escape mismatch): byte-level mutation runs
    AFTER the standard pipeline has rendered an honest parameters JSON,
    so the JSON keeps describing the un-mutated dialect.
  * Pattern B (header/preamble/n_columns/encoding/column_names mismatch):
    the standard XML pipeline runs, then the parameters JSON is rewritten
    in place with one or more keys overridden. Compatible with both
    XML-mutating polluters and byte-mutating polluters.

All filenames start with `dialect_`. POLLUTIONS exposes the engine entries
to `pollute_main_extended.py`.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Callable, Optional

from lxml import etree

from .CSVFile import CSV_XSL, CSVFile
from .polluters_extended import RawBytePolluter
from . import polluters_base as pb
from . import polluters_stdlib as stdlib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _render_csv_text(file: CSVFile) -> str:
    xslt = etree.XML(CSV_XSL)
    transform = etree.XSLT(xslt)
    return str(transform(file.xml))


def _patch_parameters(parameters_path: str, overrides: dict) -> None:
    """Read an existing parameters JSON, apply overrides, write it back."""
    with open(parameters_path, "r") as f:
        data = json.load(f)
    data.update(overrides)
    with open(parameters_path, "w") as f:
        json.dump(data, f, indent=4)


class _DialectMismatchPolluter(RawBytePolluter):
    """RawBytePolluter that also overrides keys in the rendered parameters JSON.

    The base class writes clean+parameters honestly, then runs `mutator` on
    the rendered bytes. This subclass adds a final step: rewrite the
    parameters JSON with `parameter_overrides` so the SuT reads a lying
    config alongside the polluted bytes.

    `mutator` may be None — in that case the rendered bytes are written
    verbatim and only the parameters JSON lies.

    `xml_mutator` runs against the deep-copied CSVFile *before* the rendered
    bytes are produced. Useful when the attack also needs to alter the
    XML-tree representation (e.g. adding extra header rows so the file has
    two header lines while parameters declare one).
    """

    def __init__(self, name: str,
                 mutator: Optional[Callable[[bytes, CSVFile], bytes]] = None,
                 parameter_overrides: Optional[dict] = None,
                 xml_mutator: Optional[Callable[[CSVFile], None]] = None,
                 encoding_override: Optional[str] = None,
                 description: str = ""):
        # Use a no-op mutator if none provided so the base apply() works.
        super().__init__(name=name,
                         mutator=mutator if mutator is not None else _identity_mutator,
                         description=description)
        self.parameter_overrides = parameter_overrides or {}
        self.xml_mutator = xml_mutator
        self.encoding_override = encoding_override

    def apply(self, source_file: CSVFile, out_csv_dir: str, out_clean_dir: str,
              out_parameters_dir: str, new_filename: str) -> None:
        f = deepcopy(source_file)
        f.filename = new_filename
        f.xml.getroot().attrib["filename"] = new_filename

        if self.xml_mutator is not None:
            self.xml_mutator(f)
            # ensure filename hasn't drifted (some stdlib mutators rewrite it)
            f.filename = new_filename
            f.xml.getroot().attrib["filename"] = new_filename

        # If the attack writes bytes in a different encoding than what the
        # parameters JSON will declare, set f.encoding so write_parameters
        # records the bytes' actual encoding, then we override after.
        if self.encoding_override is not None:
            f.encoding = self.encoding_override
            f.xml.getroot().attrib["encoding"] = self.encoding_override

        Path(out_clean_dir).mkdir(parents=True, exist_ok=True)
        Path(out_parameters_dir).mkdir(parents=True, exist_ok=True)
        f.write_clean_csv(out_clean_dir)
        f.write_parameters(out_parameters_dir)

        text = _render_csv_text(f)
        try:
            base_bytes = text.encode(f.encoding)
        except (LookupError, UnicodeEncodeError):
            base_bytes = text.encode("utf-8")
        polluted = self.mutator(base_bytes, f)

        Path(out_csv_dir).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(out_csv_dir, new_filename), "wb") as out:
            out.write(polluted)

        if self.parameter_overrides:
            params_path = os.path.join(out_parameters_dir,
                                       f"{new_filename}_parameters.json")
            _patch_parameters(params_path, self.parameter_overrides)


def _identity_mutator(b: bytes, file: CSVFile) -> bytes:
    return b


# ---------------------------------------------------------------------------
# Byte-level mutators (Pattern A)
# ---------------------------------------------------------------------------

def _replace_outside_quotes(byte_in: int, byte_out: int):
    """Build a mutator that replaces `byte_in` with `byte_out` outside of
    `"`-quoted regions on a per-line basis. Quoting state resets at each
    record delimiter so a malformed quote on one row doesn't pollute the
    rest of the file."""
    def mutator(b: bytes, file: CSVFile) -> bytes:
        out = bytearray()
        in_quote = False
        for byte in b:
            if byte == 0x0A or byte == 0x0D:  # record boundary, reset
                in_quote = False
                out.append(byte)
                continue
            if byte == 0x22:  # double-quote
                in_quote = not in_quote
                out.append(byte)
            elif byte == byte_in and not in_quote:
                out.append(byte_out)
            else:
                out.append(byte)
        return bytes(out)
    return mutator


def _replace_outside_quotes_multibyte(needle: bytes, replacement: bytes):
    """Multi-byte version: replace every occurrence of `needle` outside of
    `"`-quoted regions with `replacement`."""
    def mutator(b: bytes, file: CSVFile) -> bytes:
        out = bytearray()
        in_quote = False
        i = 0
        n = len(b)
        nl = len(needle)
        while i < n:
            byte = b[i]
            if byte == 0x0A or byte == 0x0D:
                in_quote = False
                out.append(byte)
                i += 1
                continue
            if byte == 0x22:
                in_quote = not in_quote
                out.append(byte)
                i += 1
                continue
            if not in_quote and i + nl <= n and b[i:i + nl] == needle:
                out.extend(replacement)
                i += nl
                continue
            out.append(byte)
            i += 1
        return bytes(out)
    return mutator


def _swap_quote_to_single(b: bytes, file: CSVFile) -> bytes:
    """Replace every `"` byte with `'`. Whole-byte swap; safe because the
    source has no embedded `'` quoting."""
    return b.replace(b'"', b"'")


def _swap_quote_to_double_inside_single(b: bytes, file: CSVFile) -> bytes:
    """Wrap quoted regions in `'` instead of `"` (treat `"` as if it were
    `'` for quoting; replace pairs)."""
    return b.replace(b'"', b"'")


def _replace_doubled_quote_with_backslash(b: bytes, file: CSVFile) -> bytes:
    """If a cell contains a doubled `""`, the file's effective quoting
    style is doubled-quote escape. Rewrite to backslash escape.

    Source CSVFile.write_csv writes `""` as the quote escape; this mutator
    replaces every `""` with `\\"` so the file uses backslash escapes."""
    out = bytearray()
    i = 0
    n = len(b)
    while i < n:
        if i + 1 < n and b[i] == 0x22 and b[i + 1] == 0x22:
            out.append(0x5C)  # backslash
            out.append(0x22)
            i += 2
        else:
            out.append(b[i])
            i += 1
    return bytes(out)


def _replace_backslash_escape_with_doubled(b: bytes, file: CSVFile) -> bytes:
    """Rewrite \\" to "" in unquoted bytes (the inverse mutator)."""
    return b.replace(b'\\"', b'""')


def _crlf_to_lf(b: bytes, file: CSVFile) -> bytes:
    return b.replace(b"\r\n", b"\n")


def _lf_to_crlf(b: bytes, file: CSVFile) -> bytes:
    # First normalize to LF only, then expand. Avoids \r\r\n.
    return b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def _comma_to_comma_space(b: bytes, file: CSVFile) -> bytes:
    """Replace each unquoted `,` with `, `."""
    return _replace_outside_quotes_multibyte(b",", b", ")(b, file)


def _comma_space_to_comma(b: bytes, file: CSVFile) -> bytes:
    return _replace_outside_quotes_multibyte(b", ", b",")(b, file)


def _partial_replace(byte_in: int, byte_out: int, fraction: float,
                     min_keep_first: int = 1):
    """Replace a fraction of `byte_in` occurrences (outside quotes) with
    `byte_out`. Deterministic by occurrence index. `min_keep_first` rows
    are left untouched so the parser can lock onto the declared dialect."""
    def mutator(b: bytes, file: CSVFile) -> bytes:
        # Walk the file, count rows. Replace target byte only on rows
        # whose 0-indexed position satisfies `idx % every == 0` for some
        # `every` derived from fraction.
        if fraction <= 0:
            return b
        every = max(2, int(round(1 / fraction)))
        out = bytearray()
        in_quote = False
        row_idx = 0
        for byte in b:
            if byte == 0x0A:
                in_quote = False
                out.append(byte)
                row_idx += 1
                continue
            if byte == 0x0D:
                in_quote = False
                out.append(byte)
                continue
            if byte == 0x22:
                in_quote = not in_quote
                out.append(byte)
                continue
            if (byte == byte_in and not in_quote
                    and row_idx >= min_keep_first
                    and (row_idx % every == 0)):
                out.append(byte_out)
            else:
                out.append(byte)
        return bytes(out)
    return mutator


# Pre-built mutators
_comma_to_semicolon = _replace_outside_quotes(0x2C, 0x3B)
_comma_to_tab = _replace_outside_quotes(0x2C, 0x09)
_comma_to_pipe = _replace_outside_quotes(0x2C, 0x7C)


# ---------------------------------------------------------------------------
# Pattern B helpers: XML mutators (run before bytes are rendered)
# ---------------------------------------------------------------------------

def _add_extra_header_row(file: CSVFile) -> None:
    """Add a second header row (copy of the first) into the XML so the
    file has 2 header lines. Pairs with parameter_override declaring 1.
    """
    stdlib.expandColumnHeader(file, extra_rows=1)


def _add_three_preamble_rows(file: CSVFile) -> None:
    """Add 3 preamble rows but tagged as 'data' so write_parameters
    counts 0 preamble lines. The bytes will however carry these prefix
    rows, and parameters declare 0 preamble — SuT will read the preamble
    rows as data rows.

    We construct the rows ourselves to avoid the standard polluter tagging
    them with role='preamble'."""
    # Insert three single-cell-padded rows of arbitrary preamble text
    # at the top. They'll be tagged role="data" so they show up in clean
    # AND in parameters as part of the data section. Then we'll override
    # parameters to claim preamble_lines=3 (the lying scenario goes the
    # other way too — see _add_three_preamble_rows_honest).
    pb.addRows(file, cell_content="EXPORTED REPORT 2024",
               n_rows=1, position=0, col_count=1, role="preamble")
    pb.addRows(file, cell_content="Generated by ETL pipeline",
               n_rows=1, position=0, col_count=1, role="preamble")
    pb.addRows(file, cell_content="Confidential",
               n_rows=1, position=0, col_count=1, role="preamble")


def _strip_preamble_marking(file: CSVFile) -> None:
    """Remove all preamble role markings (no preamble in XML)."""
    root = file.xml.getroot()
    for r in root.xpath("//row[@role='preamble']"):
        r.attrib["role"] = "data"


# ---------------------------------------------------------------------------
# Encoding-mismatch helpers
# ---------------------------------------------------------------------------

def _inject_high_bit_chars(file: CSVFile) -> None:
    """Replace some cell text with non-ASCII characters so that
    encoding/decoding asymmetries actually corrupt content. We pick a
    couple of cells and inject Latin-1 / Windows-1252 friendly chars."""
    root = file.xml.getroot()
    rows = root.xpath("//row[@role='data']")
    # Inject curly quotes and accented characters into the first few rows.
    samples = ["caf\u00e9", "\u00a9 2024", "na\u00efve", "Sm\u00f6rg\u00e5sbord",
               "voil\u00e0", "\u00e9migr\u00e9"]
    for idx, row in enumerate(rows[:6]):
        # Replace first cell value text with our sample. If the cell already
        # has subvalues (escape splits), strip and replace.
        cells = [c for c in row if c.tag == "cell"]
        if not cells:
            continue
        target_cell = cells[min(2, len(cells) - 1)]  # 3rd-ish cell
        # Wipe child <value> elements, leave quotation/escape markers alone.
        new_values = []
        for child in list(target_cell):
            if child.tag == "value":
                target_cell.remove(child)
        v = etree.SubElement(target_cell, "value")
        v.text = samples[idx % len(samples)]


def _utf8_to_cp1252_mutator(b: bytes, file: CSVFile) -> bytes:
    """Re-encode the bytes from utf-8 to cp1252 (lossy where chars are
    outside cp1252's range; we replace with `?`)."""
    text = b.decode("utf-8", errors="replace")
    return text.encode("cp1252", errors="replace")


def _utf8_to_utf16le_mutator(b: bytes, file: CSVFile) -> bytes:
    text = b.decode("utf-8", errors="replace")
    return text.encode("utf-16-le", errors="replace")


# ---------------------------------------------------------------------------
# Header / preamble rewriters via parameters JSON
# ---------------------------------------------------------------------------

def _drop_header_role(file: CSVFile) -> None:
    """Reclassify the header row as data, so the file effectively has no
    header. Parameters JSON will honestly say 0 (we then override to lie)."""
    root = file.xml.getroot()
    for r in root.xpath("//row[@role='header']"):
        r.attrib["role"] = "data"


# ---------------------------------------------------------------------------
# Pollution catalogue
# ---------------------------------------------------------------------------

POLLUTIONS = []


def _P(filename: str, *, mutator=None, overrides=None, xml_mutator=None,
       encoding_override=None, description=""):
    POLLUTIONS.append((filename, _DialectMismatchPolluter(
        name=filename, mutator=mutator, parameter_overrides=overrides,
        xml_mutator=xml_mutator, encoding_override=encoding_override,
        description=description), {}))


# 1. Parameters declare `,`, file uses `;`
_P("dialect_delim_lies_comma_actual_semicolon.csv",
   mutator=_comma_to_semicolon,
   overrides={"delimiter": ","},
   description="Bytes use `;` between fields; params claim `,`.")

# 2. Parameters declare `,`, file uses `\t`
_P("dialect_delim_lies_comma_actual_tab.csv",
   mutator=_comma_to_tab,
   overrides={"delimiter": ","},
   description="Bytes use TAB between fields; params claim `,`.")

# 3. Parameters declare `,`, file uses `|`
_P("dialect_delim_lies_comma_actual_pipe.csv",
   mutator=_comma_to_pipe,
   overrides={"delimiter": ","},
   description="Bytes use `|` between fields; params claim `,`.")

# 3b. Parameters declare `;`, file uses `,`
_P("dialect_delim_lies_semicolon_actual_comma.csv",
   mutator=None,
   overrides={"delimiter": ";"},
   description="Bytes use `,`; params claim `;`.")

# 3c. Parameters declare `\t`, file uses `,`
_P("dialect_delim_lies_tab_actual_comma.csv",
   mutator=None,
   overrides={"delimiter": "\t"},
   description="Bytes use `,`; params claim TAB.")

# 4. Parameters declare quotechar `"`, file uses `'`
_P("dialect_quote_lies_double_actual_single.csv",
   mutator=_swap_quote_to_single,
   overrides={"quotechar": '"', "escapechar": '"'},
   description="Bytes use `'` for quoting; params claim `\"`.")

# 5. Parameters declare quotechar `'`, file uses `"`
_P("dialect_quote_lies_single_actual_double.csv",
   mutator=None,
   overrides={"quotechar": "'", "escapechar": "'"},
   description="Bytes use `\"`; params claim `'`.")

# 6. Parameters declare escape `\`, file uses doubled-quote escape
_P("dialect_escape_lies_backslash_actual_doubled.csv",
   mutator=None,
   overrides={"escapechar": "\\", "quotechar": '"'},
   description="Bytes use `\"\"` to escape; params claim `\\`.")

# 7. Parameters declare escape `"`, file uses backslash escape
_P("dialect_escape_lies_doubled_actual_backslash.csv",
   mutator=_replace_doubled_quote_with_backslash,
   overrides={"escapechar": '"', "quotechar": '"'},
   description="Bytes use `\\\"` to escape; params claim doubled-quote.")

# 8. File has 2 header rows, parameters declare 1
_P("dialect_header_lies_one_actual_two.csv",
   xml_mutator=_add_extra_header_row,
   overrides={"header_lines": 1},
   description="File carries 2 header rows; params claim 1.")

# 9. File has 1 header row, parameters declare 2
_P("dialect_header_lies_two_actual_one.csv",
   mutator=None,
   overrides={"header_lines": 2},
   description="File has 1 header; params claim 2 (data row 1 lost).")

# 10. File has 3 preamble rows tagged as preamble, params lie preamble=0
_P("dialect_preamble_lies_zero_actual_three.csv",
   xml_mutator=_add_three_preamble_rows,
   overrides={"preamble_lines": 0},
   description="File has 3 preamble rows; params claim 0.")

# 11. File has 0 preamble rows, params claim 3
_P("dialect_preamble_lies_three_actual_zero.csv",
   mutator=None,
   overrides={"preamble_lines": 3},
   description="File has no preamble; params claim 3 (loses 3 data rows).")

# 12. Parameters declare ascii, bytes are cp1252 with high-bit chars
_P("dialect_encoding_lies_ascii_actual_cp1252.csv",
   xml_mutator=_inject_high_bit_chars,
   encoding_override="cp1252",
   overrides={"encoding": "ascii"},
   description="File has cp1252 high-bit chars; params claim ascii.")

# 13. Parameters declare ascii, bytes are utf-8 multi-byte
_P("dialect_encoding_lies_ascii_actual_utf8.csv",
   xml_mutator=_inject_high_bit_chars,
   encoding_override="utf-8",
   overrides={"encoding": "ascii"},
   description="File has utf-8 multi-byte chars; params claim ascii.")

# 14. Parameters declare utf-8, bytes are utf-16-le
_P("dialect_encoding_lies_utf8_actual_utf16le.csv",
   mutator=_utf8_to_utf16le_mutator,
   overrides={"encoding": "utf-8"},
   description="File is utf-16-le; params claim utf-8.")

# 15. Parameters declare latin-1, bytes are utf-8 (mojibake on multi-byte)
_P("dialect_encoding_lies_latin1_actual_utf8.csv",
   xml_mutator=_inject_high_bit_chars,
   encoding_override="utf-8",
   overrides={"encoding": "latin-1"},
   description="File is utf-8 with multi-byte; params claim latin-1.")

# 16. Parameters declare `,`, file uses `, ` (comma-space)
_P("dialect_delim_lies_comma_actual_comma_space.csv",
   mutator=_comma_to_comma_space,
   overrides={"delimiter": ","},
   description="File uses `, `; params claim `,`.")

# 17. Parameters declare `, `, file uses `,`
_P("dialect_delim_lies_comma_space_actual_comma.csv",
   mutator=None,
   overrides={"delimiter": ", "},
   description="File uses `,`; params claim `, `.")

# 18. Parameters declare `\r\n`, file uses `\n`
_P("dialect_recordsep_lies_crlf_actual_lf.csv",
   mutator=_crlf_to_lf,
   overrides={"row_delimiter": "\r\n"},
   description="File uses LF; params claim CRLF.")

# 18b. Parameters declare `\n`, file uses `\r\n`
_P("dialect_recordsep_lies_lf_actual_crlf.csv",
   mutator=None,
   overrides={"row_delimiter": "\n"},
   description="File uses CRLF; params claim LF.")

# 19. Subtle: 95% of rows use `,`, 5% use `;`; params declare `,`
_P("dialect_delim_subtle_mostly_comma_some_semicolon.csv",
   mutator=_partial_replace(0x2C, 0x3B, 0.1, min_keep_first=2),
   overrides={"delimiter": ","},
   description="~10% of rows use `;`; params claim `,`.")

# 20. Subtle: 95% of rows use `"`, 5% use `'`; params declare `"`
_P("dialect_quote_subtle_mostly_double_some_single.csv",
   mutator=_partial_replace(0x22, 0x27, 0.1, min_keep_first=2),
   overrides={"quotechar": '"'},
   description="~10% of rows use `'` quoting; params claim `\"`.")

# 21. Parameters declare n_columns 9, file actually has 10
def _add_trailing_column(file: CSVFile) -> None:
    pb.addColumns(file, position=file.col_count + 1, n_cols=1,
                  col_names=["TrailingExtra"], cell_content="X", role="data")
    file.col_count += 1
    # Mark the new header cell properly by re-tagging row 1
    root = file.xml.getroot()
    first_row = root.xpath("//row[1]")
    if first_row:
        first_row[0].attrib["role"] = "header"
        for c in first_row[0]:
            if c.tag == "cell":
                c.attrib["role"] = "header"

_P("dialect_ncols_lies_nine_actual_ten.csv",
   xml_mutator=_add_trailing_column,
   overrides={"n_columns": 9},
   description="File has 10 columns; params claim 9.")

# 22. Parameters declare n_columns 9, file actually has 7
def _drop_two_columns(file: CSVFile) -> None:
    if file.col_count >= 7:
        # Drop the last two columns
        pb.deleteColumns(file, col=[file.col_count - 1, file.col_count - 2])
        file.col_count -= 2

_P("dialect_ncols_lies_nine_actual_seven.csv",
   xml_mutator=_drop_two_columns,
   overrides={"n_columns": 9},
   description="File has 7 columns; params claim 9.")

# 23. Parameters declare column_names that don't match the actual header
_P("dialect_colnames_lies_unrelated_names.csv",
   mutator=None,
   overrides={"column_names": ["alpha", "beta", "gamma", "delta",
                               "epsilon", "zeta", "eta", "theta", "iota"]},
   description="Header text in file unchanged; params declare different names.")

# 24. Parameters declare header_lines 0, file has a header
_P("dialect_header_lies_zero_actual_one.csv",
   mutator=None,
   overrides={"header_lines": 0, "column_names": []},
   description="File has 1 header row; params claim 0.")

# 25. Parameters declare header_lines 1, file has none
_P("dialect_header_lies_one_actual_zero.csv",
   xml_mutator=_drop_header_role,
   overrides={"header_lines": 1},
   description="File has no header; params claim 1 (loses first data row).")


# ---------------------------------------------------------------------------
# Round 2 — Sharpened variants targeting auto-detect parsers and
# layered/combined dialect lies. The first round revealed these gaps:
#   * duckdbauto and pycsv shrug off single-axis delimiter swaps because
#     they sniff. Layering an encoding lie with a delimiter lie defeats
#     the sniffer because it can't decode the bytes correctly to even
#     start sniffing.
#   * For SuTs that read parameters but auto-detect delimiter (pandas with
#     delimiter=None), declaring the wrong encoding still corrupts everything.
#   * Combined lies (multiple keys at once) compound damage beyond either
#     alone.
# ---------------------------------------------------------------------------

# 26. Combined: bytes are utf-16-le AND use `;` delimiter; params declare
# utf-8 AND `,`. Stacks two lies that compound.
def _utf8_text_then_semicolon_then_utf16le(b: bytes, file: CSVFile) -> bytes:
    swapped = _comma_to_semicolon(b, file)
    text = swapped.decode("utf-8", errors="replace")
    return text.encode("utf-16-le", errors="replace")

_P("dialect_combo_utf16le_semicolon.csv",
   mutator=_utf8_text_then_semicolon_then_utf16le,
   overrides={"encoding": "utf-8", "delimiter": ","},
   description="Bytes utf-16-le with `;` delim; params claim utf-8 + `,`.")

# 27. Combined: file has 2 headers + 2 preamble; params claim 0 + 0
def _add_preamble_and_extra_header(file: CSVFile) -> None:
    # expand header FIRST (header is at row 1), then prepend preamble.
    stdlib.expandColumnHeader(file, extra_rows=1)
    _add_three_preamble_rows(file)

_P("dialect_combo_preamble_and_multi_header.csv",
   xml_mutator=_add_preamble_and_extra_header,
   overrides={"preamble_lines": 0, "header_lines": 1},
   description="File has 3 preamble + 2 header rows; params claim 0 + 1.")

# 28. Encoding lie: bytes are big5 (wide), params claim utf-8.
def _utf8_to_big5_with_chars(b: bytes, file: CSVFile) -> bytes:
    text = b.decode("utf-8", errors="replace")
    # Replace some ascii content with big5-encodable chars
    text = text.replace("Comments", "\u8a55\u8a96")  # Chinese chars
    return text.encode("big5", errors="replace")

_P("dialect_encoding_lies_utf8_actual_big5.csv",
   xml_mutator=_inject_high_bit_chars,
   mutator=_utf8_to_big5_with_chars,
   overrides={"encoding": "utf-8"},
   description="File is big5; params claim utf-8.")

# 29. UTF-8 BOM + params claim utf-16-le. The BOM makes detection point
# the wrong way and the SuT will use the lying utf-16-le decoder.
def _add_utf8_bom(b: bytes, file: CSVFile) -> bytes:
    return b"\xef\xbb\xbf" + b

_P("dialect_encoding_bom_utf8_lies_utf16le.csv",
   mutator=_add_utf8_bom,
   overrides={"encoding": "utf-16-le"},
   description="File is utf-8 with BOM; params claim utf-16-le.")

# 30. NULL-byte injection as delimiter, params claim `,`. Many parsers
# treat NUL specially.
def _comma_to_nul(b: bytes, file: CSVFile) -> bytes:
    return _replace_outside_quotes(0x2C, 0x00)(b, file)

_P("dialect_delim_lies_comma_actual_nul.csv",
   mutator=_comma_to_nul,
   overrides={"delimiter": ","},
   description="File uses NUL between fields; params claim `,`.")

# 31. Multi-byte delimiter lie: file uses `||` between fields,
# params declare `,`.
def _comma_to_double_pipe(b: bytes, file: CSVFile) -> bytes:
    return _replace_outside_quotes_multibyte(b",", b"||")(b, file)

_P("dialect_delim_lies_comma_actual_double_pipe.csv",
   mutator=_comma_to_double_pipe,
   overrides={"delimiter": ","},
   description="File uses `||`; params claim `,`.")

# 32. Subtle: 50% of rows use `;`, 50% `,`; params declare `,`.
# Higher density than round 1's 10% to force more rows mis-parsed
# without crossing the auto-detect majority.
_P("dialect_delim_subtle_half_semicolon.csv",
   mutator=_partial_replace(0x2C, 0x3B, 0.5, min_keep_first=2),
   overrides={"delimiter": ","},
   description="50% of rows use `;`; params claim `,`.")

# 33. Quote-as-bracket: replace `"` with `[`/`]` pairs; params claim `"`.
def _quote_to_bracket(b: bytes, file: CSVFile) -> bytes:
    out = bytearray()
    in_quote = False
    for byte in b:
        if byte == 0x22:
            out.append(0x5B if not in_quote else 0x5D)
            in_quote = not in_quote
        else:
            out.append(byte)
    return bytes(out)

_P("dialect_quote_lies_double_actual_brackets.csv",
   mutator=_quote_to_bracket,
   overrides={"quotechar": '"'},
   description="File uses [..] for quoting; params claim `\"`.")

# 34. Header lies: params declare 5 header rows when there's only 1.
# Loses 4 data rows entirely, far more aggressive than the +1 case.
_P("dialect_header_lies_five_actual_one.csv",
   mutator=None,
   overrides={"header_lines": 5},
   description="File has 1 header; params claim 5 (loses 4 data rows).")

# 35. Preamble lies: params declare 10 preamble rows; the file has none.
_P("dialect_preamble_lies_ten_actual_zero.csv",
   mutator=None,
   overrides={"preamble_lines": 10},
   description="File has no preamble; params claim 10 (loses 10 data rows).")

# 36. Combined: file has subtle `, ` delim and lies about encoding too.
def _comma_space_then_cp1252(b: bytes, file: CSVFile) -> bytes:
    swapped = _comma_to_comma_space(b, file)
    text = swapped.decode("utf-8", errors="replace")
    return text.encode("cp1252", errors="replace")

_P("dialect_combo_comma_space_with_cp1252.csv",
   xml_mutator=_inject_high_bit_chars,
   mutator=_comma_space_then_cp1252,
   overrides={"encoding": "ascii", "delimiter": ","},
   description="File uses `, ` delim and is cp1252; params claim `,` + ascii.")

# 37. Encoding lies: file uses utf-16-be (less common than utf-16-le),
# params claim utf-8.
def _utf8_to_utf16be(b: bytes, file: CSVFile) -> bytes:
    text = b.decode("utf-8", errors="replace")
    return text.encode("utf-16-be", errors="replace")

_P("dialect_encoding_lies_utf8_actual_utf16be.csv",
   mutator=_utf8_to_utf16be,
   overrides={"encoding": "utf-8"},
   description="File is utf-16-be; params claim utf-8.")

# 38. Quote lies + escape lies stacked: file uses `'` quote with `\\'`
# escapes; params claim `\"` and `\"\"` doubling.
def _double_to_single_with_backslash(b: bytes, file: CSVFile) -> bytes:
    # replace doubled quotes first to backslash-quote, then convert
    # remaining `"` to `'`. Final escape pattern: \'
    step1 = _replace_doubled_quote_with_backslash(b, file)
    return step1.replace(b'"', b"'").replace(b"\\'", b"\\'")  # idempotent step

_P("dialect_combo_quote_single_escape_backslash.csv",
   mutator=_double_to_single_with_backslash,
   overrides={"quotechar": '"', "escapechar": '"'},
   description="File uses `'` quoting with `\\` escape; params claim `\"`/doubled.")
