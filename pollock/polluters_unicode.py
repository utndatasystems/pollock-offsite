"""
Engine A: Unicode & encoding hostility.

Pollutions that exploit Unicode/byte-level edge cases that mainstream CSV
parsers mishandle. Two flavors:

1. XML-mutating polluters — non-ASCII chars introduced via the standard
   XML pipeline, with encoding switched to UTF-8 so the rendered bytes are
   well-formed UTF-8 (parameters honestly declare UTF-8).

2. Byte-level mutators wrapped in `RawBytePolluter` — pollutions the XML
   pipeline can't represent (BOMs, NEL/LS/PS line separators, transcoded
   encodings, invalid UTF-8 sequences, lone surrogates, mid-file mutations).

For pollutions that change the actual file encoding (utf-16-le, cp1252),
we use `EncodingAwareRawBytePolluter`, a subclass of `RawBytePolluter`
that pre-sets `file.encoding` so `write_parameters` honestly declares the
new encoding. This isolates Unicode-handling tests from dialect-mismatch
tests (which belong to Engine F).
"""
from __future__ import annotations

import unicodedata
from copy import deepcopy
from pathlib import Path
import os

from . import polluters_stdlib as pl
from .CSVFile import CSVFile
from .polluters_extended import RawBytePolluter, _render_csv_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _switch_to_utf8(file: CSVFile) -> None:
    """Switch a file to UTF-8 so non-ASCII XML mutations render cleanly."""
    file.encoding = "utf_8"
    file.xml.getroot().attrib["encoding"] = "utf_8"


class EncodingAwareRawBytePolluter(RawBytePolluter):
    """A RawBytePolluter that sets file.encoding before parameters are written.

    Use this when the byte mutation transcodes the file to a non-default
    encoding and you want parameters to reflect that honestly.
    """

    def __init__(self, name, mutator, encoding, description=""):
        super().__init__(name, mutator, description)
        self.encoding = encoding

    def apply(self, source_file, out_csv_dir, out_clean_dir,
              out_parameters_dir, new_filename):
        f = deepcopy(source_file)
        f.filename = new_filename
        f.xml.getroot().attrib["filename"] = new_filename

        # Set encoding BEFORE write_parameters runs so params declare the
        # new encoding honestly.
        f.encoding = self.encoding
        f.xml.getroot().attrib["encoding"] = self.encoding

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


# ---------------------------------------------------------------------------
# XML-mutating polluters (wrap stdlib polluters, switch to UTF-8)
# ---------------------------------------------------------------------------


def smart_double_quotes(file: CSVFile) -> None:
    """Replace ASCII " with U+201C/U+201D smart quotes on every quoted field."""
    pl.changeQuotationChar(file, target_char="\u201c\u201d")
    _switch_to_utf8(file)


def smart_single_quotes(file: CSVFile) -> None:
    """Replace quote char with U+2018/U+2019 curly single quotes."""
    pl.changeQuotationChar(file, target_char="\u2018\u2019")
    _switch_to_utf8(file)


def mixed_smart_ascii_quotes(file: CSVFile) -> None:
    """Quote some rows with smart quotes, others with ASCII — mixed in the same file."""
    # First switch all to smart quotes via XML
    pl.changeQuotationChar(file, target_char="\u201c\u201d")
    _switch_to_utf8(file)
    # Then re-set every other row's quotation_char back to ASCII "
    root = file.xml.getroot()
    rows = root.xpath("//row")
    for idx, row in enumerate(rows):
        if idx % 2 == 0:  # even rows revert to ASCII "
            for q in row.xpath(".//quotation_char"):
                q.text = '"'


def nbsp_field_delimiter(file: CSVFile) -> None:
    """Use U+00A0 NBSP as field delimiter."""
    pl.changeFieldDelimiter(file, target_delimiter="\u00a0")
    _switch_to_utf8(file)


def ideographic_space_field_delimiter(file: CSVFile) -> None:
    """Use U+3000 ideographic space as field delimiter."""
    pl.changeFieldDelimiter(file, target_delimiter="\u3000")
    _switch_to_utf8(file)


def _inject_into_header(file: CSVFile, char: str) -> None:
    root = file.xml.getroot()
    header_values = root.xpath("//row[1]//value")
    for v in header_values:
        text = v.text or ""
        # Insert char between every character of the header
        v.text = char.join(list(text))


