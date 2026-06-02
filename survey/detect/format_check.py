"""Conservative non-CSV format detection.

Some corpora ship files with ``.csv``/``.tsv`` extensions whose contents
are actually a different binary format (PDF, ZIP/XLSX, image, MS Office
OLE2 compound document, ...). Those files would otherwise flow into
:func:`survey.detect.parser.parse_csv_sample` and produce meaningless
detector output.

Detection runs on the **uncompressed** head of the file via
:func:`survey.detect.io_utils.read_head_bytes`, so wrappers like
``foo.pdf.csv.gz`` still match on the inner PDF magic rather than the
outer gzip envelope.

Whitelist-of-binary-magics approach: we only flag formats we are
confident are not CSV. A ``None`` return means "not on the blacklist",
NOT "is a CSV" — that's what the rest of the pipeline decides.
"""

from __future__ import annotations

from pathlib import Path

from . import io_utils


# (label, magic_prefix). All prefixes are at offset 0; no two collide.
_BINARY_MAGICS: tuple[tuple[str, bytes], ...] = (
    ("pdf",          b"%PDF-"),
    ("zip",          b"PK\x03\x04"),                              # xlsx/docx/odf/jar
    ("zip-empty",    b"PK\x05\x06"),
    ("zip-spanned",  b"PK\x07\x08"),
    ("ole2",         b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),         # legacy xls/doc/ppt
    ("png",          b"\x89PNG\r\n\x1a\n"),
    ("jpeg",         b"\xff\xd8\xff"),
    ("gif",          b"GIF87a"),
    ("gif",          b"GIF89a"),
    ("elf",          b"\x7fELF"),
    ("mach-o-32",    b"\xfe\xed\xfa\xce"),
    ("mach-o-64",    b"\xfe\xed\xfa\xcf"),
    ("mach-o-32-le", b"\xce\xfa\xed\xfe"),
    ("mach-o-64-le", b"\xcf\xfa\xed\xfe"),
    ("sqlite",       b"SQLite format 3\x00"),
    ("parquet",      b"PAR1"),
    ("rar",          b"Rar!\x1a\x07"),
    ("7z",           b"7z\xbc\xaf\x27\x1c"),
    ("bzip2",        b"BZh"),
)

# Largest magic prefix is OLE2 at 8 bytes; 32 leaves headroom.
_HEAD_BYTES = 32


def detect_non_csv_format(path: Path) -> str | None:
    """Return a short label if ``path`` is a known non-CSV binary format, else ``None``.

    Reads the first :data:`_HEAD_BYTES` decompressed bytes via
    :func:`io_utils.read_head_bytes`, so this is correct for ``.csv.gz``
    and ``.csv.zstd`` wrappers as well as plain files.
    """
    try:
        head = io_utils.read_head_bytes(path, _HEAD_BYTES)
    except Exception:
        # IO/decompression failed; let the downstream parser surface its
        # own error rather than masking it here.
        return None
    for label, magic in _BINARY_MAGICS:
        if head.startswith(magic):
            return label
    return None
