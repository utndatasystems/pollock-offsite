"""File-level detectors: filename, dimension, encoding, BOM."""

from __future__ import annotations

import codecs
import re
from pathlib import Path

from .parser import ParsedSample


_NONALNUM_NOSEP_RE = re.compile(r"[^a-zA-Z0-9_\-. ]")
_NONALNUM_NOUNDER_RE = re.compile(r"[^a-zA-Z0-9\-. ]")


def file_name_nonalnum(path: Path) -> bool:
    """True when the *stem* contains chars outside ``[A-Za-z0-9_\\- .]``."""
    return bool(_NONALNUM_NOSEP_RE.search(path.stem))


def file_name_nonalnum_nounderscore(path: Path) -> bool:
    """Stricter variant — underscore also disallowed."""
    return bool(_NONALNUM_NOUNDER_RE.search(path.stem))


def dimension(sample: ParsedSample, n_rows: int, n_cols: int) -> str:
    """Returns ``"<rows>x<cols>"`` like the original Pollock survey."""
    return f"{n_rows}x{n_cols}"


def encoding_flag(sample: ParsedSample) -> tuple[str, float]:
    """Canonicalize encoding name via ``codecs.lookup`` to absorb aliases.

    chardet may return ``Windows-1252`` while ``pollock/constants.py``
    expects ``cp1252``; ``codecs.lookup(name).name`` normalises both to
    the canonical Python codec name.
    """
    raw = sample.encoding or "utf-8"
    try:
        canonical = codecs.lookup(raw).name
    except LookupError:
        canonical = raw
    return canonical, sample.encoding_confidence


def bom_present(sample: ParsedSample) -> bool:
    return sample.bom is not None