def zwsp_in_header(file: CSVFile) -> None:
    """Insert U+200B zero-width space between every char in the header row."""
    _inject_into_header(file, "\u200b")
    _switch_to_utf8(file)


def zwnj_in_header(file: CSVFile) -> None:
    """Insert U+200C zero-width non-joiner between every char in the header."""
    _inject_into_header(file, "\u200c")
    _switch_to_utf8(file)


def zwj_in_header(file: CSVFile) -> None:
    """Insert U+200D zero-width joiner between every char in the header."""
    _inject_into_header(file, "\u200d")
    _switch_to_utf8(file)


def rlm_lrm_around_delimiters(file: CSVFile) -> None:
    """Sprinkle U+200E LRM and U+200F RLM around field delimiters and headers."""
    root = file.xml.getroot()
    delims = root.xpath("//field_delimiter")
    for idx, d in enumerate(delims):
        mark = "\u200e" if idx % 2 == 0 else "\u200f"
        d.text = mark + (d.text or "") + mark
    # also insert RLM into the middle of every header value
    header_values = root.xpath("//row[1]//value")
    for v in header_values:
        text = v.text or ""
        if len(text) >= 2:
            mid = len(text) // 2
            v.text = text[:mid] + "\u200f" + text[mid:]
    _switch_to_utf8(file)


def replacement_char_in_cells(file: CSVFile) -> None:
    """Substitute U+FFFD into a few cells (simulates upstream encoding loss)."""
    root = file.xml.getroot()
    # corrupt header word slightly + a few data cells
    header_vals = root.xpath("//row[1]//value")
    for v in header_vals:
        if v.text and len(v.text) >= 3:
            t = v.text
            v.text = t[0] + "\ufffd" + t[2:]
    # corrupt cell in row 3 col 6 (ProductType)
    rows = root.xpath("//row")
    for r_idx in [2, 5, 8, 12]:
        if r_idx < len(rows):
            vals = rows[r_idx].xpath(".//value")
            if len(vals) > 5 and vals[5].text:
                t = vals[5].text
                vals[5].text = "\ufffd" + t[1:] if len(t) > 1 else "\ufffd"
    _switch_to_utf8(file)


def nfc_vs_nfd_header(file: CSVFile) -> None:
    """Header has 'Café' in NFD form; first row data cell has the same word in NFC.
    Multiset comparison is sensitive to this difference."""
    root = file.xml.getroot()
    header_vals = root.xpath("//row[1]//value")
    if header_vals:
        # replace the first header (DATE) with 'Café' in NFD form
        nfd = unicodedata.normalize("NFD", "Café")
        header_vals[0].text = nfd
    # First data row col 0 — keep "Café" in NFC
    rows = root.xpath("//row")
    if len(rows) > 1:
        data_vals = rows[1].xpath(".//value")
        if data_vals:
            data_vals[0].text = unicodedata.normalize("NFC", "Café")
    _switch_to_utf8(file)


def diacritic_mixed_normalization(file: CSVFile) -> None:
    """Use NFD-decomposed and NFC-composed forms of the same accented strings
    in different rows. Tests parsers' Unicode normalization (or lack thereof)."""
    root = file.xml.getroot()
    rows = root.xpath("//row")
    composed = "Crème Brûlée"
    decomposed = unicodedata.normalize("NFD", composed)
    # alternate composed/decomposed in the ProductDescription column
    for idx, row in enumerate(rows[1:], 1):
        vals = row.xpath(".//value")
        if len(vals) > 6:
            tgt = composed if idx % 2 else decomposed
            vals[6].text = (vals[6].text or "") + " " + tgt
    _switch_to_utf8(file)


# ---------------------------------------------------------------------------
# Byte-level mutators (BOMs, line separators, encodings, invalid UTF-8)
# ---------------------------------------------------------------------------


def _bom_utf8(b: bytes, file: CSVFile) -> bytes:
    return b"\xef\xbb\xbf" + b


def _bom_utf8_double(b: bytes, file: CSVFile) -> bytes:
    return b"\xef\xbb\xbf\xef\xbb\xbf" + b


