"""CSV row tokenizer used by every Tier 1 detector.

We deliberately do **not** instantiate ``pollock.CSVFile`` here.
``CSVFile.write_parameters`` (the obvious code we'd want to reuse) depends
on ``self.xml`` being populated, which means building a full lxml tree per
row — fine for the 84-row source CSV, fatal for a 5-million-row real-world
one. Instead this module replicates the small slice we actually need:

  1. Decode the file with chardet fallback (CSVFile.py:131-139).
  2. Sniff a dialect (clevercsv) on a head sample.
  3. Tokenize rows with ``clevercsv.cparser_util.parse_string`` (the same
     call CSVFile.py:154 makes after building its dialect).

The output is a ``ParsedSample`` dataclass that all downstream detectors
share.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from clevercsv import Detector
from clevercsv.cparser_util import parse_string
from clevercsv.dialect import SimpleDialect

from . import io_utils
from .sampling import decode_with_fallback, head_tail_text, is_big_file


# Sentinel inserted by ``sampling.head_tail_text`` between head and tail.
SAMPLE_GAP_TOKEN = "# <SAMPLE_GAP> #"


@dataclass
class ParsedSample:
    path: Path
    bytes_total: int
    encoding: str
    encoding_confidence: float
    bom: bytes | None
    sniffer_dialect: SimpleDialect | None
    sniffer_confidence: float
    raw_text: str
    sampled: bool
    rows: list[list[tuple[str, bool]]] = field(default_factory=list)
    rows_quoted: list[list[bool]] = field(default_factory=list)

    @property
    def field_delimiter(self) -> str:
        return self.sniffer_dialect.delimiter if self.sniffer_dialect else ","

    @property
    def quote_char(self) -> str:
        return self.sniffer_dialect.quotechar if self.sniffer_dialect else '"'

    @property
    def escape_char(self) -> str:
        return self.sniffer_dialect.escapechar if self.sniffer_dialect else ""


_BOM_PREFIXES: tuple[tuple[bytes, str], ...] = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)


def _detect_bom(raw: bytes) -> bytes | None:
    for prefix, _ in _BOM_PREFIXES:
        if raw.startswith(prefix):
            return prefix
    return None


def _detect_encoding(raw: bytes) -> tuple[str, float]:
    """Detect encoding using BOM first, chardet as fallback.

    Mirrors the order pollock/CSVFile.py uses (try declared, fall back to
    chardet) but starts from BOM since we don't have a declared encoding
    when running over a freshly-fetched corpus.
    """
    import chardet

    bom = _detect_bom(raw)
    if bom is not None:
        for prefix, name in _BOM_PREFIXES:
            if raw.startswith(prefix):
                return name, 1.0

    detected = chardet.detect(raw) or {}
    enc = detected.get("encoding") or "utf-8"
    conf = float(detected.get("confidence") or 0.0)
    return enc, conf


def _record_delimiter_from_text(text: str) -> str:
    """Pick the most common newline form in a text sample."""
    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    cr_only = text.count("\r") - crlf
    if crlf >= lf_only and crlf >= cr_only:
        return "\r\n"
    if lf_only >= cr_only:
        return "\n"
    return "\r"


def parse_csv_sample(path: Path, *, force_no_sampling: bool = False) -> ParsedSample:
    """Load + decode + tokenize ``path`` for downstream detectors.

    Handles both plain CSV and ``.csv.zstd`` / ``.csv.zst`` (transparently
    decompressed via :mod:`survey.detect.io_utils`).

    Pass ``force_no_sampling=True`` to read the whole file even when it
    exceeds ``SAMPLE_BYTES_THRESHOLD``. Used by the scan command's
    ``--no-sampling`` flag so line numbers in the tail of large files
    stay accurate at the cost of a full read.

    On failure the returned sample has ``sniffer_dialect=None`` and an
    empty ``rows`` list — callers must check.
    """
    bytes_on_disk = io_utils.file_size_compressed(path)

    # Read up to 1 MB of *uncompressed* bytes for encoding detection +
    # dialect sniffing. For small files this is the whole content.
    sniff_cap = 1 << 20
    raw_head = io_utils.read_head_bytes(path, sniff_cap)

    encoding, conf = _detect_encoding(raw_head)
    bom = _detect_bom(raw_head)

    # Tier 1 always operates on a bounded sample of text — unless the
    # caller forced sampling off, in which case we read the whole file.
    if is_big_file(path) and not force_no_sampling:
        text, sampled = head_tail_text(path, encoding)
    else:
        # Small files: read the entire decompressed contents in one go.
        # The ``raw_head`` we already have may already cover the whole file.
        if len(raw_head) < sniff_cap:
            raw_full = raw_head
        else:
            raw_full = io_utils.read_all_bytes(path)
        text, _ = decode_with_fallback(raw_full, encoding)
        sampled = False

    # Strip BOM from text if present so downstream parsing isn't confused.
    if bom is not None:
        try:
            bom_text = bom.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            bom_text = ""
        if bom_text and text.startswith(bom_text):
            text = text[len(bom_text):]

    # Sniff dialect on the (possibly sampled) text.
    sniffer_dialect: SimpleDialect | None = None
    sniffer_conf = 0.0
    try:
        det = Detector()
        sniffer_dialect = det.detect(text, verbose=False)
        # CleverCSV's score isn't normalised; we report a coarse confidence:
        # 1.0 when a dialect was returned, 0.0 otherwise. Detectors that
        # care about confidence (sniffer_low_confidence) overlay their own
        # heuristics on top of this in ``dialect.py``.
        sniffer_conf = 1.0 if sniffer_dialect is not None else 0.0
    except Exception:
        sniffer_dialect = None
        sniffer_conf = 0.0

    rows: list[list[tuple[str, bool]]] = []
    rows_quoted: list[list[bool]] = []

    if sniffer_dialect is not None:
        # Empty-string escapechar is what pollock/CSVFile.py:151 uses when
        # the escape and quote chars match.
        try:
            tok = list(parse_string(text, sniffer_dialect, return_quoted=True))
            for row in tok:
                rows.append(list(row))
                rows_quoted.append([is_quoted for _, is_quoted in row])
        except Exception:
            rows = []
            rows_quoted = []

    return ParsedSample(
        path=path,
        bytes_total=bytes_on_disk,
        encoding=encoding,
        encoding_confidence=conf,
        bom=bom,
        sniffer_dialect=sniffer_dialect,
        sniffer_confidence=sniffer_conf,
        raw_text=text,
        sampled=sampled,
        rows=rows,
        rows_quoted=rows_quoted,
    )


def vote_field_delimiter(sample: ParsedSample) -> str:
    if sample.sniffer_dialect is None:
        return ""
    return sample.sniffer_dialect.delimiter or ""


def vote_quote_char(sample: ParsedSample) -> str:
    if sample.sniffer_dialect is None:
        return ""
    return sample.sniffer_dialect.quotechar or ""


def vote_escape_char(sample: ParsedSample) -> str:
    if sample.sniffer_dialect is None:
        return ""
    return sample.sniffer_dialect.escapechar or ""


def vote_record_delimiter(sample: ParsedSample) -> str:
    return _record_delimiter_from_text(sample.raw_text)
