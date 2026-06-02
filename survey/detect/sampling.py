"""Head/tail line sampling for big files.

Tier 1 detectors are bounded: above ``SAMPLE_BYTES_THRESHOLD`` (uncompressed
estimate) we read at most ``SAMPLE_HEAD_LINES`` from the start and
``SAMPLE_TAIL_LINES`` from the end. Detectors that produced approximate
results record ``n_sampled`` in the per-file confidence block.

Routes all byte access through :mod:`survey.detect.io_utils` so that
``.csv.zstd`` files are decompressed on the fly.
"""

from __future__ import annotations

import io
from pathlib import Path

from ..config import SAMPLE_BYTES_THRESHOLD, SAMPLE_HEAD_LINES, SAMPLE_TAIL_LINES
from . import io_utils


def is_big_file(path: Path) -> bool:
    return io_utils.estimated_uncompressed_size(path) > SAMPLE_BYTES_THRESHOLD


def decode_with_fallback(raw: bytes, declared_encoding: str | None) -> tuple[str, str]:
    """Decode ``raw`` using ``declared_encoding`` first, fall back to chardet.

    Mirrors the recipe in ``pollock/CSVFile.py`` lines 131-139. Returns the
    decoded text and the encoding actually used.
    """
    import chardet

    encodings_to_try: list[str] = []
    if declared_encoding:
        encodings_to_try.append(declared_encoding)
    encodings_to_try.append("utf-8")
    encodings_to_try.append("latin-1")  # always succeeds, last resort

    for enc in encodings_to_try:
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue

    detected = chardet.detect(raw) or {}
    enc = detected.get("encoding") or "latin-1"
    return raw.decode(enc, errors="replace"), enc


def head_tail_text(path: Path, encoding: str) -> tuple[str, bool]:
    """Return decoded text capped to head+tail lines for big files.

    Always reads the *whole* file when small. For zstd inputs we still
    only stream-decompress what's needed for the head; the tail uses one
    full pass keeping a rolling window — slower than seek-based tailing
    but compression makes seek-based tailing impossible for streaming
    decompressors.
    """
    if not is_big_file(path):
        raw = io_utils.read_all_bytes(path)
        text, _ = decode_with_fallback(raw, encoding)
        return text, False

    head_lines: list[str] = []
    head_text = ""
    with io_utils.open_decompressed(path) as f:
        buf = io.BytesIO()
        while len(head_lines) < SAMPLE_HEAD_LINES:
            chunk = f.read(1 << 16)
            if not chunk:
                break
            buf.write(chunk)
            text_so_far, _ = decode_with_fallback(buf.getvalue(), encoding)
            head_lines = text_so_far.splitlines(keepends=True)
        head_text = "".join(head_lines[:SAMPLE_HEAD_LINES])

    # Tail: stream the whole file once, keep the last SAMPLE_TAIL_LINES.
    # For plain files we could seek, but compressed streams don't seek
    # cheaply and this keeps the two paths uniform.
    tail_window: list[str] = []
    with io_utils.open_decompressed(path) as f:
        decoder_buf = io.BytesIO()
        leftover_text = ""
        while True:
            chunk = f.read(1 << 16)
            if not chunk:
                break
            decoder_buf.write(chunk)
            try:
                decoded = decoder_buf.getvalue().decode(encoding)
            except (UnicodeDecodeError, LookupError):
                # Fall back: replace bad bytes (we only need approximate tail).
                decoded = decoder_buf.getvalue().decode(encoding, errors="replace")
            # Keep only complete lines, leaving the last (possibly partial) line
            # in ``leftover_text`` until the next chunk fills it in.
            lines = (leftover_text + decoded).splitlines(keepends=True)
            if lines and not lines[-1].endswith(("\n", "\r")):
                leftover_text = lines.pop()
            else:
                leftover_text = ""
            tail_window.extend(lines)
            if len(tail_window) > SAMPLE_TAIL_LINES * 4:
                tail_window = tail_window[-SAMPLE_TAIL_LINES * 2:]
            decoder_buf = io.BytesIO()  # reset
        if leftover_text:
            tail_window.append(leftover_text)
    tail_text = "".join(tail_window[-SAMPLE_TAIL_LINES:])

    glue = "\n# <SAMPLE_GAP> #\n"
    return head_text + glue + tail_text, True