def _bom_utf16_le(b: bytes, file: CSVFile) -> bytes:
    """Prepend UTF-16-LE BOM (FF FE) to a UTF-8 file — declared encoding mismatch."""
    return b"\xff\xfe" + b


def _bom_utf16_be(b: bytes, file: CSVFile) -> bytes:
    return b"\xfe\xff" + b


def _bom_utf32_be(b: bytes, file: CSVFile) -> bytes:
    return b"\x00\x00\xfe\xff" + b


def _bom_utf32_le(b: bytes, file: CSVFile) -> bytes:
    return b"\xff\xfe\x00\x00" + b


def _bom_mid_file(b: bytes, file: CSVFile) -> bytes:
    """Insert a UTF-8 BOM after the 5th newline."""
    parts = b.split(b"\r\n")
    if len(parts) > 5:
        head = b"\r\n".join(parts[:5]) + b"\r\n"
        tail = b"\r\n".join(parts[5:])
        return head + b"\xef\xbb\xbf" + tail
    return b"\xef\xbb\xbf" + b


def _replace_record_with(seq: bytes):
    """Build a mutator that swaps \\r\\n for `seq`."""
    def mut(b: bytes, file: CSVFile) -> bytes:
        return b.replace(b"\r\n", seq)
    return mut


# NEL is encoded as 0xC2 0x85 in UTF-8
_NEL = "\u0085".encode("utf-8")
# LINE SEPARATOR U+2028 → 0xE2 0x80 0xA8
_LS = "\u2028".encode("utf-8")
# PARAGRAPH SEPARATOR U+2029 → 0xE2 0x80 0xA9
_PS = "\u2029".encode("utf-8")


def _utf16_transcode(b: bytes, file: CSVFile) -> bytes:
    """No-op: EncodingAwareRawBytePolluter has already encoded as UTF-16-LE."""
    return b


def _utf16be_transcode(b: bytes, file: CSVFile) -> bytes:
    """No-op: bytes are already UTF-16-BE thanks to EncodingAwareRawBytePolluter."""
    return b


def _cp1252_transcode(b: bytes, file: CSVFile) -> bytes:
    """File is already cp1252-encoded; inject a few Windows-1252-only high-bit chars."""
    # Decode from cp1252 (the file's declared encoding), modify, re-encode.
    text = b.decode("cp1252", errors="replace")
    text = text.replace("PRODUCTID", "PRODUCTID\u201c\u2122", 1)
    return text.encode("cp1252", errors="replace")


def _mixed_header_utf16_body_utf8(b: bytes, file: CSVFile) -> bytes:
    """Header row encoded as UTF-16-LE, body as UTF-8."""
    text = b.decode("utf-8", errors="replace")
    nl = text.find("\r\n")
    if nl < 0:
        return b
    header = text[: nl + 2]
    body = text[nl + 2 :]
    return header.encode("utf-16-le") + body.encode("utf-8")


def _invalid_utf8_in_cells(b: bytes, file: CSVFile) -> bytes:
    """Inject 0xC3 0x28 (start of multi-byte then ASCII — invalid UTF-8)."""
    # insert into a few specific locations in the body
    inj = b"\xc3\x28"
    parts = b.split(b"\r\n")
    out = []
    for i, p in enumerate(parts):
        if i in (3, 7, 11) and p:
            # inject at midpoint of the row
            mid = len(p) // 2
            out.append(p[:mid] + inj + p[mid:])
        else:
            out.append(p)
    return b"\r\n".join(out)


def _lone_surrogate(b: bytes, file: CSVFile) -> bytes:
    """Inject the raw bytes for an unpaired UTF-16 surrogate (D800).
    Encoded as UTF-8 it would be ED A0 80 — invalid as standalone UTF-8."""
    parts = b.split(b"\r\n")
    if len(parts) > 4:
        parts[4] = parts[4] + b"\xed\xa0\x80,trailer"
    return b"\r\n".join(parts)


def _overlong_utf8(b: bytes, file: CSVFile) -> bytes:
    """Replace one '/' with overlong UTF-8 (C0 AF) — invalid."""
    return b.replace(b"https:/", b"https:\xc0\xaf", 1)


def _embedded_nul(b: bytes, file: CSVFile) -> bytes:
    """Inject NUL bytes into a few cells (parsers often refuse or split on them)."""
    parts = b.split(b"\r\n")
    out = []
    for i, p in enumerate(parts):
        if i in (2, 6, 10) and p:
            mid = len(p) // 2
            out.append(p[:mid] + b"\x00" + p[mid:])
        else:
            out.append(p)
    return b"\r\n".join(out)


def _utf7_encoded(b: bytes, file: CSVFile) -> bytes:
    """No-op: EncodingAwareRawBytePolluter has already encoded the bytes as UTF-7."""
    return b


# Combined / sharper attacks (added in round 2)
def _bom_utf8_plus_smart_quotes(b: bytes, file: CSVFile) -> bytes:
    """UTF-8 BOM prepended + smart quotes in body."""
    text = b.decode("utf-8", errors="replace")
    text = text.replace('"', "\u201c", 1)
    return b"\xef\xbb\xbf" + text.encode("utf-8")


def _multiple_boms_scattered(b: bytes, file: CSVFile) -> bytes:
    """Multiple BOMs scattered through the file (header start, after row 5, end)."""
    BOM = b"\xef\xbb\xbf"
    parts = b.split(b"\r\n")
    if len(parts) < 6:
        return BOM + b
    parts[0] = BOM + parts[0]
    parts[5] = BOM + parts[5]
    return b"\r\n".join(parts) + BOM


def _nel_with_bom(b: bytes, file: CSVFile) -> bytes:
    """UTF-8 BOM + NEL line separators."""
    return b"\xef\xbb\xbf" + b.replace(b"\r\n", _NEL)


def _ls_no_terminator(b: bytes, file: CSVFile) -> bytes:
    """Replace \\r\\n with LS, and also strip the trailing record delimiter."""
    out = b.replace(b"\r\n", _LS)
    if out.endswith(_LS):
        out = out[: -len(_LS)]
    return out


def _zwsp_around_every_delim(b: bytes, file: CSVFile) -> bytes:
    """Wrap every comma in zero-width spaces."""
    zwsp = "\u200b".encode("utf-8")
    return b.replace(b",", zwsp + b"," + zwsp)


def _mixed_invalid_in_quoted_field(b: bytes, file: CSVFile) -> bytes:
    """Inject invalid UTF-8 INSIDE a quoted field (most damaging — breaks quote handling)."""
    text = b.decode("utf-8", errors="replace")
    # find a quoted field and inject mid-quote
    idx = text.find('"', text.find('"') + 1)  # second quote = start of next quoted field
    if idx > 0:
        # insert raw bytes that are invalid UTF-8
        prefix = text[: idx + 1].encode("utf-8")
        suffix = text[idx + 1 :].encode("utf-8")
        return prefix + b"\xc3\x28\xff\xfe" + suffix
    return b


def _bom_with_embedded_nul(b: bytes, file: CSVFile) -> bytes:
    """BOM + embedded NUL in row 3."""
    out = _embedded_nul(b, file)
    return b"\xef\xbb\xbf" + out


def _smart_quotes_with_invalid_utf8(b: bytes, file: CSVFile) -> bytes:
    """Replace ASCII quotes with smart quotes AND inject invalid UTF-8."""
    text = b.decode("utf-8", errors="replace")
    text = text.replace('"', "\u201c")
    out = text.encode("utf-8")
    # inject invalid utf-8 in middle
    mid = len(out) // 2
    return out[:mid] + b"\xc3\x28" + out[mid:]


def _crlf_to_lf_with_bom(b: bytes, file: CSVFile) -> bytes:
    """UTF-8 BOM + LF-only line endings (instead of CRLF) — params still say CRLF."""
    return b"\xef\xbb\xbf" + b.replace(b"\r\n", b"\n")


def _fffd_everywhere(b: bytes, file: CSVFile) -> bytes:
    """Inject U+FFFD replacement characters scattered through the file."""
    text = b.decode("utf-8", errors="replace")
    out = []
    for i, c in enumerate(text):
        out.append(c)
        if i % 25 == 24:
            out.append("\ufffd")
    return "".join(out).encode("utf-8")


def _ps_record_with_bom(b: bytes, file: CSVFile) -> bytes:
    """UTF-8 BOM + paragraph separator instead of \\r\\n."""
    return b"\xef\xbb\xbf" + b.replace(b"\r\n", _PS)


def _mixed_line_endings(b: bytes, file: CSVFile) -> bytes:
    """Mix CRLF, LF, NEL, and LS in different rows."""
    parts = b.split(b"\r\n")
    seps = [b"\r\n", b"\n", _NEL, _LS, b"\r\n"]
    out = b""
    for i, p in enumerate(parts):
        out += p
        if i < len(parts) - 1:
            out += seps[i % len(seps)]
    return out


# ---------------------------------------------------------------------------
# POLLUTIONS registry
# ---------------------------------------------------------------------------


POLLUTIONS = [
    # === Round 1: starting set (duds dropped) ============================
    # BOMs — break pycsv's Sniffer; some break duckdb / pandas too.
    ("unicode_bom_utf8.csv",
     RawBytePolluter("bom_utf8", _bom_utf8, "Prepend UTF-8 BOM"),
     {}),
    ("unicode_bom_utf8_doubled.csv",
     RawBytePolluter("bom_utf8_doubled", _bom_utf8_double, "Prepend two UTF-8 BOMs"),
     {}),
    ("unicode_bom_utf16le_in_utf8.csv",
     RawBytePolluter("bom_utf16le", _bom_utf16_le, "UTF-16-LE BOM on UTF-8 file"),
     {}),
    ("unicode_bom_utf16be_in_utf8.csv",
     RawBytePolluter("bom_utf16be", _bom_utf16_be, "UTF-16-BE BOM on UTF-8 file"),
     {}),
    ("unicode_bom_utf32be.csv",
     RawBytePolluter("bom_utf32be", _bom_utf32_be, "Prepend UTF-32-BE BOM"),
     {}),
    ("unicode_bom_utf32le.csv",
     RawBytePolluter("bom_utf32le", _bom_utf32_le, "Prepend UTF-32-LE BOM"),
     {}),
    ("unicode_bom_midfile.csv",
     RawBytePolluter("bom_midfile", _bom_mid_file, "Inject UTF-8 BOM after row 5"),
     {}),

    # Unicode line separators — destroy pycsv/pandas, hurt duckdbparse.
    ("unicode_record_delim_nel.csv",
     RawBytePolluter("record_nel", _replace_record_with(_NEL),
                     "Use U+0085 NEL as record delimiter"),
     {}),
    ("unicode_record_delim_ls.csv",
     RawBytePolluter("record_ls", _replace_record_with(_LS),
                     "Use U+2028 LINE SEPARATOR as record delimiter"),
     {}),
    ("unicode_record_delim_ps.csv",
     RawBytePolluter("record_ps", _replace_record_with(_PS),
                     "Use U+2029 PARAGRAPH SEPARATOR as record delimiter"),
     {}),

    # Smart quotes — params honestly say \u201c, but parsers expecting "
    # mishandle them (pycsv/pandas/duckdbparse).
    ("unicode_smart_double_quotes.csv", smart_double_quotes, {}),
    ("unicode_smart_single_quotes.csv", smart_single_quotes, {}),
    ("unicode_zwsp_in_header.csv", zwsp_in_header, {}),
    ("unicode_rlm_lrm_marks.csv", rlm_lrm_around_delimiters, {}),

    # Full encoding switches (params honestly declare new encoding).
    ("unicode_utf16le_file.csv",
     EncodingAwareRawBytePolluter("utf16le_file", _utf16_transcode,
                                  encoding="utf_16_le",
                                  description="File transcoded to UTF-16-LE"),
     {}),
    ("unicode_utf16be_file.csv",
     EncodingAwareRawBytePolluter("utf16be_file", _utf16be_transcode,
                                  encoding="utf_16_be",
                                  description="File transcoded to UTF-16-BE"),
     {}),
    ("unicode_mixed_header_utf16_body_utf8.csv",
     RawBytePolluter("mixed_enc", _mixed_header_utf16_body_utf8,
                     "Header in UTF-16-LE, body in UTF-8"),
     {}),

    # Invalid byte sequences (kill pandas, pycsv).
    ("unicode_invalid_utf8_bytes.csv",
     RawBytePolluter("invalid_utf8", _invalid_utf8_in_cells,
                     "Inject 0xC3 0x28 invalid UTF-8 sequences"),
     {}),
    ("unicode_lone_surrogate.csv",
     RawBytePolluter("lone_surrogate", _lone_surrogate,
                     "Inject raw bytes for unpaired surrogate U+D800"),
     {}),
    ("unicode_overlong_utf8.csv",
     RawBytePolluter("overlong_utf8", _overlong_utf8,
                     "Replace ASCII / with overlong C0 AF encoding"),
     {}),
    ("unicode_embedded_nul.csv",
     RawBytePolluter("embedded_nul", _embedded_nul,
                     "Inject NUL bytes into cell content"),
     {}),

    # Unicode-space delimiters — pandas auto-detect chokes.
    ("unicode_nbsp_field_delim.csv", nbsp_field_delimiter, {}),
    ("unicode_ideographic_space_delim.csv", ideographic_space_field_delimiter, {}),

    # Mixed-mode (round-1 win, kept).
    ("unicode_mixed_smart_ascii_quotes.csv", mixed_smart_ascii_quotes, {}),

    # === Round 2: sharpened variants of wins =============================
    # Combination attacks: BOM + smart quotes
    ("unicode_bom_plus_smart_quotes.csv",
     RawBytePolluter("bom_smart_quotes", _bom_utf8_plus_smart_quotes,
                     "UTF-8 BOM + smart curly quote in body"),
     {}),
    # BOM + Unicode line separators — double-trouble, BOM defeats sniffers
    # while NEL/PS defeat the line-end logic.
    ("unicode_bom_with_nel.csv",
     RawBytePolluter("bom_with_nel", _nel_with_bom,
                     "UTF-8 BOM + NEL line separators"),
     {}),
    ("unicode_bom_with_ps.csv",
     RawBytePolluter("bom_with_ps", _ps_record_with_bom,
                     "UTF-8 BOM + PARAGRAPH SEPARATOR line endings"),
     {}),
    # Multiple BOMs scattered through the file — adversarial vs. simple
    # "strip BOM at offset 0" implementations.
    ("unicode_multiple_boms_scattered.csv",
     RawBytePolluter("multi_boms", _multiple_boms_scattered,
                     "BOM at start, mid-file, and end"),
     {}),
    # Smart quotes + invalid UTF-8 in a single file
    ("unicode_smart_quotes_invalid_utf8.csv",
     RawBytePolluter("smart_invalid", _smart_quotes_with_invalid_utf8,
                     "Smart quotes + injected invalid UTF-8 bytes"),
     {}),
    # Invalid UTF-8 inside a quoted field — breaks both decoder AND quote logic
    ("unicode_invalid_utf8_in_quoted_field.csv",
     RawBytePolluter("invalid_in_quote", _mixed_invalid_in_quoted_field,
                     "Invalid UTF-8 bytes injected inside an open quote"),
     {}),
    # ZWSP wrapping every comma — invisible delimiters confuse parsers
    ("unicode_zwsp_around_every_delim.csv",
     RawBytePolluter("zwsp_delim", _zwsp_around_every_delim,
                     "Wrap every comma in U+200B zero-width spaces"),
     {}),
    # LS line separators with no trailing terminator — fragile for many parsers
    ("unicode_ls_no_terminator.csv",
     RawBytePolluter("ls_no_term", _ls_no_terminator,
                     "LS line separators, trailing terminator stripped"),
     {}),
    # Mixed line endings (CRLF/LF/NEL/LS) — confuses streaming parsers
    ("unicode_mixed_line_endings.csv",
     RawBytePolluter("mixed_eol", _mixed_line_endings,
                     "Cycle through CRLF, LF, NEL, LS line endings"),
     {}),
    # BOM + LF endings (params declare CRLF — line-ending mismatch + BOM)
    ("unicode_crlf_to_lf_with_bom.csv",
     RawBytePolluter("bom_lf", _crlf_to_lf_with_bom,
                     "UTF-8 BOM + LF-only line endings"),
     {}),
    # BOM + embedded NUL — combo
    ("unicode_bom_with_embedded_nul.csv",
     RawBytePolluter("bom_nul", _bom_with_embedded_nul,
                     "UTF-8 BOM + NUL bytes in cells"),
     {}),
    # FFFD scattered through file — many tokens of replacement char
    ("unicode_fffd_everywhere.csv",
     RawBytePolluter("fffd_scatter", _fffd_everywhere,
                     "U+FFFD replacement character every ~25 chars"),
     {}),
]
